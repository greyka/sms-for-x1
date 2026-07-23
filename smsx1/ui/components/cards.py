"""Карточки: стеклянная поверхность с мягкой тенью и hover-подъёмом,
карточка-метрика и строка «ключ → значение».
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from qfluentwidgets import BodyLabel, CaptionLabel, IconWidget, StrongBodyLabel

from ...config import THEME
from ..theme import soft_shadow

P = THEME.palette
R = THEME.radius
S = THEME.spacing


class GlassCard(QFrame):
    """Полупрозрачная карточка со скруглением, обводкой и hover-анимацией."""

    def __init__(self, parent: QWidget | None = None, *, radius: int = R.md,
                 padding: int = S.xl, interactive: bool = True) -> None:
        super().__init__(parent)
        self._radius = radius
        self._interactive = interactive
        self.setObjectName("glassCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._apply_style(hover=False)

        self._shadow = soft_shadow(self, blur=38, y=16, alpha=110)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(padding, padding, padding, padding)
        self._root.setSpacing(S.md)

    # публичный layout для наполнения
    def body(self) -> QVBoxLayout:
        return self._root

    def add(self, widget: QWidget) -> None:
        self._root.addWidget(widget)

    def _apply_style(self, hover: bool) -> None:
        bg = P.rgba(P.card, 0.92 if not hover else 0.98)
        border = P.rgba(P.text, 0.06 if not hover else 0.12)
        self.setStyleSheet(f"""
            #glassCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {self._radius}px;
            }}
        """)

    def enterEvent(self, e: QEvent) -> None:
        if self._interactive:
            self._apply_style(hover=True)
            self._shadow.setColor(QColor(59, 130, 246, 60))
            self._shadow.setBlurRadius(46)
        super().enterEvent(e)

    def leaveEvent(self, e: QEvent) -> None:
        if self._interactive:
            self._apply_style(hover=False)
            c = QColor(0, 0, 0)
            c.setAlpha(110)
            self._shadow.setColor(c)
            self._shadow.setBlurRadius(38)
        super().leaveEvent(e)


class StatCard(GlassCard):
    """Карточка-метрика: иконка, крупное значение, подпись, дельта/статус."""

    def __init__(self, icon, title: str, value: str = "—",
                 accent: str = P.primary, parent: QWidget | None = None) -> None:
        super().__init__(parent, radius=R.md, padding=S.xl)
        self._accent = accent

        head = QHBoxLayout()
        head.setSpacing(S.md)

        self._icon_holder = QFrame(self)
        self._icon_holder.setFixedSize(44, 44)
        self._icon_holder.setStyleSheet(f"""
            background-color: {P.rgba(accent, 0.16)};
            border-radius: {R.sm}px;
        """)
        icon_lay = QHBoxLayout(self._icon_holder)
        icon_lay.setContentsMargins(0, 0, 0, 0)
        self._icon = IconWidget(icon, self._icon_holder)
        self._icon.setFixedSize(22, 22)
        icon_lay.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignCenter)

        self._caption = CaptionLabel(title, self)
        self._caption.setStyleSheet(f"color: {P.text_secondary};")

        head.addWidget(self._icon_holder)
        head.addStretch(1)

        self._value = QLabel(value, self)
        self._value.setStyleSheet(
            f"color: {P.text}; font-size: 26px; font-weight: 700;")

        self._sub = CaptionLabel("", self)
        self._sub.setStyleSheet(f"color: {P.text_tertiary};")

        self.body().addLayout(head)
        self.body().addSpacing(S.sm)
        self.body().addWidget(self._value)
        self.body().addWidget(self._caption)
        self.body().addWidget(self._sub)

    def set_value(self, value: str) -> None:
        self._value.setText(value)

    def set_sub(self, text: str, color: str | None = None) -> None:
        self._sub.setText(text)
        self._sub.setStyleSheet(f"color: {color or P.text_tertiary};")

    def set_accent(self, accent: str) -> None:
        self._accent = accent
        self._icon_holder.setStyleSheet(f"""
            background-color: {P.rgba(accent, 0.16)};
            border-radius: {R.sm}px;
        """)


class MetricRow(QWidget):
    """Строка «подпись → значение» для карточек деталей."""

    def __init__(self, key: str, value: str = "—", *, mono: bool = False,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.setSpacing(S.md)

        self._key = BodyLabel(key, self)
        self._key.setStyleSheet(f"color: {P.text_secondary};")
        self._value = StrongBodyLabel(value, self)
        font = "font-family: 'Cascadia Code','Consolas',monospace;" if mono else ""
        self._value.setStyleSheet(f"color: {P.text}; {font}")
        self._value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        lay.addWidget(self._key)
        lay.addStretch(1)
        lay.addWidget(self._value)

    def set_value(self, value: str, color: str | None = None) -> None:
        self._value.setText(value)
        if color:
            self._value.setStyleSheet(f"color: {color};")
