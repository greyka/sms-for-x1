"""Нижний статус-бар: подключение, оператор, сигнал, версия приложения."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from qfluentwidgets import CaptionLabel

from .. import __version__
from ..config import THEME
from ..core.models import ConnState, ModemStatus
from .components.badges import Dot

P = THEME.palette


class _Segment(QWidget):
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.dot = Dot(P.text_tertiary, size=8, pulse=False, parent=self)
        self.label = CaptionLabel(text, self)
        self.label.setStyleSheet(f"color: {P.text_secondary};")
        lay.addWidget(self.dot)
        lay.addWidget(self.label)

    def set(self, text: str, color: str, pulse: bool = False) -> None:
        self.label.setText(text)
        self.dot.set_color(color, pulse)


class StatusBar(QFrame):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(38)
        self.setStyleSheet(f"""
            #statusBar {{
                background-color: {P.rgba(P.panel, 0.75)};
                border-top: 1px solid {P.rgba(P.text, 0.06)};
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(20)

        self.conn = _Segment("Подключение: —", self)
        self.signal = _Segment("Сигнал: —", self)
        lay.addWidget(self.conn)
        lay.addWidget(self._sep())
        lay.addWidget(self.signal)
        lay.addStretch(1)

        ver = CaptionLabel(f"SMS for X1  ·  v{__version__}", self)
        ver.setStyleSheet(f"color: {P.text_tertiary};")
        lay.addWidget(ver)

        state.statusChanged.connect(self._on_status)

    def _sep(self) -> QFrame:
        s = QFrame(self)
        s.setFixedSize(1, 16)
        s.setStyleSheet(f"background-color: {P.rgba(P.text, 0.10)};")
        return s

    def _on_status(self, st: ModemStatus) -> None:
        color = {
            ConnState.CONNECTED: P.success,
            ConnState.CONNECTING: P.warning,
            ConnState.DISCONNECTED: P.error,
            ConnState.UNKNOWN: P.text_tertiary,
        }[st.state]
        self.conn.set(f"{st.provider or 'Модем'}: {st.state.label}", color,
                      pulse=st.state == ConnState.CONNECTED)
        scol = P.success if st.signal_bars >= 3 else P.warning if st.signal_bars == 2 else P.error
        self.signal.set(f"Сигнал: {st.signal_percent}%  ({st.signal_label})", scol)
