"""타일 그리드: 창 너비에 맞춰 줄바꿈되고 드래그로 순서를 바꾼다."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QStyle,
    QStyledItemDelegate,
)

from ..models import Tile

ADD_ID = "__add__"
ADD_COLOR = "#2B2F3A"
ID_ROLE = Qt.UserRole
COLOR_ROLE = Qt.UserRole + 1
TILE_SIZE = QSize(100, 68)
TILE_FLAGS = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled


class TileDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(option.rect).adjusted(3, 3, -3, -3)
        color = QColor(index.data(COLOR_ROLE))
        if option.state & QStyle.StateFlag.State_MouseOver:
            color = color.lighter(120)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 10, 10)

        font = QFont(option.font)
        font.setBold(True)
        if index.data(ID_ROLE) == ADD_ID:
            font.setPointSizeF(max(font.pointSizeF(), 9.0) + 8)
        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        flags = int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap)
        painter.drawText(rect.adjusted(6, 4, -6, -4), flags, index.data(Qt.DisplayRole))
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
        self.setSpacing(2)
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
