"""USSD: быстрые команды оператора, ввод произвольного кода, вывод ответа."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from qfluentwidgets import (
    BodyLabel, CaptionLabel, ComboBox, FluentIcon as FIF, IndeterminateProgressRing,
    LineEdit, PillPushButton, PrimaryPushButton, StrongBodyLabel, TextEdit,
)

from ...config import THEME, DEVICE_HINTS
from ...core.models import UssdResult
from ..components import GlassCard
from ..components.section import SectionHeader
from .base_page import BasePage

P = THEME.palette
S = THEME.spacing
R = THEME.radius


class UssdPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__("ussdPage", "USSD-команды",
                         "Быстрые запросы к оператору: номер, баланс, услуги",
                         crumbs=["SMS for X1", "USSD"], parent=parent)
        self.state = state

        # ── ввод ──
        card = GlassCard(radius=R.md, padding=S.xl, interactive=False)
        card.body().addWidget(SectionHeader("Отправить запрос", "Например, *110*10#"))

        row = QHBoxLayout()
        row.setSpacing(S.md)
        self.operator = ComboBox(self)
        self.operator.addItems(list(DEVICE_HINTS["operator_ussd"].keys()))
        self.operator.setFixedWidth(150)
        self.operator.currentTextChanged.connect(self._reload_quick)

        self.code = LineEdit(self)
        self.code.setPlaceholderText("USSD-код, напр. *100#")
        self.code.setClearButtonEnabled(True)
        self.code.returnPressed.connect(self._send_custom)

        self.send_btn = PrimaryPushButton(FIF.SEND, "Отправить", self)
        self.send_btn.clicked.connect(self._send_custom)

        row.addWidget(self.operator)
        row.addWidget(self.code, 1)
        row.addWidget(self.send_btn)
        card.body().addLayout(row)

        # быстрые кнопки
        card.body().addSpacing(S.sm)
        self.quick_wrap = QHBoxLayout()
        self.quick_wrap.setSpacing(S.sm)
        self.quick_wrap.setAlignment(Qt.AlignmentFlag.AlignLeft)
        card.body().addLayout(self.quick_wrap)

        hint = CaptionLabel(
            "USSD — сервис коммутации каналов: на время запроса модем уходит с LTE "
            "(CSFB), поэтому мобильный интернет ненадолго прерывается. "
            "Приложение восстановит соединение автоматически.", card)
        hint.setStyleSheet(f"color: {P.text_tertiary};")
        hint.setWordWrap(True)
        card.body().addSpacing(S.sm)
        card.body().addWidget(hint)
        self.body().addWidget(card)

        # ── ответ ──
        self.answer_card = GlassCard(radius=R.md, padding=S.xl, interactive=False)
        head = QHBoxLayout()
        head.addWidget(SectionHeader("Ответ оператора", ""))
        head.addStretch(1)
        self.spinner = IndeterminateProgressRing(self)
        self.spinner.setFixedSize(22, 22)
        self.spinner.hide()
        head.addWidget(self.spinner)
        self.answer_card.body().addLayout(head)

        self.answer = TextEdit(self.answer_card)
        self.answer.setReadOnly(True)
        self.answer.setPlaceholderText("Здесь появится ответ на USSD-запрос.")
        self.answer.setFixedHeight(180)
        self.answer.setStyleSheet(self.answer.styleSheet() +
                                  "font-family:'Cascadia Code','Consolas',monospace;")
        self.answer_card.body().addWidget(self.answer)
        self.body().addWidget(self.answer_card)

        self.state.ussdReply.connect(self._on_reply)
        self.state.ussdLoading.connect(self._on_loading)
        self._reload_quick(self.operator.currentText())

    _ICONS = {
        "Мой номер": FIF.PHONE,
        "Баланс": FIF.MARKET,
        "Остатки пакетов": FIF.PIE_SINGLE,
    }

    def _reload_quick(self, operator: str) -> None:
        while self.quick_wrap.count():
            item = self.quick_wrap.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        codes = DEVICE_HINTS["operator_ussd"].get(operator, {})
        for label, code in codes.items():
            icon = self._ICONS.get(label, FIF.SEND)
            btn = PillPushButton(icon, f"{label}", self)
            if hasattr(btn, "setCheckable"):
                btn.setCheckable(False)
            btn.setToolTip(code)
            btn.clicked.connect(lambda _=False, c=code: self._send(c))
            self.quick_wrap.addWidget(btn)
        self.quick_wrap.addStretch(1)

    def trigger(self, code: str, operator: str | None = None) -> None:
        """Программно выполнить USSD-код (для быстрых действий с других экранов)."""
        if operator:
            idx = self.operator.findText(operator)
            if idx >= 0:
                self.operator.setCurrentIndex(idx)
        self._send(code)

    def _send_custom(self) -> None:
        code = self.code.text().strip()
        if code:
            self._send(code)

    def _send(self, code: str) -> None:
        self.code.setText(code)
        self.answer.setPlainText(f"→ Отправка {code} …")
        self.state.send_ussd(code)

    def _on_loading(self, loading: bool) -> None:
        self.spinner.setVisible(loading)
        self.send_btn.setEnabled(not loading)

    def _on_reply(self, res: UssdResult) -> None:
        if res.ok:
            text = res.text or "(пустой ответ)"
            self.answer.setPlainText(text)
        else:
            self.answer.setPlainText(f"⚠ {res.error or 'Не удалось выполнить запрос'}\n\n"
                                     "Возможная причина — слабый сигнал или модем "
                                     "не зарегистрирован в сети.")
