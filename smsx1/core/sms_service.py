"""Чтение и отправка SMS через Windows WinRT (winsdk).

Модем Quectel в MBIM-режиме не отдаёт AT-порт, поэтому SMS идут через
Windows.Devices.Sms. Все операции обёрнуты в синхронные методы (внутри
asyncio) — их удобно звать из рабочих потоков Qt.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from .models import SmsDirection, SmsMessage, OpResult

try:
    from winsdk.windows.devices.sms import (
        SmsDevice,
        SmsMessageFilter,
        SmsTextMessage,
    )
    from winsdk.windows.devices.enumeration import DeviceInformation
    _WINRT_OK = True
    _WINRT_ERR = ""
except Exception as exc:  # pragma: no cover
    _WINRT_OK = False
    _WINRT_ERR = str(exc)


class SmsService:
    """Доступ к хранилищу SMS модема."""

    def __init__(self) -> None:
        self.available = _WINRT_OK
        self.last_error = _WINRT_ERR

    # ── публичный синхронный API ─────────────────────────────────────────────
    def read_all(self) -> list[SmsMessage]:
        if not self.available:
            return []
        try:
            return asyncio.run(self._read_all_async())
        except Exception as exc:
            self.last_error = str(exc)
            return []

    def send(self, number: str, text: str) -> OpResult:
        if not self.available:
            return OpResult(False, "WinRT SMS API недоступен")
        try:
            return asyncio.run(self._send_async(number, text))
        except Exception as exc:
            return OpResult(False, f"Ошибка отправки: {exc}")

    def delete(self, message_id: str) -> OpResult:
        if not self.available:
            return OpResult(False, "WinRT SMS API недоступен")
        try:
            return asyncio.run(self._delete_async(message_id))
        except Exception as exc:
            return OpResult(False, f"Ошибка удаления: {exc}")

    # ── реализация ───────────────────────────────────────────────────────────
    async def _open_device(self):
        selector = SmsDevice.get_device_selector()
        devices = await DeviceInformation.find_all_async(selector)
        last = None
        for info in devices:
            try:
                dev = await SmsDevice.from_id_async(info.id)
                if dev is not None:
                    return dev
            except Exception as exc:  # часть селекторов не открывается
                last = exc
                continue
        if last:
            raise last
        raise RuntimeError("SMS-устройство не найдено")

    async def _read_all_async(self) -> list[SmsMessage]:
        dev = await self._open_device()
        store = dev.message_store
        raw = await store.get_messages_async(SmsMessageFilter.ALL)
        result: list[SmsMessage] = []
        for m in raw:
            result.append(self._convert(m))
        result.sort(key=lambda x: x.timestamp or datetime.min, reverse=True)
        return result

    async def _send_async(self, number: str, text: str) -> OpResult:
        dev = await self._open_device()
        msg = SmsTextMessage()
        # .to — список получателей
        try:
            msg.to.append(number)
        except Exception:
            try:
                msg.to = [number]
            except Exception:
                pass
        msg.body = text
        await dev.send_message_async(msg)
        return OpResult(True, "Сообщение отправлено")

    async def _delete_async(self, message_id: str) -> OpResult:
        dev = await self._open_device()
        await dev.message_store.delete_message_async(int(message_id))
        return OpResult(True, "Сообщение удалено")

    # ── конвертация WinRT → модель ───────────────────────────────────────────
    def _convert(self, m) -> SmsMessage:
        tm = getattr(m, "text_message", None) or m
        sender = self._safe(lambda: tm.from_) or self._safe(lambda: tm.to) or "—"
        body = self._safe(lambda: tm.body) or ""
        ts = self._parse_ts(self._safe(lambda: tm.timestamp))
        mid = str(self._safe(lambda: m.id) or "")
        is_read = bool(self._safe(lambda: m.is_read))
        return SmsMessage(
            id=mid,
            sender=str(sender),
            body=str(body),
            timestamp=ts,
            direction=SmsDirection.INCOMING,
            is_read=is_read,
        )

    @staticmethod
    def _safe(fn):
        try:
            return fn()
        except Exception:
            return None

    @staticmethod
    def _parse_ts(value) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.astimezone() if value.tzinfo else value
        # winsdk может отдать DateTimeOffset-подобный объект
        try:
            return datetime.fromtimestamp(value.timestamp(), tz=timezone.utc).astimezone()
        except Exception:
            return None
