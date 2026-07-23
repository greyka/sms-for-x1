"""Применение дизайн-системы: тёмная тема, акцент, шрифты, тени, анимации.

Центральная точка — ``apply_theme(app)``. Здесь же — фабрики теней и
плавных анимаций, чтобы микровзаимодействия были единообразны.
"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from qfluentwidgets import setTheme, setThemeColor, Theme

from ..config import THEME

P = THEME.palette


# ─────────────────────────────────────────────────────────────────────────────
#  Глобальная тема
# ─────────────────────────────────────────────────────────────────────────────
def apply_theme(app) -> None:
    setTheme(Theme.DARK)
    setThemeColor(P.primary)

    # Приятный дефолтный шрифт
    for family in ("Segoe UI Variable Display", "Segoe UI", "Inter"):
        if family in QFontDatabase.families():
            f = QFont(family, 10)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            app.setFont(f)
            break

    app.setStyleSheet(_GLOBAL_QSS)


# ─────────────────────────────────────────────────────────────────────────────
#  Тени (elevation)
# ─────────────────────────────────────────────────────────────────────────────
def soft_shadow(widget: QWidget, *, blur: int = 40, y: int = 14,
                alpha: int = 120, color: str | None = None) -> QGraphicsDropShadowEffect:
    """Мягкая тень для карточек/поповеров."""
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setXOffset(0)
    eff.setYOffset(y)
    c = QColor(color) if color else QColor(0, 0, 0)
    c.setAlpha(alpha)
    eff.setColor(c)
    widget.setGraphicsEffect(eff)
    return eff


def glow(widget: QWidget, color: str, *, blur: int = 32, alpha: int = 140) -> QGraphicsDropShadowEffect:
    """Цветное свечение (для акцентных элементов при наведении)."""
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, 0)
    c = QColor(color)
    c.setAlpha(alpha)
    eff.setColor(c)
    widget.setGraphicsEffect(eff)
    return eff


# ─────────────────────────────────────────────────────────────────────────────
#  Анимации
# ─────────────────────────────────────────────────────────────────────────────
_EASING = {
    "OutCubic": QEasingCurve.Type.OutCubic,
    "InOutCubic": QEasingCurve.Type.InOutCubic,
    "OutBack": QEasingCurve.Type.OutBack,
    "OutQuint": QEasingCurve.Type.OutQuint,
}


def animate(widget: QWidget, prop: bytes, start, end,
            duration: int = THEME.motion.normal,
            easing: str = "OutCubic") -> QPropertyAnimation:
    anim = QPropertyAnimation(widget, prop)
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(_EASING.get(easing, QEasingCurve.Type.OutCubic))
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim


def fade_in(widget: QWidget, duration: int = THEME.motion.normal) -> QPropertyAnimation:
    from PySide6.QtWidgets import QGraphicsOpacityEffect
    eff = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(eff)
    anim = QPropertyAnimation(eff, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim


# ─────────────────────────────────────────────────────────────────────────────
#  Глобальный QSS
# ─────────────────────────────────────────────────────────────────────────────
_GLOBAL_QSS = f"""
* {{
    outline: none;
}}
QWidget {{
    color: {P.text};
}}
QToolTip {{
    background-color: {P.elevated};
    color: {P.text};
    border: 1px solid {P.stroke};
    border-radius: 8px;
    padding: 6px 10px;
}}
/* тонкие современные скроллбары */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px 4px 0;
}}
QScrollBar::handle:vertical {{
    background: {P.rgba(P.text_secondary, 0.22)};
    border-radius: 5px;
    min-height: 36px;
}}
QScrollBar::handle:vertical:hover {{
    background: {P.rgba(P.text_secondary, 0.40)};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0; background: transparent;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0 4px 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background: {P.rgba(P.text_secondary, 0.22)};
    border-radius: 5px;
    min-width: 36px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {P.rgba(P.text_secondary, 0.40)};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; background: transparent;
}}
"""
