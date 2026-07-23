"""Заголовок секции с подписью и тонкий разделитель."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

from qfluentwidgets import CaptionLabel, StrongBodyLabel

from ...config import THEME

P = THEME.palette


class SectionHeader(QWidget):
    """Крупный заголовок раздела + мягкая подпись справа/снизу."""

    def __init__(self, title: str, subtitle: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        self._title = StrongBodyLabel(title, self)
        self._title.setStyleSheet(
            f"color: {P.text}; font-size: 17px; font-weight: 700;")
        lay.addWidget(self._title)

        if subtitle:
            self._sub = CaptionLabel(subtitle, self)
            self._sub.setStyleSheet(f"color: {P.text_secondary};")
            lay.addWidget(self._sub)

    def set_title(self, text: str) -> None:
        self._title.setText(text)


class Divider(QFrame):
    """Горизонтальный волосяной разделитель."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background-color: {P.rgba(P.text, 0.07)}; border: none;")
