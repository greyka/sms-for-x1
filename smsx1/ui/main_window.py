"""Главное окно: FluentWindow (frameless + Mica), sidebar-навигация,
статус-бар, всплывающие уведомления, анимированное появление.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation, QRect, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from qfluentwidgets import (
    FluentWindow, FluentIcon as FIF, InfoBar, InfoBarPosition, NavigationItemPosition,
    setThemeColor,
)

from .. import __app_name__, __version__
from ..config import THEME
from ..viewmodels.app_state import AppState
from .pages import DashboardPage, MessagesPage, ModemPage, SettingsPage, UssdPage
from .status_bar import StatusBar

P = THEME.palette


class MainWindow(FluentWindow):
    def __init__(self, state: AppState, icon_path: str | None = None):
        super().__init__()
        self.state = state

        # ── окно ──
        self.setWindowTitle(f"{__app_name__} — управление модемом")
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1180, 760)
        self.setMinimumSize(QSize(920, 620))
        self._center()

        # frameless + Mica/акрил (с тёмным fallback-фоном, если Mica недоступна)
        self.setCustomBackgroundColor(P.bg, P.bg)
        try:
            self.setMicaEffectEnabled(True)
        except Exception:
            pass
        self.stackedWidget.setStyleSheet(f"QStackedWidget {{ background: {P.bg}; }}")
        setThemeColor(P.primary)

        # ── страницы ──
        self.dashboard = DashboardPage(state, self)
        self.messages = MessagesPage(state, self)
        self.ussd = UssdPage(state, self)
        self.modem = ModemPage(state, self)
        self.settings = SettingsPage(state, self)

        self.addSubInterface(self.dashboard, FIF.HOME, "Обзор")
        self.addSubInterface(self.messages, FIF.MESSAGE, "Сообщения")
        self.addSubInterface(self.ussd, FIF.COMMAND_PROMPT, "USSD")
        self.addSubInterface(self.modem, FIF.CONNECT, "Модем")
        self.addSubInterface(
            self.settings, FIF.SETTING, "Настройки",
            position=NavigationItemPosition.BOTTOM)

        self.navigationInterface.setExpandWidth(240)
        self.navigationInterface.setCollapsible(True)

        # быстрые действия дашборда → экран USSD
        self.dashboard.quickUssd.connect(self._on_quick_ussd)

        # ── статус-бар снизу ──
        self._install_status_bar()

        # ── уведомления ──
        self.state.notify.connect(self._notify)

        # ── появление ──
        self._play_intro()

    # ── быстрые действия ─────────────────────────────────────────────────────
    def _on_quick_ussd(self, code: str) -> None:
        self.stackedWidget.setCurrentWidget(self.ussd)
        self.ussd.trigger(code)

    # ── статус-бар ───────────────────────────────────────────────────────────
    def _install_status_bar(self) -> None:
        self.status_bar = StatusBar(self.state, self)
        # widgetLayout (QHBoxLayout) держит stackedWidget — оборачиваем в вертикаль
        self.widgetLayout.removeWidget(self.stackedWidget)
        container = QWidget(self)
        container.setStyleSheet(f"background: {P.bg};")
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self.stackedWidget, 1)
        v.addWidget(self.status_bar)
        self.widgetLayout.addWidget(container)

    # ── уведомления ──────────────────────────────────────────────────────────
    def _notify(self, level: str, text: str) -> None:
        if not text:
            return
        factory = {
            "success": InfoBar.success,
            "info": InfoBar.info,
            "warning": InfoBar.warning,
            "error": InfoBar.error,
        }.get(level, InfoBar.info)
        factory(
            title={"success": "Готово", "info": "Информация",
                   "warning": "Внимание", "error": "Ошибка"}.get(level, ""),
            content=text,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=4000,
            parent=self,
        )

    # ── появление ────────────────────────────────────────────────────────────
    def _play_intro(self) -> None:
        eff_geo = self.geometry()
        start = QRect(eff_geo.x(), eff_geo.y() + 24,
                      eff_geo.width(), eff_geo.height())
        self._intro = QPropertyAnimation(self, b"geometry")
        self._intro.setDuration(THEME.motion.slow)
        self._intro.setStartValue(start)
        self._intro.setEndValue(eff_geo)
        self._intro.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setWindowOpacity(0.0)
        self._fade = QPropertyAnimation(self, b"windowOpacity")
        self._fade.setDuration(THEME.motion.slow)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if hasattr(self, "_intro"):
            self._intro.start()
            self._fade.start()
            del self._intro

    def _center(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.center().x() - self.width() // 2,
                      geo.center().y() - self.height() // 2)
