"""Настройки и «О приложении» (с версией)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from qfluentwidgets import (
    BodyLabel, CaptionLabel, ComboBox, FluentIcon as FIF, HyperlinkButton,
    IconWidget, PrimaryPushButton, PushButton, StrongBodyLabel, SwitchButton,
    TitleLabel, TransparentToolButton,
)

from ... import __version__, __app_name__
from ...config import THEME
from ..components import GlassCard, MetricRow
from ..components.section import SectionHeader, Divider
from .base_page import BasePage

P = THEME.palette
S = THEME.spacing
R = THEME.radius


class _Row(QWidget):
    def __init__(self, title, subtitle, control, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 8)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(StrongBodyLabel(title, self))
        s = CaptionLabel(subtitle, self)
        s.setStyleSheet(f"color: {P.text_secondary};")
        col.addWidget(s)
        lay.addLayout(col)
        lay.addStretch(1)
        lay.addWidget(control)


class SettingsPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__("settingsPage", "Настройки",
                         "Поведение приложения и информация",
                         crumbs=["SMS for X1", "Настройки"], parent=parent)
        self.state = state

        # ── поведение ──
        beh = GlassCard(radius=R.md, padding=S.xl, interactive=False)
        beh.body().addWidget(SectionHeader("Поведение", "Опрос статуса и уведомления"))
        beh.body().addSpacing(S.sm)

        self.poll = ComboBox(self)
        self.poll.addItems(["3 секунды", "5 секунд", "10 секунд", "30 секунд"])
        self.poll.setCurrentIndex(1)
        self.poll.setFixedWidth(160)
        self.poll.currentIndexChanged.connect(self._poll_changed)
        beh.body().addWidget(_Row("Интервал обновления",
                                  "Как часто опрашивать модем", self.poll))
        beh.body().addWidget(Divider())

        self.autoswitch = SwitchButton(self)
        self.autoswitch.setChecked(True)
        beh.body().addWidget(_Row("Уведомления",
                                  "Показывать всплывающие сообщения о событиях",
                                  self.autoswitch))
        self.body().addWidget(beh)

        # ── внешний вид ──
        appearance = GlassCard(radius=R.md, padding=S.xl, interactive=False)
        appearance.body().addWidget(SectionHeader("Внешний вид", "Акцентный цвет интерфейса"))
        appearance.body().addSpacing(S.sm)
        swatches = QHBoxLayout()
        swatches.setSpacing(S.md)
        swatches.setAlignment(Qt.AlignmentFlag.AlignLeft)
        for color in (P.primary, P.cyan, P.violet, P.emerald):
            swatches.addWidget(self._swatch(color))
        appearance.body().addLayout(swatches)
        self.body().addWidget(appearance)

        # ── COM-порт / AT ──
        self.body().addWidget(self._serial_card())

        # ── о приложении ──
        self.body().addWidget(self._about_card())

        self.state.portsChanged.connect(self._on_ports)
        self.state.atResult.connect(self._on_at)
        self.state.refresh_ports()

    def _serial_card(self) -> GlassCard:
        card = GlassCard(radius=R.md, padding=S.xl, interactive=False)
        head = QHBoxLayout()
        head.addWidget(SectionHeader(
            "COM-порт модема", "Для AT-команд (если модем в AT-режиме)"))
        head.addStretch(1)
        self.ports_reload = TransparentToolButton(FIF.SYNC, self)
        self.ports_reload.setToolTip("Обновить список портов")
        self.ports_reload.clicked.connect(self.state.refresh_ports)
        head.addWidget(self.ports_reload)
        card.body().addLayout(head)
        card.body().addSpacing(S.sm)

        row = QHBoxLayout()
        row.setSpacing(S.md)
        row.addWidget(BodyLabel("Порт", self))
        self.port_combo = ComboBox(self)
        self.port_combo.setMinimumWidth(280)
        self.port_combo.currentIndexChanged.connect(self._port_selected)
        self.detect_btn = PrimaryPushButton(FIF.SEARCH, "Автоопределение", self)
        self.detect_btn.clicked.connect(self._autodetect)
        row.addStretch(1)
        row.addWidget(self.port_combo)
        row.addWidget(self.detect_btn)
        card.body().addLayout(row)

        self.port_note = CaptionLabel(
            "Модем Quectel в MBIM-режиме обычно не выдаёт AT-порт (только DM/EDL). "
            "Автоопределение проверит все порты командой AT.", self)
        self.port_note.setStyleSheet(f"color: {P.text_tertiary};")
        self.port_note.setWordWrap(True)
        card.body().addSpacing(S.sm)
        card.body().addWidget(self.port_note)
        return card

    def _on_ports(self, ports: list) -> None:
        self.port_combo.clear()
        if not ports:
            self.port_combo.addItem("Порты не найдены")
            self.port_combo.setEnabled(False)
            return
        self.port_combo.setEnabled(True)
        for p in ports:
            label = f"{p.device} — {p.description}" if p.description else p.device
            self.port_combo.addItem(label, userData=p.device)

    def _port_selected(self, idx: int) -> None:
        data = self.port_combo.itemData(idx)
        if data:
            self.state.select_port(str(data))

    def _autodetect(self) -> None:
        self.detect_btn.setEnabled(False)
        self.port_note.setText("Идёт автоопределение — проверяю порты…")
        self.state.autodetect_port()

    def _on_at(self, res) -> None:
        self.detect_btn.setEnabled(True)
        color = P.success if res.ok else P.warning
        self.port_note.setStyleSheet(f"color: {color};")
        self.port_note.setText(res.message)

    def _swatch(self, color: str) -> QWidget:
        from qfluentwidgets import setThemeColor
        w = QWidget(self)
        w.setFixedSize(40, 40)
        w.setCursor(Qt.CursorShape.PointingHandCursor)
        w.setStyleSheet(f"""
            background-color: {color};
            border-radius: {R.sm}px;
            border: 2px solid {P.rgba(P.text, 0.15)};
        """)
        w.mousePressEvent = lambda _e, c=color: setThemeColor(c)
        return w

    def _about_card(self) -> GlassCard:
        card = GlassCard(radius=R.md, padding=S.xl, interactive=False)
        top = QHBoxLayout()
        logo = QWidget(card)
        logo.setFixedSize(56, 56)
        logo.setStyleSheet(f"""
            background-color: {P.rgba(P.primary, 0.18)};
            border-radius: {R.md}px;
        """)
        logo_lay = QHBoxLayout(logo)
        logo_lay.setContentsMargins(0, 0, 0, 0)
        ic = IconWidget(FIF.MESSAGE, logo)
        ic.setFixedSize(28, 28)
        logo_lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignCenter)

        col = QVBoxLayout()
        col.setSpacing(2)
        name = TitleLabel(__app_name__, card)
        name.setStyleSheet("font-size: 20px; font-weight: 700;")
        ver = CaptionLabel(f"Версия {__version__}", card)
        ver.setStyleSheet(f"color: {P.primary}; font-weight: 600;")
        col.addWidget(name)
        col.addWidget(ver)

        top.addWidget(logo)
        top.addSpacing(S.md)
        top.addLayout(col)
        top.addStretch(1)
        card.body().addLayout(top)
        card.body().addSpacing(S.md)
        card.body().addWidget(Divider())

        card.body().addWidget(MetricRow("Устройство", "ThinkPad X1 Carbon Gen 9"))
        card.body().addWidget(MetricRow("Модем", "Quectel EM120R-GL"))
        card.body().addWidget(MetricRow("Технологии", "PySide6 · qfluentwidgets · WinRT"))

        links = QHBoxLayout()
        links.setAlignment(Qt.AlignmentFlag.AlignLeft)
        links.addWidget(HyperlinkButton(
            "https://github.com/greyka/sms-for-x1", "Репозиторий на GitHub",
            card, FIF.GITHUB))
        card.body().addSpacing(S.sm)
        card.body().addLayout(links)
        return card

    def _poll_changed(self, idx: int) -> None:
        ms = [3000, 5000, 10000, 30000][idx]
        self.state._timer.setInterval(ms)
