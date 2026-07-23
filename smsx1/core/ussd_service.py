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
            text = ""
            reply_msg = getattr(reply, "message", None)
            if reply_msg is not None:
                text = getattr(reply_msg, "payload_as_text", "") or ""
            action = any(a in result_code for a in _ACTION_CODES)
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
