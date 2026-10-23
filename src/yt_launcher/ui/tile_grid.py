"""타일 그리드: 창 너비에 맞춰 줄바꿈되고 드래그로 순서를 바꾼다."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QStyledItemDelegate,
)

from ..models import Tile

ADD_ID = "__add__"
ADD_COLOR = "#2B2F3A"
ID_ROLE = Qt.UserRole
COLOR_ROLE = Qt.UserRole + 1
SHADOW = 6  # 타일 둘레에 그림자가 번질 여백
TILE_SIZE = QSize(96 + 2 * SHADOW, 66 + 2 * SHADOW)
TILE_RADIUS = 12
TILE_FLAGS = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
HOVER_SCALE = 0.03  # 마우스를 올리면 3% 커진다
PRESS_SCALE = 0.03  # 누르면 3% 작아진다
HOVER_MS = 120
TICK_MS = 16
TEXT_COLOR = QColor(255, 255, 255, 235)


class TileDelegate(QStyledItemDelegate):
    """그림자 + 위에서 아래로 옅어지는 그라데이션 + 마우스 반응 크기 변화."""

    def paint(self, painter: QPainter, option, index) -> None:
        grid = self.parent()
        tile_id = index.data(ID_ROLE)
        level = grid.hover_level(tile_id)
        scale = 1 + HOVER_SCALE * level - (PRESS_SCALE if grid.pressed_id == tile_id else 0)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        base = QRectF(option.rect).adjusted(SHADOW, SHADOW, -SHADOW, -SHADOW)
        w, h = base.width() * scale, base.height() * scale
        rect = QRectF(base.center().x() - w / 2, base.center().y() - h / 2, w, h)

        # 부드러운 그림자: 아래로 조금 내린 둥근 사각형을 점점 크고 옅게 여러 번 겹친다
        painter.setPen(Qt.NoPen)
        for i in range(SHADOW, 0, -1):
            painter.setBrush(QColor(0, 0, 0, int((7 + 6 * level) * (SHADOW - i + 1) / SHADOW)))
            painter.drawRoundedRect(rect.adjusted(-i, -i + 2, i, i + 2), TILE_RADIUS + i, TILE_RADIUS + i)

        color = QColor(index.data(COLOR_ROLE))
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0, color.lighter(int(112 + 10 * level)))
        gradient.setColorAt(1, color.darker(106))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, TILE_RADIUS, TILE_RADIUS)

        font = QFont(option.font)
        font.setWeight(QFont.DemiBold)
        if tile_id == ADD_ID:
            font.setWeight(QFont.Normal)
            font.setPointSizeF(max(font.pointSizeF(), 9.0) + 9)
        painter.setFont(font)
        painter.setPen(TEXT_COLOR)
        flags = int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap)
        painter.drawText(rect.adjusted(8, 4, -8, -4), flags, index.data(Qt.DisplayRole))
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        return TILE_SIZE


class TileGrid(QListWidget):
    tile_clicked = Signal(str)
    add_requested = Signal()
    edit_requested = Signal(str)
    delete_requested = Signal(str)
    order_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.ListMode)
        self.setFlow(QListView.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListView.Adjust)
        self.setUniformItemSizes(True)
        self.setSpacing(1)
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setItemDelegate(TileDelegate(self))
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemClicked.connect(self._on_item_clicked)
        self._add_color = ADD_COLOR
        self._levels: dict[str, float] = {}  # 타일별 마우스 오버 진행도 0~1
        self._hover_id: str | None = None
        self.pressed_id: str | None = None
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(TICK_MS)
        self._hover_timer.timeout.connect(self._step_hover)

    # 마우스 반응
    def hover_level(self, tile_id: str) -> float:
        return self._levels.get(tile_id, 0.0)

    def _set_hover(self, tile_id: str | None) -> None:
        if tile_id != self._hover_id:
            self._hover_id = tile_id
            self._hover_timer.start()

    def _step_hover(self) -> None:
        step = TICK_MS / HOVER_MS
        settled = True
        for tile_id in set(self._levels) | ({self._hover_id} - {None}):
            target = 1.0 if tile_id == self._hover_id else 0.0
            level = self._levels.get(tile_id, 0.0)
            level = min(target, level + step) if target > level else max(target, level - step)
            if level == 0.0:
                self._levels.pop(tile_id, None)
            else:
                self._levels[tile_id] = level
            settled = settled and level == target
        if settled:
            self._hover_timer.stop()
        self.viewport().update()

    def _id_at(self, pos) -> str | None:
        item = self.itemAt(pos)
        return item.data(ID_ROLE) if item is not None else None

    def mouseMoveEvent(self, event) -> None:
        self._set_hover(self._id_at(event.position().toPoint()))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.pressed_id = self._id_at(event.position().toPoint())
            self.viewport().update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self.pressed_id = None
        self.viewport().update()
        super().mouseReleaseEvent(event)

    def viewportEvent(self, event) -> bool:
        if event.type() == QEvent.Leave:
            self._set_hover(None)
            self.pressed_id = None
        return super().viewportEvent(event)

    def set_add_color(self, color: str) -> None:
        """테마에 맞춰 ＋ 타일 색을 바꾼다."""
        self._add_color = color
        for i in range(self.count()):
            if self.item(i).data(ID_ROLE) == ADD_ID:
                self.item(i).setData(COLOR_ROLE, color)

    def set_tiles(self, tiles: list[Tile]) -> None:
        self.clear()
        for tile in tiles:
            item = QListWidgetItem(tile.label)
            item.setData(ID_ROLE, tile.id)
            item.setData(COLOR_ROLE, tile.display_color)
            item.setToolTip(tile.query)
            item.setFlags(TILE_FLAGS)
            item.setSizeHint(TILE_SIZE)
            self.addItem(item)
        add = QListWidgetItem("＋")
        add.setData(ID_ROLE, ADD_ID)
        add.setData(COLOR_ROLE, self._add_color)
        add.setToolTip("검색어 추가")
        add.setFlags(Qt.ItemIsEnabled)
        add.setSizeHint(TILE_SIZE)
        self.addItem(add)

    def tile_ids(self) -> list[str]:
        ids = (self.item(i).data(ID_ROLE) for i in range(self.count()))
        return [tile_id for tile_id in ids if tile_id != ADD_ID]

    def dropEvent(self, event) -> None:
        super().dropEvent(event)
        self._keep_add_last()
        self.order_changed.emit(self.tile_ids())

    def _keep_add_last(self) -> None:
        for i in range(self.count()):
            if self.item(i).data(ID_ROLE) == ADD_ID and i != self.count() - 1:
                self.addItem(self.takeItem(i))
                return

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        tile_id = item.data(ID_ROLE)
        if tile_id == ADD_ID:
            self.add_requested.emit()
        else:
            self.tile_clicked.emit(tile_id)

    def _show_context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        if item is None or item.data(ID_ROLE) == ADD_ID:
            return
        tile_id = item.data(ID_ROLE)
        menu = QMenu(self)
        edit = menu.addAction("수정")
        delete = menu.addAction("삭제")
        chosen = menu.exec(self.viewport().mapToGlobal(pos))
        if chosen is edit:
            self.edit_requested.emit(tile_id)
        elif chosen is delete:
            self.delete_requested.emit(tile_id)
