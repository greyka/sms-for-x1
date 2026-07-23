"""Индикатор уровня сигнала — четыре столбика с анимацией и цветом по качеству."""
from __future__ import annotations

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from ...config import THEME

P = THEME.palette


class SignalMeter(QWidget):
    """4 столбика. Уровень 0..4, плавно анимируется, цвет зависит от качества."""

    BARS = 4

    def __init__(self, level: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(52, 34)
        self._level = level
        self._fill = float(level)
        self._anim: QPropertyAnimation | None = None

    def set_level(self, level: int) -> None:
        level = max(0, min(self.BARS, level))
        self._level = level
        if self._anim:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"fill")
        self._anim.setDuration(THEME.motion.slow)
        self._anim.setStartValue(self._fill)
        self._anim.setEndValue(float(level))
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def _get_fill(self) -> float:
        return self._fill

    def _set_fill(self, v: float) -> None:
        self._fill = v
        self.update()

    fill = Property(float, _get_fill, _set_fill)

    def _color(self) -> QColor:
        if self._level <= 0:
            return QColor(P.error)
        if self._level == 1:
            return QColor(P.error)
        if self._level == 2:
            return QColor(P.warning)
        if self._level == 3:
            return QColor(P.cyan)
        return QColor(P.success)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        gap = 6
        bar_w = (w - gap * (self.BARS - 1)) / self.BARS
        active = self._color()

        for i in range(self.BARS):
            bar_h = h * (0.42 + 0.58 * (i / (self.BARS - 1)))
            x = i * (bar_w + gap)
            y = h - bar_h
            path = QPainterPath()
            path.addRoundedRect(x, y, bar_w, bar_h, 3, 3)

            filled = self._fill >= (i + 1) or (self._fill > i and self._fill - i > 0.35)
            if filled:
                p.fillPath(path, active)
            else:
                dim = QColor(P.text_secondary)
                dim.setAlphaF(0.16)
                p.fillPath(path, dim)
