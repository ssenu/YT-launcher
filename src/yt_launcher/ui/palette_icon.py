"""테마 버튼용 팔레트 아이콘 (원 안에 그린 물감 팔레트)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

ICON_SIZE = 30
_RENDER_SIZE = 96  # 크게 그린 뒤 줄여서 경계를 매끄럽게 한다
_BOARD = "#F2E2C4"
_BOARD_EDGE = "#B89B6C"
_PAINTS = ("#E53935", "#FDD835", "#43A047", "#1E88E5")


def palette_pixmap(circle: str, edge: str, size: int = _RENDER_SIZE) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    s = size / 96  # 아래 좌표는 96px 기준
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)

    # 바탕 원
    p.setPen(QPen(QColor(edge), 3 * s))
    p.setBrush(QColor(circle))
    p.drawEllipse(QRectF(3 * s, 3 * s, 90 * s, 90 * s))

    # 팔레트 판: 타원에서 오른쪽 아래 엄지 구멍을 뺀 모양
    board = QPainterPath()
    board.addEllipse(QRectF(18 * s, 24 * s, 60 * s, 48 * s))
    hole = QPainterPath()
    hole.addEllipse(QPointF(60 * s, 58 * s), 7 * s, 7 * s)
    p.setPen(QPen(QColor(_BOARD_EDGE), 2.5 * s))
    p.setBrush(QColor(_BOARD))
    p.drawPath(board.subtracted(hole))

    # 물감 방울
    p.setPen(Qt.NoPen)
    for color, (x, y) in zip(_PAINTS, ((32, 42), (44, 34), (58, 36), (34, 57))):
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(x * s, y * s), 6 * s, 6 * s)
    p.end()
    return pixmap


def palette_icon(circle: str, edge: str) -> QIcon:
    return QIcon(palette_pixmap(circle, edge))
