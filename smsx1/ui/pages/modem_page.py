"""Модем: управление радио, подключением, переключение SIM-слотов, возможности."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from qfluentwidgets import (
    BodyLabel, CaptionLabel, CheckBox, ComboBox, FluentIcon as FIF, IconWidget,
    PrimaryPushButton, PushButton, StrongBodyLabel, SwitchButton,
)

from ...config import THEME
from ...core.models import ConnState, ModemStatus, SlotKind
from ..components import GlassCard, MetricRow, StatusBadge
from ..components.section import SectionHeader, Divider
from .base_page import BasePage

P = THEME.palette
S = THEME.spacing
R = THEME.radius


class _Toggle(QWidget):
    """Строка с названием, описанием и переключателем."""

    def __init__(self, title: str, subtitle: str, checked: bool, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 8)
        col = QVBoxLayout()
        col.setSpacing(2)
        t = StrongBodyLabel(title, self)
        s = CaptionLabel(subtitle, self)
        s.setStyleSheet(f"color: {P.text_secondary};")
        col.addWidget(t)
        col.addWidget(s)
        self.switch = SwitchButton(self)
        self.switch.setChecked(checked)
        lay.addLayout(col)
        lay.addStretch(1)
        lay.addWidget(self.switch)


class ModemPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__("modemPage", "Модем",
                         "Режимы работы, подключение и SIM-слоты",
                         crumbs=["SMS for X1", "Модем"], parent=parent)
        self.state = state

        # ── управление подключением ──
        conn = GlassCard(radius=R.md, padding=S.xl, interactive=False)
        head = QHBoxLayout()
        head.addWidget(SectionHeader("Подключение", "Управление сессией передачи данных"))
        head.addStretch(1)
        self.conn_badge = StatusBadge("—", "muted")
        head.addWidget(self.conn_badge)
        conn.body().addLayout(head)
        conn.body().addSpacing(S.sm)

        self.radio = _Toggle("Радиомодуль", "Полностью включает или выключает сотовый модем", True)
        self.radio.switch.checkedChanged.connect(self.state.set_radio)
        conn.body().addWidget(self.radio)
        conn.body().addWidget(Divider())

        btns = QHBoxLayout()
        btns.setSpacing(S.md)
        self.connect_btn = PrimaryPushButton(FIF.LINK, "Подключить", self)
        self.connect_btn.clicked.connect(self.state.connect_modem)
        self.disconnect_btn = PushButton(FIF.CANCEL, "Отключить", self)
        self.disconnect_btn.clicked.connect(self.state.disconnect_modem)
        btns.addWidget(self.connect_btn)
        btns.addWidget(self.disconnect_btn)
        btns.addStretch(1)
        conn.body().addSpacing(S.sm)
        conn.body().addLayout(btns)
        self.body().addWidget(conn)

        # ── SIM-слоты ──
        sim = GlassCard(radius=R.md, padding=S.xl, interactive=False)
        sim.body().addWidget(SectionHeader("SIM-карты", "Выбор активного слота (Multi-SIM)"))
        sim.body().addSpacing(S.sm)
        row = QHBoxLayout()
        row.setSpacing(S.md)
        row.addWidget(BodyLabel("Активный слот", self))
        self.slot_combo = ComboBox(self)
        self.slot_combo.setFixedWidth(240)
        self.apply_slot_btn = PushButton(FIF.ACCEPT, "Применить", self)
        self.apply_slot_btn.clicked.connect(self._apply_slot)
        row.addStretch(1)
        row.addWidget(self.slot_combo)
        row.addWidget(self.apply_slot_btn)
        sim.body().addLayout(row)
        self.body().addWidget(sim)

        # ── возможности ──
        caps = GlassCard(radius=R.md, padding=S.xl, interactive=False)
        caps.body().addWidget(SectionHeader("Возможности", "Что поддерживает модем"))
        caps.body().addSpacing(S.sm)
        self.cap_sms = MetricRow("SMS (приём/отправка)", "—")
        self.cap_ussd = MetricRow("USSD", "—")
        self.cap_multisim = MetricRow("Multi-SIM", "—")
        self.cap_data = MetricRow("Технологии данных", "—")
        self.cap_ctx = MetricRow("Макс. контекстов", "—")
        for m in (self.cap_sms, self.cap_ussd, self.cap_multisim, self.cap_data, self.cap_ctx):
            caps.body().addWidget(m)
        self.body().addWidget(caps)

        self.state.statusChanged.connect(self._on_status)

    def _apply_slot(self) -> None:
        idx = self.slot_combo.currentIndex()
        data = self.slot_combo.currentData()
        self.state.set_slot(int(data) if data is not None else idx)

    def _on_status(self, st: ModemStatus) -> None:
        level = {
            ConnState.CONNECTED: "success",
            ConnState.CONNECTING: "warning",
            ConnState.DISCONNECTED: "error",
            ConnState.UNKNOWN: "muted",
        }[st.state]
        self.conn_badge.set_status(st.state.label, level,
                                   pulse=st.state == ConnState.CONNECTED)

        # слоты
        cur = self.slot_combo.currentData()
        self.slot_combo.clear()
        for slot in st.slots:
            self.slot_combo.addItem(slot.title, userData=slot.index)
        if cur is not None:
            for i in range(self.slot_combo.count()):
                if self.slot_combo.itemData(i) == cur:
                    self.slot_combo.setCurrentIndex(i)
                    break

        yes = lambda b: ("Да", P.success) if b else ("Нет", P.text_tertiary)
        v, c = yes(st.sms_capable); self.cap_sms.set_value(v, c)
        v, c = yes(st.ussd_capable); self.cap_ussd.set_value(v, c)
        v, c = yes(st.multi_sim); self.cap_multisim.set_value(v, c)
        self.cap_data.set_value(st.data_class or "—")
        self.cap_ctx.set_value(str(st.max_activation_contexts or "—"))
