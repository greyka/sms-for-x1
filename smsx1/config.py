"""Единая палитра, типографика и метрики дизайн-системы.

Одно место истины для всех цветов, радиусов, теней и отступов —
чтобы интерфейс читался как единая премиальная система.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
#  Палитра (задана заказчиком)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Palette:
    # Акценты
    primary: str = "#3B82F6"      # синий — основной
    cyan: str = "#06B6D4"
    violet: str = "#8B5CF6"
    emerald: str = "#10B981"

    # Поверхности (по возрастанию высоты)
    bg: str = "#0F1115"           # фон окна
    panel: str = "#181A20"        # панели (sidebar, toolbar)
    card: str = "#20242C"         # карточки
    elevated: str = "#272C36"     # всплывающие/наведённые поверхности
    stroke: str = "#2B303B"       # тонкие разделители/обводки

    # Текст
    text: str = "#FFFFFF"
    text_secondary: str = "#A1A1AA"
    text_tertiary: str = "#71717A"

    # Семантика
    error: str = "#EF4444"
    warning: str = "#F59E0B"
    success: str = "#22C55E"
    info: str = "#3B82F6"

    def rgba(self, hex_color: str, alpha: float) -> str:
        """#RRGGBB + alpha[0..1] → 'rgba(r, g, b, a)'."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha:.3f})"


# ─────────────────────────────────────────────────────────────────────────────
#  Метрики
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Radius:
    xs: int = 8
    sm: int = 12
    md: int = 16
    lg: int = 20
    xl: int = 28
    pill: int = 999


@dataclass(frozen=True)
class Spacing:
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32


@dataclass(frozen=True)
class Typography:
    family: str = "Segoe UI Variable Display, Segoe UI, Inter, system-ui"
    mono: str = "Cascadia Code, JetBrains Mono, Consolas, monospace"
    # размер / вес
    display: tuple = (28, 700)
    title: tuple = (20, 700)
    subtitle: tuple = (16, 600)
    body: tuple = (14, 400)
    body_strong: tuple = (14, 600)
    caption: tuple = (12, 500)
    micro: tuple = (11, 600)


@dataclass(frozen=True)
class Motion:
    """Длительности анимаций (мс) и кривые."""
    instant: int = 90
    fast: int = 160
    normal: int = 240
    slow: int = 360
    # QEasingCurve.Type подбираются в ui/theme при импорте Qt
    ease_out: str = "OutCubic"
    ease_in_out: str = "InOutCubic"
    spring: str = "OutBack"


@dataclass(frozen=True)
class Theme:
    palette: Palette = field(default_factory=Palette)
    radius: Radius = field(default_factory=Radius)
    spacing: Spacing = field(default_factory=Spacing)
    typography: Typography = field(default_factory=Typography)
    motion: Motion = field(default_factory=Motion)


THEME = Theme()


# ─────────────────────────────────────────────────────────────────────────────
#  Известные параметры устройства (fallback-подсказки для UI)
# ─────────────────────────────────────────────────────────────────────────────
DEVICE_HINTS = {
    "modem_model": "Quectel EM120R-GL",
    "laptop": "ThinkPad X1 Carbon Gen 9",
    "operator_ussd": {
        "Beeline": {
            "Мой номер": "*110*10#",
            "Баланс": "*102#",
            "Остатки пакетов": "*102*3#",
        },
        "МТС": {"Мой номер": "*111*0887#", "Баланс": "*100#"},
        "МегаФон": {"Мой номер": "*205#", "Баланс": "*100#"},
        "Tele2": {"Мой номер": "*201#", "Баланс": "*105#"},
    },
}
