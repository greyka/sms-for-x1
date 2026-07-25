"""Точка входа приложения SMS for X1."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import __app_name__, __version__
from .ui.theme import apply_theme
from .ui.main_window import MainWindow
from .viewmodels.app_state import AppState

ASSETS = Path(__file__).resolve().parent.parent / "assets"
APP_ID = "SMSforX1.ModemManager.1"  # AppUserModelID для корректной иконки в панели задач


def _set_app_user_model_id() -> None:
    """Windows группирует кнопки панели задач по AppUserModelID. Без явного ID
    приложение под pythonw наследует иконку лаунчера (.pyw). Задаём свой ID —
    тогда панель задач берёт иконку окна (setWindowIcon)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def _set_native_taskbar_icon(window, icon_path: Path) -> None:
    """Принудительно задать значок окна через WinAPI WM_SETICON.

    Frameless-окно qframelesswindow не всегда транслирует setWindowIcon в
    нативный значок → панель задач показывает generic-иконку. WM_SETICON на
    HWND ставит значок в обход Qt."""
    if sys.platform != "win32" or not icon_path.exists():
        return
    try:
        import ctypes
        u32 = ctypes.windll.user32
        hwnd = int(window.winId())
        IMAGE_ICON, LR_LOADFROMFILE, LR_DEFAULTSIZE = 1, 0x10, 0x40
        WM_SETICON, ICON_SMALL, ICON_BIG = 0x0080, 0, 1
        big = u32.LoadImageW(None, str(icon_path), IMAGE_ICON, 256, 256, LR_LOADFROMFILE)
        small = u32.LoadImageW(None, str(icon_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        if big:
            u32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big)
        if small:
            u32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small)
    except Exception:
        pass


def main() -> int:
    _set_app_user_model_id()

    # High-DPI по умолчанию включён в Qt6; задаём качественное масштабирование
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("SMS for X1")

    icon_path = ASSETS / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    apply_theme(app)

    state = AppState()
    window = MainWindow(state, icon_path=str(icon_path) if icon_path.exists() else None)
    window.show()
    _set_native_taskbar_icon(window, icon_path)

    state.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
