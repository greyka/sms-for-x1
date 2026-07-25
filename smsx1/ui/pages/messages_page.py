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
    Dialog, TextEdit,
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


class MessageViewDialog(MessageBoxBase):
    """Просмотр полного текста SMS (в т.ч. склеенной из частей)."""

    def __init__(self, msg: SmsMessage, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(f"Сообщение от {msg.sender}", self)
        meta = msg.time_label + (f"   ·   {msg.parts} частей" if msg.parts > 1 else "")
        self.metaLabel = CaptionLabel(meta, self)
        self.metaLabel.setStyleSheet(f"color: {P.text_secondary};")

        self.body_view = TextEdit(self)
        self.body_view.setReadOnly(True)
        self.body_view.setPlainText(msg.body)
        self.body_view.setMinimumHeight(220)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.metaLabel)
        self.viewLayout.addSpacing(6)
        self.viewLayout.addWidget(self.body_view)

        self.yesButton.setText("Закрыть")
        self.cancelButton.hide()
        self.widget.setMinimumWidth(560)


class MessagesPage(BasePage):
    COLS = ["Отправитель", "Сообщение", "Дата и время", "Статус"]

    def __init__(self, state, parent=None):
        super().__init__("messagesPage", "Сообщения",
                         "Входящие и исходящие SMS через модем",
                         crumbs=["SMS for X1", "Сообщения"], parent=parent)
        self.state = state
        self._all: list[SmsMessage] = []
        self._shown: list[SmsMessage] = []      # сообщения в текущем порядке строк

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
        self.delete_btn = PushButton(FIF.DELETE, "Удалить", self)
        self.delete_btn.clicked.connect(self._delete_selected)
        self.delete_btn.setEnabled(False)
        self.reload_btn = TransparentToolButton(FIF.SYNC, self)
        self.reload_btn.setToolTip("Обновить")
        self.reload_btn.clicked.connect(self.state.refresh_messages)

        bar.addWidget(self.search)
        bar.addWidget(self.count_badge)
        bar.addStretch(1)
        bar.addWidget(self.reload_btn)
        bar.addWidget(self.delete_btn)
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
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.table.itemDoubleClicked.connect(self._open_message)
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
        self._shown = list(msgs)
        self.count_badge.setText(str(len(msgs)))
        has = bool(msgs)
        self.card.setVisible(has)
        self.empty.setVisible(not has)

        self.table.setRowCount(len(msgs))
        for r, m in enumerate(msgs):
            self.table.setItem(r, 0, self._item(m.sender, bold=True))
            preview = m.preview
            if m.parts > 1:
                preview = f"{preview}   ·  {self._plural_parts(m.parts)}"
            self.table.setItem(r, 1, self._item(preview))
            self.table.setItem(r, 2, self._item(m.time_label, color=P.text_secondary))
            status = "Прочитано" if m.is_read else "Новое"
            self.table.setItem(r, 3, self._item(
                status, color=P.text_secondary if m.is_read else P.primary))
            self.table.setRowHeight(r, 48)
        self.delete_btn.setEnabled(False)

    # ── просмотр полного текста ──
    def _open_message(self, item) -> None:
        r = item.row()
        if 0 <= r < len(self._shown):
            MessageViewDialog(self._shown[r], self.window()).exec()

    # ── выбор и удаление ──
    def _on_selection(self) -> None:
        rows = {i.row() for i in self.table.selectedItems()}
        self.delete_btn.setEnabled(bool(rows))
        self.delete_btn.setText(f"Удалить ({len(rows)})" if rows else "Удалить")

    def _selected_messages(self) -> list[SmsMessage]:
        rows = sorted({i.row() for i in self.table.selectedItems()})
        return [self._shown[r] for r in rows if 0 <= r < len(self._shown)]

    def _delete_selected(self) -> None:
        msgs = self._selected_messages()
        if not msgs:
            return
        total_parts = sum(len(m.part_ids or [m.id]) for m in msgs)
        title = "Удалить сообщения?"
        content = (f"Будет удалено сообщений: {len(msgs)}"
                   + (f" (сегментов: {total_parts})" if total_parts != len(msgs) else "")
                   + ".\nДействие необратимо.")
        dlg = Dialog(title, content, self.window())
        dlg.yesButton.setText("Удалить")
        dlg.cancelButton.setText("Отмена")
        if dlg.exec():
            self.state.delete_messages(msgs)

    @staticmethod
    def _plural_parts(n: int) -> str:
        n10, n100 = n % 10, n % 100
        if n10 == 1 and n100 != 11:
            word = "часть"
        elif 2 <= n10 <= 4 and not (12 <= n100 <= 14):
            word = "части"
        else:
            word = "частей"
        return f"{n} {word}"

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
