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


def main() -> int:
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

    state.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
