"""Работа с COM-портом модема: перечисление, автоопределение AT-порта,
отправка AT-команд.

У Quectel в MBIM-режиме AT-порт может отсутствовать (только DM/EDL). Сервис
корректно это обрабатывает: автоопределение просто не найдёт отвечающий порт.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .models import OpResult

try:
    import serial
    from serial.tools import list_ports
    _SERIAL_OK = True
except Exception as exc:  # pragma: no cover
    _SERIAL_OK = False
    _SERIAL_ERR = str(exc)


@dataclass
class PortInfo:
    device: str            # COM4
    description: str       # Quectel … (COM4)
    hwid: str = ""
    likely_at: bool = False


class SerialService:
    def __init__(self) -> None:
        self.available = _SERIAL_OK
        self.selected: Optional[str] = None

    def list_ports(self) -> list[PortInfo]:
        if not self.available:
            return []
        out: list[PortInfo] = []
        for p in list_ports.comports():
            desc = p.description or ""
            likely = any(k in desc.lower() for k in ("at", "modem", "quectel", "application"))
            out.append(PortInfo(device=p.device, description=desc,
                                hwid=p.hwid or "", likely_at=likely))
        # AT-кандидаты выше
        out.sort(key=lambda x: (not x.likely_at, x.device))
        return out

    def autodetect(self, baud: int = 115200) -> OpResult:
        """Перебрать порты, найти отвечающий на 'AT' → 'OK'."""
        if not self.available:
            return OpResult(False, "pyserial недоступен")
        ports = self.list_ports()
        if not ports:
            return OpResult(False, "COM-порты не найдены")
        for p in ports:
            resp = self._probe(p.device, baud)
            if resp is not None and "OK" in resp.upper():
                self.selected = p.device
                return OpResult(True, f"AT-модем найден на {p.device}", payload=p.device)
        return OpResult(
            False,
            "AT-порт не найден. Модем, вероятно, в MBIM-режиме без AT-интерфейса.",
        )

    def send_at(self, command: str, port: Optional[str] = None,
                baud: int = 115200, timeout: float = 3.0) -> OpResult:
        if not self.available:
            return OpResult(False, "pyserial недоступен")
        port = port or self.selected
        if not port:
            return OpResult(False, "COM-порт не выбран")
        try:
            with serial.Serial(port, baud, timeout=timeout) as ser:
                ser.reset_input_buffer()
                ser.write((command.strip() + "\r\n").encode())
                time.sleep(0.35)
                data = ser.read(4096).decode(errors="replace").strip()
            return OpResult(bool(data), data or "(пустой ответ)", payload=data)
        except Exception as exc:
            return OpResult(False, f"Ошибка порта {port}: {exc}")

    def _probe(self, port: str, baud: int) -> Optional[str]:
        try:
            with serial.Serial(port, baud, timeout=1.0) as ser:
                ser.reset_input_buffer()
                ser.write(b"AT\r\n")
                time.sleep(0.3)
                return ser.read(256).decode(errors="replace")
        except Exception:
            return None
