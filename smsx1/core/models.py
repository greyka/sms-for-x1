"""Модели данных приложения (dataclasses)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ConnState(str, Enum):
    CONNECTED = "connected"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        return {
            ConnState.CONNECTED: "Подключено",
            ConnState.CONNECTING: "Подключение…",
            ConnState.DISCONNECTED: "Не подключено",
            ConnState.UNKNOWN: "Неизвестно",
        }[self]


class SlotKind(str, Enum):
    PHYSICAL = "physical"
    ESIM = "esim"
    EMPTY = "empty"
    UNKNOWN = "unknown"


@dataclass
class SimSlot:
    index: int
    kind: SlotKind = SlotKind.UNKNOWN
    state: str = ""
    active: bool = False

    @property
    def title(self) -> str:
        base = {
            SlotKind.PHYSICAL: "Физическая SIM",
            SlotKind.ESIM: "eSIM",
            SlotKind.EMPTY: "Пустой слот",
            SlotKind.UNKNOWN: "SIM",
        }[self.kind]
        return f"{base} · слот {self.index}"


@dataclass
class CellInfo:
    """Данные обслуживающей базовой станции (соты)."""
    tech: str = ""                 # LTE / 5G NR / WCDMA / GSM
    cell_id: Optional[int] = None  # глобальный идентификатор соты
    pci: Optional[int] = None      # physical cell id
    earfcn: Optional[int] = None   # частотный канал
    band: str = ""                 # рассчитанный диапазон (напр. "Band 3 (1800)")
    tac: Optional[int] = None      # tracking area code
    rsrp_dbm: Optional[float] = None
    rsrq_db: Optional[float] = None
    sinr_db: Optional[float] = None
    available: bool = False        # удалось ли получить данные
    note: str = ""

    @property
    def quality_label(self) -> str:
        """Оценка качества по RSRP (LTE)."""
        r = self.rsrp_dbm
        if r is None:
            return "—"
        if r >= -80:
            return "Отличное"
        if r >= -90:
            return "Хорошее"
        if r >= -100:
            return "Среднее"
        if r >= -110:
            return "Слабое"
        return "Очень слабое"

    @property
    def quality_ratio(self) -> float:
        """RSRP → 0..1 (для прогресс-индикатора)."""
        r = self.rsrp_dbm
        if r is None:
            return 0.0
        # -120 dBm → 0, -70 dBm → 1
        return max(0.0, min(1.0, (r + 120) / 50))


@dataclass
class ModemStatus:
    """Снимок состояния модема (из `netsh mbn`)."""
    present: bool = False
    interface_name: str = ""
    interface_guid: str = ""
    state: ConnState = ConnState.UNKNOWN
    provider: str = ""
    manufacturer: str = ""
    model: str = ""
    firmware: str = ""
    device_id: str = ""            # IMEI
    cellular_class: str = ""
    data_class: str = ""           # UMTS, LTE …
    signal_percent: int = 0
    rssi_dbm: Optional[int] = None
    roaming: bool = False
    sms_capable: bool = False
    ussd_capable: bool = False
    multi_sim: bool = False
    max_activation_contexts: int = 0
    slots: list[SimSlot] = field(default_factory=list)
    cell: CellInfo = field(default_factory=CellInfo)
    error: str = ""

    @property
    def signal_bars(self) -> int:
        """0..4 деления по проценту сигнала."""
        p = self.signal_percent
        if p <= 0:
            return 0
        if p < 20:
            return 1
        if p < 45:
            return 2
        if p < 70:
            return 3
        return 4

    @property
    def signal_label(self) -> str:
        p = self.signal_percent
        if p <= 0:
            return "Нет сигнала"
        if p < 20:
            return "Очень слабый"
        if p < 45:
            return "Слабый"
        if p < 70:
            return "Средний"
        return "Отличный"


class SmsDirection(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    DRAFT = "draft"


@dataclass
class SmsMessage:
    id: str
    sender: str
    body: str
    timestamp: Optional[datetime] = None
    direction: SmsDirection = SmsDirection.INCOMING
    is_read: bool = False
    part_ids: list[str] = field(default_factory=list)  # id всех сегментов (для удаления)
    parts: int = 1                                      # сколько сегментов склеено

    @property
    def time_label(self) -> str:
        if not self.timestamp:
            return "—"
        return self.timestamp.strftime("%d.%m.%Y %H:%M")

    @property
    def preview(self) -> str:
        one = " ".join(self.body.split())
        return one if len(one) <= 64 else one[:63] + "…"


@dataclass
class UssdResult:
    ok: bool
    text: str = ""
    result_code: str = ""
    action_needed: bool = False    # сессия ждёт ответа (меню)
    error: str = ""


@dataclass
class OpResult:
    """Универсальный результат операции для UI."""
    ok: bool
    message: str = ""
    payload: object = None
