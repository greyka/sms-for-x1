"""Центральный ViewModel: держит сервисы, состояние и рассылает сигналы во View."""
from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from ..core.models import ModemStatus, OpResult, SmsMessage, UssdResult
from ..core.modem_service import ModemService
from ..core.sms_service import SmsService
from ..core.ussd_service import UssdService
from ..core.cell_service import CellService
from ..core.serial_service import SerialService
from .worker import run_async


class AppState(QObject):
    """Единый источник состояния для всех экранов."""

    # модем
    statusChanged = Signal(ModemStatus)
    statusLoading = Signal(bool)
    # sms
    messagesChanged = Signal(list)          # list[SmsMessage]
    messagesLoading = Signal(bool)
    smsSent = Signal(OpResult)
    # ussd
    ussdReply = Signal(UssdResult)
    ussdLoading = Signal(bool)
    # serial / COM
    portsChanged = Signal(list)             # list[PortInfo]
    atResult = Signal(OpResult)
    # общие уведомления
    notify = Signal(str, str)               # (level, text): info|success|warning|error

    POLL_MS = 5000

    def __init__(self) -> None:
        super().__init__()
        self.modem = ModemService()
        self.sms = SmsService()
        self.ussd = UssdService()
        self.cell = CellService()
        self.serial = SerialService()

        self._status: ModemStatus = ModemStatus()
        self._messages: list[SmsMessage] = []

        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self.refresh_status)

    # ── свойства ─────────────────────────────────────────────────────────────
    @property
    def status_snapshot(self) -> ModemStatus:
        return self._status

    @property
    def messages_snapshot(self) -> list[SmsMessage]:
        return list(self._messages)

    # ── жизненный цикл ───────────────────────────────────────────────────────
    def start(self) -> None:
        self.refresh_status()
        self.refresh_messages()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    # ── модем ────────────────────────────────────────────────────────────────
    def refresh_status(self) -> None:
        self.statusLoading.emit(True)
        run_async(
            self._full_status,
            on_result=self._on_status,
            on_error=lambda e: self.notify.emit("error", f"Статус: {e}"),
            on_finished=lambda: self.statusLoading.emit(False),
        )

    def _full_status(self) -> ModemStatus:
        """Статус модема + данные обслуживающей соты (в одном фоновом вызове)."""
        st = self.modem.status()
        if st.present and st.state.value == "connected":
            try:
                st.cell = self.cell.get()
            except Exception:
                pass
        return st

    def _on_status(self, status: ModemStatus) -> None:
        self._status = status
        self.statusChanged.emit(status)

    def set_radio(self, on: bool) -> None:
        run_async(self.modem.set_radio, on,
                  on_result=self._on_op, on_finished=self.refresh_status)

    def set_slot(self, index: int) -> None:
        run_async(self.modem.set_slot, index,
                  on_result=self._on_op, on_finished=self.refresh_status)

    def connect_modem(self) -> None:
        run_async(self.modem.connect, on_result=self._on_op, on_finished=self.refresh_status)

    def disconnect_modem(self) -> None:
        run_async(self.modem.disconnect, on_result=self._on_op, on_finished=self.refresh_status)

    def _on_op(self, res: OpResult) -> None:
        self.notify.emit("success" if res.ok else "error", res.message)

    # ── sms ──────────────────────────────────────────────────────────────────
    def refresh_messages(self) -> None:
        self.messagesLoading.emit(True)
        run_async(
            self.sms.read_all,
            on_result=self._on_messages,
            on_error=lambda e: self.notify.emit("warning", f"SMS: {e}"),
            on_finished=lambda: self.messagesLoading.emit(False),
        )

    def _on_messages(self, msgs: list[SmsMessage]) -> None:
        self._messages = msgs
        self.messagesChanged.emit(msgs)

    def send_sms(self, number: str, text: str) -> None:
        def done(res: OpResult):
            self.smsSent.emit(res)
            self._on_op(res)
            if res.ok:
                self.refresh_messages()
        run_async(self.sms.send, number, text, on_result=done)

    def delete_sms(self, message_id: str) -> None:
        run_async(self.sms.delete, message_id,
                  on_result=self._on_op, on_finished=self.refresh_messages)

    # ── ussd ─────────────────────────────────────────────────────────────────
    def send_ussd(self, code: str) -> None:
        guid = self._status.interface_guid
        self.ussdLoading.emit(True)
        run_async(
            self.ussd.send, guid, code,
            on_result=self.ussdReply.emit,
            on_error=lambda e: self.ussdReply.emit(UssdResult(False, error=e)),
            on_finished=lambda: self.ussdLoading.emit(False),
        )

    # ── serial / COM ─────────────────────────────────────────────────────────
    def refresh_ports(self) -> None:
        run_async(self.serial.list_ports, on_result=self.portsChanged.emit)

    def select_port(self, device: str) -> None:
        self.serial.selected = device or None

    def autodetect_port(self) -> None:
        def done(res: OpResult):
            self.atResult.emit(res)
            self._on_op(res)
            self.refresh_ports()
        run_async(self.serial.autodetect, on_result=done)

    def send_at(self, command: str) -> None:
        run_async(self.serial.send_at, command, on_result=self.atResult.emit)
