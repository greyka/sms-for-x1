"""Сервис модема: статус, слоты, режимы через `netsh mbn`.

Работает поверх Windows Mobile Broadband. Весь ввод/вывод — синхронный;
в GUI вызывается из рабочих потоков (см. viewmodels/worker).
"""
from __future__ import annotations

import re
import subprocess
from typing import Optional

from .models import ConnState, ModemStatus, SimSlot, SlotKind, OpResult


_CREATE_NO_WINDOW = 0x08000000


def _run(args: list[str], timeout: int = 25) -> str:
    """Запустить консольную команду и вернуть stdout (utf-8, best effort)."""
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            timeout=timeout,
            creationflags=_CREATE_NO_WINDOW,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return f"__ERROR__ {exc}"
    raw = proc.stdout or b""
    for enc in ("utf-8", "cp866", "cp1251"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _kv(text: str) -> dict[str, str]:
    """Разобрать вывод netsh 'Ключ : Значение' в словарь (по последнему появлению)."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k:
                out[k] = v
    return out


class ModemService:
    """Фасад над `netsh mbn`."""

    def __init__(self) -> None:
        self._iface_cache: Optional[tuple[str, str]] = None  # (name, guid)

    # ── интерфейс ────────────────────────────────────────────────────────────
    def _interfaces_raw(self) -> str:
        return _run(["netsh", "mbn", "show", "interfaces"])

    def find_interface(self, refresh: bool = False) -> Optional[tuple[str, str]]:
        if self._iface_cache and not refresh:
            return self._iface_cache
        text = self._interfaces_raw()
        name = self._match(text, r"Name\s*:\s*(.+)")
        guid = self._match(text, r"GUID\s*:\s*(\{[0-9A-Fa-f\-]+\})")
        if name:
            self._iface_cache = (name.strip(), (guid or "").strip())
            return self._iface_cache
        return None

    # ── статус ───────────────────────────────────────────────────────────────
    def status(self) -> ModemStatus:
        st = ModemStatus()
        text = self._interfaces_raw()
        if text.startswith("__ERROR__") or "There is 0 interface" in text or not text.strip():
            st.present = False
            st.error = "WWAN-интерфейс не найден"
            return st

        st.present = True
        st.interface_name = self._match(text, r"Name\s*:\s*(.+)").strip()
        st.interface_guid = self._match(text, r"GUID\s*:\s*(\{[0-9A-Fa-f\-]+\})").strip()
        st.provider = self._match(text, r"Provider Name\s*:\s*(.+)").strip()
        st.manufacturer = self._match(text, r"Manufacturer\s*:\s*(.+)").strip()
        st.model = self._match(text, r"Model\s*:\s*(.+)").strip()
        st.firmware = self._match(text, r"Firmware Version\s*:\s*(.+)").strip()
        st.device_id = self._match(text, r"Device Id\s*:\s*(.+)").strip()
        st.cellular_class = self._match(text, r"Cellular class\s*:\s*(.+)").strip()

        state_raw = self._match(text, r"State\s*:\s*(.+)").strip().lower()
        st.state = {
            "connected": ConnState.CONNECTED,
            "connecting": ConnState.CONNECTING,
            "disconnected": ConnState.DISCONNECTED,
            "not connected": ConnState.DISCONNECTED,
        }.get(state_raw, ConnState.UNKNOWN)

        sig = self._match(text, r"Signal\s*:\s*(\d+)")
        st.signal_percent = int(sig) if sig else 0
        rssi = re.search(r"\((-?\d+)\s*dBm\)", text)
        st.rssi_dbm = int(rssi.group(1)) if rssi else None
        st.roaming = "not roaming" not in self._match(text, r"Roaming\s*:\s*(.+)").lower()

        if st.interface_name:
            self._iface_cache = (st.interface_name, st.interface_guid)
            self._enrich_capability(st)
            self._enrich_slots(st)
        return st

    def _enrich_capability(self, st: ModemStatus) -> None:
        text = _run(["netsh", "mbn", "show", "capability", f"interface={st.interface_name}"])
        if text.startswith("__ERROR__"):
            return
        st.data_class = self._match(text, r"Data class\s*:\s*(.+)").strip()
        sms = self._match(text, r"SMS capability\s*:\s*(.+)").lower()
        st.sms_capable = "receive" in sms or "send" in sms or "pdu" in sms
        st.ussd_capable = "ussd" in text.lower()
        st.multi_sim = "multi sim" in text.lower()
        mac = self._match(text, r"Maximum activation contexts\s*:\s*(\d+)")
        st.max_activation_contexts = int(mac) if mac else 0

    def _enrich_slots(self, st: ModemStatus) -> None:
        text = _run(["netsh", "mbn", "show", "slotstatus", f"interface={st.interface_name}"])
        if text.startswith("__ERROR__"):
            return
        slots: list[SimSlot] = []
        for m in re.finditer(r"Slot index (\d+) has state:\s*(.+)", text):
            idx, state = int(m.group(1)), m.group(2).strip()
            low = state.lower()
            if "esim" in low:
                kind = SlotKind.ESIM
            elif "no sim" in low or "empty" in low or "not present" in low:
                kind = SlotKind.EMPTY
            elif "available" in low or "active" in low:
                kind = SlotKind.PHYSICAL
            else:
                kind = SlotKind.UNKNOWN
            slots.append(SimSlot(index=idx, kind=kind, state=state,
                                 active="active" in low or "available" in low))
        st.slots = slots

    # ── управление ───────────────────────────────────────────────────────────
    def connect(self) -> OpResult:
        iface = self.find_interface()
        if not iface:
            return OpResult(False, "Интерфейс не найден")
        name = iface[0]
        # Пытаемся подключиться сохранённым профилем оператора
        text = _run(["netsh", "mbn", "connect", f"interface={name}",
                     "connmode=name", f"name={self.status().provider or name}"])
        ok = "successfully" in text.lower() or "успешно" in text.lower()
        return OpResult(ok, "Команда подключения отправлена" if ok else text.strip()[:200])

    def disconnect(self) -> OpResult:
        iface = self.find_interface()
        if not iface:
            return OpResult(False, "Интерфейс не найден")
        text = _run(["netsh", "mbn", "disconnect", f"interface={iface[0]}"])
        ok = "successfully" in text.lower() or "успешно" in text.lower()
        return OpResult(ok, "Отключено" if ok else text.strip()[:200])

    def set_slot(self, slot_index: int) -> OpResult:
        iface = self.find_interface()
        if not iface:
            return OpResult(False, "Интерфейс не найден")
        text = _run(["netsh", "mbn", "set", "slotmapping",
                     f"interface={iface[0]}", f"slot={slot_index}"])
        ok = "successfully" in text.lower() or "успешно" in text.lower() or not text.strip()
        return OpResult(ok, f"Активирован слот {slot_index}" if ok else text.strip()[:200])

    def set_radio(self, on: bool) -> OpResult:
        iface = self.find_interface()
        if not iface:
            return OpResult(False, "Интерфейс не найден")
        text = _run(["netsh", "mbn", "set", "radiostate",
                     f"interface={iface[0]}", f"state={'on' if on else 'off'}"])
        ok = "successfully" in text.lower() or "успешно" in text.lower()
        return OpResult(ok, f"Радиомодуль {'включён' if on else 'выключен'}"
                        if ok else text.strip()[:200])

    # ── util ─────────────────────────────────────────────────────────────────
    @staticmethod
    def _match(text: str, pattern: str) -> str:
        m = re.search(pattern, text)
        return m.group(1) if m else ""
