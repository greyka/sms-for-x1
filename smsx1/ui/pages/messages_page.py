"""Сообщения: поиск, таблица SMS, отправка нового сообщения, пустое состояние."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QHeaderView, QHBoxLayout, QTableWidgetItem, QVBoxLayout, QWidget,
)

from qfluentwidgets import (
    BodyLabel, CaptionLabel, FluentIcon as FIF, IconWidget, LineEdit,
    PlainTextEdit, PrimaryPushButton, PushButton, SearchLineEdit, StrongBodyLabel,
    TableWidget, TransparentToolButton, MessageBoxBase, SubtitleLabel, InfoBadge,
)

from ...config import THEME
from ...core.models import SmsMessage
from ..components import GlassCard
from ..components.section import SectionHeader
from .base_page import BasePage

P = THEME.palette
S = THEME.spacing
R = THEME.radius


class ComposeDialog(MessageBoxBase):
    """Диалог отправки SMS в стиле приложения."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("Новое сообщение", self)
        self.number = LineEdit(self)
        self.number.setPlaceholderText("Номер получателя, напр. +7 900 000-00-00")
        self.number.setClearButtonEnabled(True)
        self.text = PlainTextEdit(self)
        self.text.setPlaceholderText("Текст сообщения…")
        self.text.setFixedHeight(130)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(4)
        self.viewLayout.addWidget(BodyLabel("Получатель", self))
        self.viewLayout.addWidget(self.number)
        self.viewLayout.addSpacing(6)
        self.viewLayout.addWidget(BodyLabel("Сообщение", self))
        self.viewLayout.addWidget(self.text)

        self.yesButton.setText("Отправить")
        self.cancelButton.setText("Отмена")
        self.widget.setMinimumWidth(460)

    def payload(self) -> tuple[str, str]:
        return self.number.text().strip(), self.text.toPlainText().strip()


class MessagesPage(BasePage):
    COLS = ["Отправитель", "Сообщение", "Дата и время", "Статус"]

    def __init__(self, state, parent=None):
        super().__init__("messagesPage", "Сообщения",
                         "Входящие и исходящие SMS через модем",
                         crumbs=["SMS for X1", "Сообщения"], parent=parent)
        self.state = state
        self._all: list[SmsMessage] = []

        # ── панель действий ──
        bar = QHBoxLayout()
        bar.setSpacing(S.md)
        self.search = SearchLineEdit(self)
        self.search.setPlaceholderText("Поиск по отправителю или тексту…")
        self.search.setFixedWidth(320)
        self.search.textChanged.connect(self._filter)
        self.count_badge = InfoBadge.info("0", self)

        self.compose_btn = PrimaryPushButton(FIF.SEND, "Написать", self)
        self.compose_btn.clicked.connect(self._compose)
        self.reload_btn = TransparentToolButton(FIF.SYNC, self)
        self.reload_btn.setToolTip("Обновить")
        self.reload_btn.clicked.connect(self.state.refresh_messages)

        bar.addWidget(self.search)
        bar.addWidget(self.count_badge)
        bar.addStretch(1)
        bar.addWidget(self.reload_btn)
        bar.addWidget(self.compose_btn)
        self.body().addLayout(bar)

        # ── карточка с таблицей ──
        self.card = GlassCard(radius=R.md, padding=S.md, interactive=False)
        self.table = TableWidget(self.card)
        self.table.setColumnCount(len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(12)
        self.table.setWordWrap(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(360)
        self.card.body().addWidget(self.table)
        self.body().addWidget(self.card)

        # ── пустое состояние ──
        self.empty = self._empty_state()
        self.body().addWidget(self.empty)
        self.empty.hide()

        self.state.messagesChanged.connect(self._on_messages)
        self.state.smsSent.connect(self._on_sent)

    def _empty_state(self) -> QWidget:
        card = GlassCard(radius=R.md, padding=S.xxl, interactive=False)
        col = QVBoxLayout()
        col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.setSpacing(S.sm)
        icon = IconWidget(FIF.MESSAGE, card)
        icon.setFixedSize(48, 48)
        col.addWidget(icon, 0, Qt.AlignmentFlag.AlignCenter)
        t = StrongBodyLabel("Сообщений пока нет", card)
        t.setStyleSheet("font-size: 16px; font-weight: 700;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        st = CaptionLabel("Входящие SMS появятся здесь. Убедитесь, что модем "
                          "зарегистрирован в сети.", card)
        st.setStyleSheet(f"color: {P.text_secondary};")
        st.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(t)
        col.addWidget(st)
        card.body().addLayout(col)
        return card

    # ── данные ──
    def _on_messages(self, msgs: list[SmsMessage]) -> None:
        self._all = msgs
        self._render(msgs)

    def _filter(self, query: str) -> None:
        q = query.strip().lower()
        if not q:
            self._render(self._all)
            return
        self._render([m for m in self._all
                      if q in m.sender.lower() or q in m.body.lower()])

    def _render(self, msgs: list[SmsMessage]) -> None:
        self.count_badge.setText(str(len(msgs)))
        has = bool(msgs)
        self.card.setVisible(has)
        self.empty.setVisible(not has)

        self.table.setRowCount(len(msgs))
        for r, m in enumerate(msgs):
            self.table.setItem(r, 0, self._item(m.sender, bold=True))
            self.table.setItem(r, 1, self._item(m.preview))
            self.table.setItem(r, 2, self._item(m.time_label, color=P.text_secondary))
            status = "Прочитано" if m.is_read else "Новое"
            self.table.setItem(r, 3, self._item(
                status, color=P.text_secondary if m.is_read else P.primary))
            self.table.setRowHeight(r, 48)

    @staticmethod
    def _item(text: str, *, bold: bool = False, color: str | None = None) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        if color:
            from PySide6.QtGui import QColor
            it.setForeground(QColor(color))
        if bold:
            from PySide6.QtGui import QFont
            f = it.font()
            f.setWeight(QFont.Weight.DemiBold)
            it.setFont(f)
        return it

    # ── отправка ──
    def _compose(self) -> None:
        dlg = ComposeDialog(self.window())
        if dlg.exec():
            number, text = dlg.payload()
            if number and text:
                self.state.send_sms(number, text)

    def _on_sent(self, res) -> None:
        pass  # уведомление показывает главное окно через notify
