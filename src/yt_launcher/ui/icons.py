"""런처 창에 쓰는 아이콘을 QPainter로 직접 그린다 (테마 색을 따라감)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

THEME_BUTTON_SIZE = 40
MENU_ICON_SIZE = 24
_RENDER_SIZE = 96  # 크게 그린 뒤 줄여서 경계를 매끄럽게 한다


def _canvas(size: int) -> tuple[QPixmap, QPainter]:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    return pixmap, painter


def palette_pixmap(circle: str, edge: str, glyph: str, size: int = _RENDER_SIZE) -> QPixmap:
    """색이 채워진 원 안에 선으로 그린 팔레트 (엄지 구멍 + 물감 자리 3개)."""
    pixmap, p = _canvas(size)
    s = size / 96  # 아래 좌표는 96px 기준

    p.setPen(QPen(QColor(edge), 2 * s))
    p.setBrush(QColor(circle))
    p.drawEllipse(QRectF(2 * s, 2 * s, 92 * s, 92 * s))

    board = QPainterPath()
    board.addEllipse(QRectF(27 * s, 29 * s, 42 * s, 38 * s))
    thumb = QPainterPath()
    thumb.addEllipse(QPointF(58 * s, 57 * s), 7 * s, 7 * s)
    pen = QPen(QColor(glyph), 5 * s)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawPath(board.subtracted(thumb))

    p.setPen(Qt.NoPen)
    p.setBrush(QColor(glyph))
    for x, y in ((38, 46), (45, 38), (55, 40)):
        p.drawEllipse(QPointF(x * s, y * s), 3.6 * s, 3.6 * s)
    p.end()
    return pixmap


def palette_icon(circle: str, edge: str, glyph: str) -> QIcon:
    return QIcon(palette_pixmap(circle, edge, glyph))


def dots_icon(color: str, size: int = _RENDER_SIZE) -> QIcon:
    """메뉴 버튼용 가로 점 3개."""
    pixmap, p = _canvas(size)
    s = size / 96
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    for x in (22, 48, 74):
        p.drawEllipse(QPointF(x * s, 48 * s), 8 * s, 8 * s)
    p.end()
    return QIcon(pixmap)
