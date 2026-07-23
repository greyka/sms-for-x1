"""Базовый экран: breadcrumb, крупный заголовок, прокручиваемое тело,
плавное появление контента при первом показе.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from qfluentwidgets import (
    BreadcrumbBar, CaptionLabel, SingleDirectionScrollArea, TitleLabel,
)

from ...config import THEME

P = THEME.palette
S = THEME.spacing


class BasePage(QWidget):
    """Каркас страницы с breadcrumb и прокручиваемым телом."""

    def __init__(self, object_name: str, title: str, subtitle: str = "",
                 crumbs: list[str] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self._shown_once = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(S.lg)

        # ── breadcrumb ──
        self.breadcrumb = BreadcrumbBar(self)
        for i, c in enumerate(crumbs or ["SMS for X1", title]):
            self.breadcrumb.addItem(f"crumb{i}", c)
        outer.addWidget(self.breadcrumb)

        # ── заголовок ──
        header = QVBoxLayout()
        header.setSpacing(2)
        self._title = TitleLabel(title, self)
        self._title.setStyleSheet(f"color: {P.text}; font-weight: 700;")
        header.addWidget(self._title)
        if subtitle:
            self._subtitle = CaptionLabel(subtitle, self)
            self._subtitle.setStyleSheet(f"color: {P.text_secondary};")
            header.addWidget(self._subtitle)
        outer.addLayout(header)

        # ── прокручиваемое тело ──
        self._scroll = SingleDirectionScrollArea(self, orient=Qt.Orientation.Vertical)
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll.enableTransparentBackground()

        self._content = QWidget(self._scroll)
        self._content.setStyleSheet("background: transparent;")
        self._body = QVBoxLayout(self._content)
        self._body.setContentsMargins(0, S.sm, 8, S.xl)
        self._body.setSpacing(S.lg)
        self._body.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, 1)

    # тело для наполнения контентом
    def body(self) -> QVBoxLayout:
        return self._body

    def set_toolbar(self, widget: QWidget) -> None:
        """Разместить панель действий справа от заголовка (в одну строку)."""
        row = QHBoxLayout()
        row.addWidget(self._title)
        row.addStretch(1)
        row.addWidget(widget)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self._shown_once = True
