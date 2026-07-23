"""Цветные индикаторы статуса: пилюля-бейдж и пульсирующая точка."""
from __future__ import annotations

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ...config import THEME

P = THEME.palette
R = THEME.radius


class Dot(QWidget):
    """Круглый индикатор с мягким пульсом (для «в сети»/«ошибка»)."""

    def __init__(self, color: str = P.success, size: int = 10,
                 pulse: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self._size = size
        self._ring = 0.0
        self.setFixedSize(size + 12, size + 12)
        self._anim: QPropertyAnimation | None = None
        if pulse:
            self._start_pulse()

    def set_color(self, color: str, pulse: bool = True) -> None:
        self._color = QColor(color)
        if pulse and self._anim is None:
            self._start_pulse()
        elif not pulse and self._anim is not None:
            self._anim.stop()
            self._anim = None
            self._ring = 0.0
        self.update()

    def _get_ring(self) -> float:
        return self._ring

    def _set_ring(self, v: float) -> None:
        self._ring = v
        self.update()

    ring = Property(float, _get_ring, _set_ring)

    def _start_pulse(self) -> None:
        self._anim = QPropertyAnimation(self, b"ring")
        self._anim.setDuration(1600)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2

        if self._anim is not None:
            r = self._size / 2 + self._ring * (self._size / 2 + 5)
            ring = QColor(self._color)
            ring.setAlphaF(max(0.0, 0.35 * (1 - self._ring)))
            p.setBrush(ring)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        p.setBrush(self._color)
        p.setPen(Qt.PenStyle.NoPen)
        s = self._size
        p.drawEllipse(int(cx - s / 2), int(cy - s / 2), s, s)


class StatusBadge(QWidget):
    """Пилюля с точкой и текстом: «Подключено», «Нет сигнала» и т.п."""

    LEVELS = {
        "success": THEME.palette.success,
        "info": THEME.palette.info,
        "warning": THEME.palette.warning,
        "error": THEME.palette.error,
        "muted": THEME.palette.text_tertiary,
    }

    def __init__(self, text: str = "", level: str = "muted",
                 pulse: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 5, 12, 5)
        lay.setSpacing(8)

        self._dot = Dot(self.LEVELS[level], size=8, pulse=pulse, parent=self)
        self._label = QLabel(text, self)
        self._label.setStyleSheet("font-size: 12px; font-weight: 600;")

        lay.addWidget(self._dot)
        lay.addWidget(self._label)
        self._apply(level)

    def set_status(self, text: str, level: str, pulse: bool = False) -> None:
        self._label.setText(text)
        self._dot.set_color(self.LEVELS.get(level, P.text_tertiary), pulse)
        self._apply(level)

    def _apply(self, level: str) -> None:
        color = self.LEVELS.get(level, P.text_tertiary)
        self.setStyleSheet(f"""
            background-color: {P.rgba(color, 0.12)};
            border: 1px solid {P.rgba(color, 0.28)};
            border-radius: {R.pill}px;
        """)
        self._label.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 600; background: transparent; border: none;")
