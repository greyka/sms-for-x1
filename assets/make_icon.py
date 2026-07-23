"""Рендер assets/icon.svg → icon.ico (много размеров) и icon.png.

Запуск: python assets/make_icon.py
"""
from __future__ import annotations

import io
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QByteArray
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication
from PIL import Image

HERE = Path(__file__).resolve().parent
SVG = HERE / "icon.svg"
ICO = HERE / "icon.ico"
PNG = HERE / "icon.png"
SIZES = [16, 24, 32, 48, 64, 128, 256]


def render(size: int, data: QByteArray) -> Image.Image:
    renderer = QSvgRenderer(data)
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()

    # QImage → PNG bytes → PIL
    from PySide6.QtCore import QBuffer
    qbuf = QBuffer()
    qbuf.open(QBuffer.OpenModeFlag.ReadWrite)
    img.save(qbuf, "PNG")
    buf = io.BytesIO(bytes(qbuf.data()))
    return Image.open(buf).convert("RGBA")


def main() -> None:
    app = QApplication.instance() or QApplication([])
    data = QByteArray(SVG.read_bytes())

    frames = [render(s, data) for s in SIZES]
    # PNG 256
    frames[-1].save(PNG, format="PNG")
    # ICO со всеми размерами
    frames[-1].save(ICO, format="ICO",
                    sizes=[(s, s) for s in SIZES])
    print(f"OK: {ICO.name} ({ICO.stat().st_size} B), {PNG.name}")


if __name__ == "__main__":
    main()
