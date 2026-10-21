"""src/yt_launcher/assets/icon.png 와 icon.ico 를 생성한다 (빨간 재생 버튼).

실행: .venv\\Scripts\\python tools\\make_icon.py
"""

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPolygonF

ASSETS = Path(__file__).resolve().parents[1] / "src" / "yt_launcher" / "assets"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def render(size: int) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#E53935"))
    margin = size * 0.06
    painter.drawRoundedRect(QRectF(margin, size * 0.18, size - 2 * margin, size * 0.64), size * 0.16, size * 0.16)
    painter.setBrush(QColor("#FFFFFF"))
    c = size / 2
    painter.drawPolygon(
        QPolygonF([
            QPointF(c - size * 0.12, c - size * 0.16),
            QPointF(c - size * 0.12, c + size * 0.16),
            QPointF(c + size * 0.17, c),
        ])
    )
    painter.end()
    return image


def png_bytes(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data.data())


def build_ico(images: list[tuple[int, bytes]]) -> bytes:
    """PNG 데이터를 담은 ICO 컨테이너 (Windows Vista+)."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    payload = b""
    for size, png in images:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset + len(payload))
        payload += png
    return header + entries + payload


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    ASSETS.mkdir(parents=True, exist_ok=True)
    render(256).save(str(ASSETS / "icon.png"), "PNG")
    (ASSETS / "icon.ico").write_bytes(build_ico([(s, png_bytes(render(s))) for s in ICO_SIZES]))
    print(f"written: {ASSETS}")
    del app


if __name__ == "__main__":
    main()
