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
from .pdu import parse_deliver

try:
    from winsdk.windows.devices.sms import (
        SmsDevice,
        SmsMessageFilter,
        SmsTextMessage,
        SmsBinaryMessage,
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

    # Таймауты (сек) — WinRT-операции с SMS-хранилищем модема могут зависать
    READ_TIMEOUT = 12.0
    SEND_TIMEOUT = 20.0

    # ── публичный синхронный API ─────────────────────────────────────────────
    def read_all(self) -> list[SmsMessage]:
        if not self.available:
            return []
        try:
            self.last_error = ""
            return asyncio.run(self._guard(self._read_all_async(), self.READ_TIMEOUT))
        except asyncio.TimeoutError:
            self.last_error = "Таймаут чтения SMS (модем занят или слабый сигнал)"
            return []
        except Exception as exc:
            self.last_error = str(exc)
            return []

    def send(self, number: str, text: str) -> OpResult:
        if not self.available:
            return OpResult(False, "WinRT SMS API недоступен")
        try:
            return asyncio.run(self._guard(self._send_async(number, text), self.SEND_TIMEOUT))
        except asyncio.TimeoutError:
            return OpResult(False, "Таймаут отправки SMS")
        except Exception as exc:
            return OpResult(False, f"Ошибка отправки: {exc}")

    def delete(self, message_id: str) -> OpResult:
        return self.delete_many([message_id])

    def delete_many(self, message_ids: list[str]) -> OpResult:
        if not self.available:
            return OpResult(False, "WinRT SMS API недоступен")
        ids = [i for i in message_ids if i]
        if not ids:
            return OpResult(False, "Нет сообщений для удаления")
        try:
            n = asyncio.run(self._guard(self._delete_many_async(ids), self.READ_TIMEOUT))
            return OpResult(True, f"Удалено сообщений: {n}")
        except asyncio.TimeoutError:
            return OpResult(False, "Таймаут удаления SMS")
        except Exception as exc:
            return OpResult(False, f"Ошибка удаления: {exc}")

    @staticmethod
    async def _guard(coro, timeout: float):
        return await asyncio.wait_for(coro, timeout)

    # ── реализация ───────────────────────────────────────────────────────────
    async def _devices(self):
        selector = SmsDevice.get_device_selector()
        # 2-арг перегрузка (aqsFilter, additionalProperties) — иначе winsdk
        # ошибочно выбирает find_all_async(DeviceClass:int) и падает на строке.
        try:
            return await DeviceInformation.find_all_async(selector, [])
        except TypeError:
            return await DeviceInformation.find_all_async(selector)

    async def _open_device(self):
        """Открыть первое пригодное SMS-устройство (пропуская пустые id —
        именно на них зависало чтение)."""
        for info in await self._devices():
            if not info.id:
                continue
            try:
                dev = await SmsDevice.from_id_async(info.id)
            except Exception:
                continue
            if dev is not None:
                return dev
        raise RuntimeError("SMS-устройство не найдено")

    async def _read_all_async(self) -> list[SmsMessage]:
        # перебираем устройства: берём сообщения с первого, что ответит
        for info in await self._devices():
            if not info.id:
                continue
            try:
                dev = await SmsDevice.from_id_async(info.id)
                if dev is None:
                    continue
                raw = await dev.message_store.get_messages_async(SmsMessageFilter.ALL)
            except Exception:
                continue
            items = [self._convert(m) for m in raw]
            return self._reassemble(items)
        return []

    def _reassemble(self, items: list[tuple]) -> list[SmsMessage]:
        """Склеить многочастные (concatenated) SMS в одно сообщение."""
        singles: list[SmsMessage] = []
        groups: dict[tuple, list[tuple[int, SmsMessage]]] = {}
        for msg, ref, total, seq in items:
            if ref is None or total <= 1:
                msg.part_ids = [msg.id]
                singles.append(msg)
            else:
                groups.setdefault((msg.sender, ref), []).append((seq, msg))

        merged: list[SmsMessage] = []
        for (sender, _ref), parts in groups.items():
            parts.sort(key=lambda x: x[0])
            body = "".join(p[1].body for p in parts)
            ids = [p[1].id for p in parts]
            ts = next((p[1].timestamp for p in parts if p[1].timestamp), None)
            merged.append(SmsMessage(
                id=ids[0], sender=sender, body=body, timestamp=ts,
                direction=SmsDirection.INCOMING, part_ids=ids, parts=len(parts)))

        result = singles + merged
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

    async def _delete_many_async(self, ids: list[str]) -> int:
        dev = await self._open_device()
        store = dev.message_store
        n = 0
        # удаляем от больших id к меньшим, чтобы не сдвигать индексы
        for mid in sorted(ids, key=lambda x: int(x) if str(x).isdigit() else 0, reverse=True):
            try:
                await store.delete_message_async(int(mid))
                n += 1
            except Exception:
                continue
        return n

    # ── конвертация WinRT → модель ───────────────────────────────────────────
    def _convert(self, m) -> tuple[SmsMessage, "int|None", int, int]:
        """Вернуть (сообщение, ref, total, seq) — последние три для склейки."""
        mid = str(self._safe(lambda: m.id) or "")

        # 1) текстовое сообщение (если модем отдаёт готовый текст)
        try:
            tm = SmsTextMessage._from(m)
            msg = SmsMessage(
                id=mid,
                sender=str(self._safe(lambda: tm.from_) or "—"),
                body=str(self._safe(lambda: tm.body) or ""),
                timestamp=self._parse_ts(self._safe(lambda: tm.timestamp)),
                direction=SmsDirection.INCOMING,
            )
            return msg, None, 1, 1
        except Exception:
            pass

        # 2) бинарное — сырой PDU (обычный случай для MBIM-модемов)
        try:
            bm = SmsBinaryMessage._from(m)
            data = bytes(bm.get_data())
            pdu = parse_deliver(data.hex())
            msg = SmsMessage(
                id=mid,
                sender=pdu.sender or "—",
                body=pdu.body,
                timestamp=pdu.timestamp,
                direction=SmsDirection.INCOMING,
            )
            return msg, pdu.ref, pdu.total, pdu.seq
        except Exception as exc:
            return (SmsMessage(id=mid, sender="—",
                               body=f"(не удалось декодировать SMS: {exc})",
                               direction=SmsDirection.INCOMING), None, 1, 1)

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
