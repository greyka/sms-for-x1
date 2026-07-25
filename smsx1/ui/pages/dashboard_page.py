"""Обзор: статус подключения, оператор, сигнал, SIM-слоты, быстрые действия."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from qfluentwidgets import (
    BodyLabel, CaptionLabel, FluentIcon as FIF, IconWidget, PrimaryPushButton,
    PushButton, StrongBodyLabel, TransparentToolButton,
)

from ...config import THEME
from ...core.models import ConnState, ModemStatus, SlotKind
from ..components import GlassCard, MetricRow, SignalMeter, StatCard, StatusBadge
from ..components.section import SectionHeader
from .base_page import BasePage

P = THEME.palette
S = THEME.spacing
R = THEME.radius


class DashboardPage(BasePage):
    quickUssd = Signal(str)   # запрос быстрого USSD (перехватывает главное окно)

    def __init__(self, state, parent=None):
        super().__init__("dashboardPage", "Обзор",
                         "Состояние WWAN-модема в реальном времени",
                         crumbs=["SMS for X1", "Обзор"], parent=parent)
        self.state = state

        # ── строка статуса/действий ──
        top = QHBoxLayout()
        self.badge = StatusBadge("Загрузка…", "muted", pulse=True)
        self.refresh_btn = TransparentToolButton(FIF.SYNC, self)
        self.refresh_btn.setToolTip("Обновить статус")
        self.refresh_btn.clicked.connect(self.state.refresh_status)
        top.addWidget(self.badge)
        top.addStretch(1)
        top.addWidget(self.refresh_btn)
        self.body().addLayout(top)

        # ── быстрые действия ──
        self.body().addWidget(self._quick_actions())

        # ── карточки-метрики ──
        grid = QGridLayout()
        grid.setSpacing(S.lg)
        self.card_state = StatCard(FIF.WIFI, "Подключение", "—", P.primary)
        self.card_operator = StatCard(FIF.CERTIFICATE, "Оператор", "—", P.violet)
        self.card_signal = StatCard(FIF.SPEED_HIGH, "Сигнал", "—", P.cyan)
        self.card_tech = StatCard(FIF.GLOBE, "Технология", "—", P.emerald)
        grid.addWidget(self.card_state, 0, 0)
        grid.addWidget(self.card_operator, 0, 1)
        grid.addWidget(self.card_signal, 0, 2)
        grid.addWidget(self.card_tech, 0, 3)
        for c in range(4):
            grid.setColumnStretch(c, 1)
        self.body().addLayout(grid)

        # ── большая карточка «Сигнал» + «Устройство» ──
        row = QHBoxLayout()
        row.setSpacing(S.lg)
        row.addWidget(self._signal_card(), 1)
        row.addWidget(self._device_card(), 1)
        self.body().addLayout(row)

        # ── SIM-слоты ──
        self.body().addWidget(SectionHeader("SIM-карты", "Физический слот и eSIM"))
        self.slots_row = QHBoxLayout()
        self.slots_row.setSpacing(S.lg)
        self.body().addLayout(self.slots_row)

        self.state.statusChanged.connect(self._on_status)

    # ── карточки ──
    def _signal_card(self) -> GlassCard:
        card = GlassCard(radius=R.md, padding=S.xl, interactive=False)
        head = QHBoxLayout()
        head.addWidget(SectionHeader("Уровень сигнала", "Обновляется каждые 5 секунд"))
        head.addStretch(1)
        self.meter = SignalMeter(0)
        head.addWidget(self.meter, 0, Qt.AlignmentFlag.AlignBottom)
        card.body().addLayout(head)

        self.signal_pct = StrongBodyLabel("—", card)
        self.signal_pct.setStyleSheet("font-size: 40px; font-weight: 700;")
        self.signal_quality = CaptionLabel("", card)
        self.signal_quality.setStyleSheet(f"color: {P.text_secondary};")
        card.body().addSpacing(S.md)
        card.body().addWidget(self.signal_pct)
        card.body().addWidget(self.signal_quality)
        return card

    def _device_card(self) -> GlassCard:
        card = GlassCard(radius=R.md, padding=S.xl, interactive=False)
        card.body().addWidget(SectionHeader("Устройство", "Параметры модема"))
        card.body().addSpacing(S.sm)
        self.m_model = MetricRow("Модель", "—")
        self.m_fw = MetricRow("Прошивка", "—", mono=True)
        self.m_imei = MetricRow("IMEI", "—", mono=True)
        self.m_iface = MetricRow("Интерфейс", "—")
        for m in (self.m_model, self.m_fw, self.m_imei, self.m_iface):
            card.body().addWidget(m)
        return card

    def _slot_card(self, title: str, subtitle: str, accent: str,
                   active: bool) -> GlassCard:
        card = GlassCard(radius=R.md, padding=S.lg)
        row = QHBoxLayout()
        holder = IconWidget(FIF.PHONE if accent == P.primary else FIF.VPN, card)
        holder.setFixedSize(20, 20)
        col = QVBoxLayout()
        col.setSpacing(2)
        t = StrongBodyLabel(title, card)
        st = CaptionLabel(subtitle, card)
        st.setStyleSheet(f"color: {P.text_secondary};")
        col.addWidget(t)
        col.addWidget(st)
        row.addWidget(holder)
        row.addSpacing(6)
        row.addLayout(col)
        row.addStretch(1)
        badge = StatusBadge("Активна" if active else "Ожидание",
                            "success" if active else "muted", pulse=active)
        row.addWidget(badge)
        card.body().addLayout(row)
        return card

    # ── быстрые действия ──
    def _quick_actions(self) -> GlassCard:
        card = GlassCard(radius=R.md, padding=S.lg, interactive=False)
        row = QHBoxLayout()
        row.setSpacing(S.md)
        title = StrongBodyLabel("Быстрые действия", card)
        title.setStyleSheet("font-size: 15px; font-weight: 700;")
        row.addWidget(title)
        row.addStretch(1)

        num_btn = PrimaryPushButton(FIF.PHONE, "Узнать номер", card)
        num_btn.clicked.connect(lambda: self.quickUssd.emit("*110*10#"))
        bal_btn = PushButton(FIF.MARKET, "Баланс", card)
        bal_btn.clicked.connect(lambda: self.quickUssd.emit("*102#"))
        sms_btn = PushButton(FIF.SYNC, "Обновить SMS", card)
        sms_btn.clicked.connect(self.state.refresh_messages)

        row.addWidget(bal_btn)
        row.addWidget(sms_btn)
        row.addWidget(num_btn)
        card.body().addLayout(row)
        return card

    # ── обновление ──
    def _on_status(self, st: ModemStatus) -> None:
        # бейдж
        level = {
            ConnState.CONNECTED: "success",
            ConnState.CONNECTING: "warning",
            ConnState.DISCONNECTED: "error",
            ConnState.UNKNOWN: "muted",
        }[st.state]
        self.badge.set_status(st.state.label, level, pulse=st.state == ConnState.CONNECTED)

        self.card_state.set_value(st.state.label)
        self.card_state.set_sub("В сети" if st.state == ConnState.CONNECTED else "")
        self.card_operator.set_value(st.provider or "—")
        self.card_operator.set_sub("Роуминг" if st.roaming else "Домашняя сеть")
        self.card_signal.set_value(f"{st.signal_percent}%")
        self.card_signal.set_sub(st.signal_label,
                                 P.success if st.signal_bars >= 3 else
                                 P.warning if st.signal_bars == 2 else P.error)
        self.card_tech.set_value((st.data_class.split(",")[-1].strip() or st.cellular_class or "—"))
        self.card_tech.set_sub(st.cellular_class)

        self.meter.set_level(st.signal_bars)
        self.signal_pct.setText(f"{st.signal_percent}%")
        rssi = f"  ·  {st.rssi_dbm} dBm" if st.rssi_dbm is not None else ""
        self.signal_quality.setText(f"{st.signal_label}{rssi}")

        self.m_model.set_value(st.model or "—")
        self.m_fw.set_value(st.firmware or "—")
        self.m_imei.set_value(st.device_id or "—")
        self.m_iface.set_value(st.interface_name or "—")

        # слоты
        while self.slots_row.count():
            item = self.slots_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not st.slots:
            self.slots_row.addWidget(self._slot_card("SIM", "Нет данных", P.primary, False))
        for slot in st.slots:
            accent = P.primary if slot.kind == SlotKind.PHYSICAL else P.violet
            self.slots_row.addWidget(
                self._slot_card(slot.title, slot.state, accent, slot.active))
        self.slots_row.addStretch(1)
