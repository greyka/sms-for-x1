"""USSD-запросы через Windows WinRT (winsdk).

Позволяет узнать номер, баланс, управлять услугами оператора коротким кодом
(*100#, *110*10# …). Требует зарегистрированного в сети модема.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from .models import UssdResult

try:
    from winsdk.windows.networking.networkoperators import (
        UssdSession,
        UssdMessage,
    )
    _WINRT_OK = True
    _WINRT_ERR = ""
except Exception as exc:  # pragma: no cover
    _WINRT_OK = False
    _WINRT_ERR = str(exc)


_ACTION_CODES = {"actionrequired", "action_required"}


class UssdService:
    def __init__(self) -> None:
        self.available = _WINRT_OK
        self.last_error = _WINRT_ERR

    def send(self, interface_guid: str, code: str, timeout: float = 30.0) -> UssdResult:
        if not self.available:
            return UssdResult(False, error="WinRT USSD API недоступен")
        if not interface_guid:
            return UssdResult(False, error="Не найден GUID WWAN-интерфейса")
        try:
            return asyncio.run(self._send_async(interface_guid, code, timeout))
        except Exception as exc:
            return UssdResult(False, error=f"Ошибка USSD: {exc}")

    async def _send_async(self, guid: str, code: str, timeout: float) -> UssdResult:
        session = None
        try:
            session = UssdSession.create_from_network_interface_id(guid)
            msg = UssdMessage(code)
            op = session.send_message_and_get_reply_async(msg)
            reply = await asyncio.wait_for(self._await(op), timeout=timeout)

            result_code = str(getattr(reply, "result_code", "")).lower()
            reply_msg = getattr(reply, "message", None)
            text = self._extract_text(reply_msg)
            action = any(a in result_code for a in _ACTION_CODES)
            if not text and "no_action" not in result_code and "action" in result_code:
                text = "(оператор ждёт ответа — введите пункт меню)"
            return UssdResult(
                ok=True,
                text=text.strip(),
                result_code=result_code,
                action_needed=action,
            )
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass

    @staticmethod
    async def _await(op):
        # winsdk IAsyncOperation совместим с await напрямую
        return await op

    # ── извлечение текста ответа ─────────────────────────────────────────────
    @classmethod
    def _extract_text(cls, msg) -> str:
        if msg is None:
            return ""
        # 1) готовый текст
        try:
            t = msg.payload_as_text or ""
            if t.strip():
                return t
        except Exception:
            pass
        # 2) сырой payload + декодирование по data_coding_scheme
        try:
            raw = bytes(msg.get_payload())
        except Exception:
            return ""
        if not raw:
            return ""
        dcs = 0
        try:
            dcs = int(getattr(msg, "data_coding_scheme", 0) or 0)
        except Exception:
            dcs = 0
        # UCS2 (16-бит)
        if dcs == 0x48 or (dcs & 0x0C) == 0x08:
            try:
                return raw.decode("utf-16-be", errors="replace").strip()
            except Exception:
                pass
        # GSM 7-bit (упакованные септеты)
        try:
            g = cls._gsm7_decode(raw)
            if g.strip():
                return g.strip()
        except Exception:
            pass
        # запасной вариант
        return raw.decode("latin-1", errors="replace").strip()

    # базовый алфавит GSM 03.38
    _GSM7 = ("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
             "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")

    @classmethod
    def _gsm7_decode(cls, data: bytes) -> str:
        # распаковка 7-битных септетов
        septets, bits, cur = [], 0, 0
        for byte in data:
            cur |= byte << bits
            bits += 8
            while bits >= 7:
                septets.append(cur & 0x7F)
                cur >>= 7
                bits -= 7
        chars = []
        i = 0
        while i < len(septets):
            s = septets[i]
            if s == 0x1B and i + 1 < len(septets):
                i += 1  # расширение — пропускаем для простоты
                chars.append(" ")
            elif s < len(cls._GSM7):
                chars.append(cls._GSM7[s])
            i += 1
        return "".join(chars)
