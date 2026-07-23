"""Сервис модема: статус, слоты, режимы через `netsh mbn`.

Важно: netsh локализует названия полей (на русской Windows — «Имя», «Состояние»,
«Сигнал» …). Поэтому парсер двуязычный: сопоставляет и английские, и русские
метки и значения.
"""
from __future__ import annotations

import re
import subprocess
from typing import Optional

from .models import ConnState, ModemStatus, SimSlot, SlotKind, OpResult

_CREATE_NO_WINDOW = 0x08000000


def _run(args: list[str], timeout: int = 25) -> str:
    """Запустить консольную команду и вернуть stdout (best-effort декод)."""
    try:
        proc = subprocess.run(
            args, capture_output=True, timeout=timeout,
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


def _find(text: str, *patterns: str) -> str:
    """Первое совпадение среди нескольких (двуязычных) шаблонов."""
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


class ModemService:
    """Фасад над `netsh mbn` (EN/RU)."""

    def __init__(self) -> None:
        self._iface_cache: Optional[tuple[str, str]] = None

    # ── интерфейс ────────────────────────────────────────────────────────────
    def _interfaces_raw(self) -> str:
        return _run(["netsh", "mbn", "show", "interfaces"])

    def find_interface(self, refresh: bool = False) -> Optional[tuple[str, str]]:
        if self._iface_cache and not refresh:
            return self._iface_cache
        text = self._interfaces_raw()
        name = _find(text, r"(?:^|\n)\s*Name\s*:\s*(.+)", r"(?:^|\n)\s*Имя\s*:\s*(.+)")
        guid = _find(text, r"GUID\s*:\s*(\{[0-9A-Fa-f\-]+\})")
        if name:
            self._iface_cache = (name.strip(), guid.strip())
            return self._iface_cache
        return None

    # ── статус ───────────────────────────────────────────────────────────────
    def status(self) -> ModemStatus:
        st = ModemStatus()
        text = self._interfaces_raw()
        if (text.startswith("__ERROR__") or not text.strip()
                or re.search(r"0 interface|0 интерфейс", text)):
            st.present = False
            st.error = "WWAN-интерфейс не найден"
            return st

        st.present = True
        st.interface_name = _find(text, r"(?:^|\n)\s*Name\s*:\s*(.+)",
                                  r"(?:^|\n)\s*Имя\s*:\s*(.+)")
        st.interface_guid = _find(text, r"GUID\s*:\s*(\{[0-9A-Fa-f\-]+\})")
        st.provider = _find(text, r"Provider Name\s*:\s*(.+)", r"Имя поставщика\s*:\s*(.+)")
        st.manufacturer = _find(text, r"Manufacturer\s*:\s*(.+)", r"Производитель\s*:\s*(.+)")
        st.model = _find(text, r"Model\s*:\s*(.+)", r"Модель\s*:\s*(.+)")
        st.firmware = _find(text, r"Firmware Version\s*:\s*(.+)",
                            r"Версия встроенного ПО\s*:?\s*:\s*(.+)",
                            r"Версия встроенного ПО[^\n:]*:\s*(.+)")
        st.device_id = _find(text, r"Device Id\s*:\s*(.+)", r"Код устройства\s*:\s*(.+)")
        st.cellular_class = _find(text, r"Cellular class\s*:\s*(.+)",
                                  r"Класс мобильного устройства\s*:\s*(.+)")

        state_raw = _find(text, r"State\s*:\s*(.+)", r"Состояние\s*:\s*(.+)").lower()
        st.state = self._parse_state(state_raw)

        sig = _find(text, r"Signal\s*:\s*(\d+)", r"Сигнал\s*:\s*(\d+)")
        st.signal_percent = int(sig) if sig else 0
        rssi = re.search(r"\((-?\d+)\s*(?:dBm|дБм)\)", text)
        st.rssi_dbm = int(rssi.group(1)) if rssi else None

        roam = _find(text, r"Roaming\s*:\s*(.+)", r"Роуминг\s*:\s*(.+)").lower()
        st.roaming = not any(k in roam for k in ("not roaming", "нет роуминга", "home", "домаш"))

        if st.interface_name:
            self._iface_cache = (st.interface_name, st.interface_guid)
            self._enrich_capability(st)
            self._enrich_slots(st)
        return st

    @staticmethod
    def _parse_state(val: str) -> ConnState:
        v = val.lower()
        if any(k in v for k in ("not connected", "disconnected", "не подключен", "отключен")):
            return ConnState.DISCONNECTED
        if any(k in v for k in ("connecting", "подключение")):
            return ConnState.CONNECTING
        if any(k in v for k in ("connected", "подключено", "подключен")):
            return ConnState.CONNECTED
        return ConnState.UNKNOWN

    def _enrich_capability(self, st: ModemStatus) -> None:
        text = _run(["netsh", "mbn", "show", "capability", f"interface={st.interface_name}"])
        if text.startswith("__ERROR__"):
            return
        st.data_class = _find(text, r"Data class\s*:\s*(.+)", r"Класс данных\s*:\s*(.+)")
        sms = _find(text, r"SMS capability\s*:\s*(.+)",
                    r"Возможности работы с SMS\s*:\s*(.+)").lower()
        st.sms_capable = any(k in sms for k in ("receive", "send", "pdu", "прием", "приём", "передача"))
        low = text.lower()
        st.ussd_capable = "ussd" in low
        st.multi_sim = ("multi sim" in low or "несколько sim" in low)
        mac = _find(text, r"Maximum activation contexts\s*:\s*(\d+)",
                    r"[Мм]аксимальное.*?контекст\w*\s*:\s*(\d+)",
                    r"активн\w+ контекст\w*\s*:\s*(\d+)")
        st.max_activation_contexts = int(mac) if mac else 0

    def _enrich_slots(self, st: ModemStatus) -> None:
        text = _run(["netsh", "mbn", "show", "slotstatus", f"interface={st.interface_name}"])
        if text.startswith("__ERROR__"):
            return
        slots: list[SimSlot] = []
        pattern = r"(?:Slot index (\d+) has state:|Состояние слота с индексом (\d+):)\s*(.+)"
        for m in re.finditer(pattern, text):
            idx = int(m.group(1) or m.group(2))
            state = m.group(3).strip()
            low = state.lower()
            if "esim" in low or "есим" in low:
                kind = SlotKind.ESIM
            elif any(k in low for k in ("no sim", "empty", "not present",
                                        "отсутству", "пуст", "нет sim")):
                kind = SlotKind.EMPTY
            elif any(k in low for k in ("available", "active", "доступ", "активн")):
                kind = SlotKind.PHYSICAL
            else:
                kind = SlotKind.UNKNOWN
            active = any(k in low for k in ("active", "available", "доступ", "активн"))
            slots.append(SimSlot(index=idx, kind=kind, state=state, active=active))
        st.slots = slots

    # ── управление ───────────────────────────────────────────────────────────
    def profiles(self, iface_name: str) -> list[str]:
        """Список сохранённых профилей подключения интерфейса."""
        text = _run(["netsh", "mbn", "show", "profiles", f"interface={iface_name}"])
        if text.startswith("__ERROR__"):
            return []
        out = []
        for line in text.splitlines():
            s = line.strip()
            # имена профилей — отступ, без ':' и не разделитель
            if s and ":" not in s and not s.startswith("-"):
                out.append(s)
        return out

    def connect(self) -> OpResult:
        iface = self.find_interface()
        if not iface:
            return OpResult(False, "Интерфейс не найден")
        name = iface[0]
        profs = self.profiles(name)
        if not profs:
            return OpResult(False, "Нет сохранённого профиля подключения для этого модема")
        text = _run(["netsh", "mbn", "connect", f"interface={name}",
                     "connmode=name", f"name={profs[0]}"])
        low = text.lower()
        if "0x139f" in low or "already" in low or "уже под" in low:
            return OpResult(True, "Модем уже подключён")
        return OpResult(self._ok(text), self._msg(text, "Команда подключения отправлена"))

    def disconnect(self) -> OpResult:
        iface = self.find_interface()
        if not iface:
            return OpResult(False, "Интерфейс не найден")
        text = _run(["netsh", "mbn", "disconnect", f"interface={iface[0]}"])
        return OpResult(self._ok(text), self._msg(text, "Отключено"))

    def set_slot(self, slot_index: int) -> OpResult:
        iface = self.find_interface()
        if not iface:
            return OpResult(False, "Интерфейс не найден")
        text = _run(["netsh", "mbn", "set", "slotmapping",
                     f"interface={iface[0]}", f"slot={slot_index}"])
        return OpResult(self._ok(text, allow_empty=True),
                        self._msg(text, f"Активирован слот {slot_index}"))

    def set_radio(self, on: bool) -> OpResult:
        iface = self.find_interface()
        if not iface:
            return OpResult(False, "Интерфейс не найден")
        text = _run(["netsh", "mbn", "set", "radiostate",
                     f"interface={iface[0]}", f"state={'on' if on else 'off'}"])
        return OpResult(self._ok(text),
                        self._msg(text, f"Радиомодуль {'включён' if on else 'выключен'}"))

    # ── util ─────────────────────────────────────────────────────────────────
    # netsh mbn для connect/disconnect не всегда пишет «успешно», зато явно
    # сообщает об ошибке. Поэтому успех = отсутствие маркеров ошибки.
    _ERROR_MARKERS = ("ошибк", "сбой", "не удалось", "error", "failed",
                      "cannot", "invalid", "0x")

    @staticmethod
    def _ok(text: str, allow_empty: bool = True) -> bool:
        low = text.lower()
        if any(k in low for k in ModemService._ERROR_MARKERS):
            return False
        return True

    @staticmethod
    def _msg(text: str, ok_msg: str) -> str:
        low = text.lower()
        if any(k in low for k in ModemService._ERROR_MARKERS):
            clean = " ".join(text.split())
            # частый случай: уже подключено
            if "0x139f" in low or "already" in low or "уже под" in low:
                return "Модем уже подключён"
            return clean[:200] if clean else "Команда завершилась с ошибкой"
        return ok_msg
