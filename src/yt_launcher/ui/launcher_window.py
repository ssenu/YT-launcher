"""바탕화면 위젯 형태의 런처 창."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import win32
from ..geometry import Rect
from ..version import APP_NAME
from .tile_grid import TileGrid

EDGE = 6
MIN_W = 240
MIN_H = 200
GEOMETRY_SAVE_DELAY_MS = 500

STYLE = """
#launcher { background: #16181D; border: 1px solid #2A2E37; }
#header { background: #1F232B; }
#title { color: #F1F3F5; font-weight: bold; font-size: 13px; }
#updateBadge { background: #E53935; color: #FFFFFF; border: none; border-radius: 9px;
               padding: 2px 10px; font-weight: bold; }
#menuButton { color: #C9CED6; background: transparent; border: none; font-size: 16px; padding: 0 6px; }
#menuButton::menu-indicator { image: none; }
#progress { background: #2A2E37; border: none; }
#progress::chunk { background: #E53935; }
#tileGrid { background: transparent; border: none; }
"""

_CURSORS = {
    Qt.Edge.LeftEdge | Qt.Edge.TopEdge: Qt.SizeFDiagCursor,
    Qt.Edge.RightEdge | Qt.Edge.BottomEdge: Qt.SizeFDiagCursor,
    Qt.Edge.RightEdge | Qt.Edge.TopEdge: Qt.SizeBDiagCursor,
    Qt.Edge.LeftEdge | Qt.Edge.BottomEdge: Qt.SizeBDiagCursor,
    Qt.Edge.LeftEdge: Qt.SizeHorCursor,
    Qt.Edge.RightEdge: Qt.SizeHorCursor,
    Qt.Edge.TopEdge: Qt.SizeVerCursor,
    Qt.Edge.BottomEdge: Qt.SizeVerCursor,
}


class Header(QWidget):
    """제목·업데이트 배지·메뉴. 드래그하면 창을 옮긴다."""

    def __init__(self, menu: QMenu, can_move: Callable[[], bool], parent=None):
        super().__init__(parent)
        self._can_move = can_move
        self.setObjectName("header")
        self.setAttribute(Qt.WA_StyledBackground, True)

        title = QLabel(APP_NAME)
        title.setObjectName("title")
        self.update_button = QPushButton()
        self.update_button.setObjectName("updateBadge")
        self.update_button.setCursor(Qt.PointingHandCursor)
        self.update_button.hide()
        menu_button = QToolButton()
        menu_button.setObjectName("menuButton")
        menu_button.setText("⋯")
        menu_button.setMenu(menu)
        menu_button.setPopupMode(QToolButton.InstantPopup)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(self.update_button)
        layout.addWidget(menu_button)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._can_move() and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
            return
        super().mousePressEvent(event)


class LauncherWindow(QWidget):
    tile_clicked = Signal(str)
    add_requested = Signal()
    edit_requested = Signal(str)
    delete_requested = Signal(str)
    order_changed = Signal(list)
    update_clicked = Signal()
    geometry_changed = Signal(object)

    def __init__(self, menu: QMenu):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnBottomHint)
        self.setObjectName("launcher")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(MIN_W, MIN_H)
        self.setMouseTracking(True)
        self.setStyleSheet(STYLE)
        self._locked = False
        self._pinned = False

        self.header = Header(menu, lambda: not self._locked, self)
        self.progress = QProgressBar(self)
        self.progress.setObjectName("progress")
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.hide()
        self.grid = TileGrid(self)
        self.grid.setObjectName("tileGrid")
        # 가장자리에서 바뀐 크기 조절 커서가 자식 위젯에 남지 않도록 고정한다.
        for child in (self.header, self.grid, self.progress):
            child.setCursor(Qt.ArrowCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(EDGE, EDGE, EDGE, EDGE)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.progress)
        layout.addWidget(self.grid, 1)

        self.header.update_button.clicked.connect(lambda: self.update_clicked.emit())
        self.grid.tile_clicked.connect(self.tile_clicked)
        self.grid.add_requested.connect(self.add_requested)
        self.grid.edit_requested.connect(self.edit_requested)
        self.grid.delete_requested.connect(self.delete_requested)
        self.grid.order_changed.connect(self.order_changed)

        self._geometry_timer = QTimer(self)
        self._geometry_timer.setSingleShot(True)
        self._geometry_timer.setInterval(GEOMETRY_SAVE_DELAY_MS)
        self._geometry_timer.timeout.connect(self._emit_geometry)

    # 상태 표시
    def set_tiles(self, tiles) -> None:
        self.grid.set_tiles(tiles)

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        if locked:
            self.unsetCursor()

    def show_update_badge(self, text: str) -> None:
        self.header.update_button.setText(text)
        self.header.update_button.show()

    def hide_update_badge(self) -> None:
        self.header.update_button.hide()

    def set_progress(self, done: int, total: int) -> None:
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(min(done, max(total, 1)))
        self.progress.show()

    def hide_progress(self) -> None:
        self.progress.hide()

    # 바탕화면 레이어
    def showEvent(self, event) -> None:
        super().showEvent(event)
        hwnd = int(self.winId())
        if not self._pinned:
            self._pinned = win32.pin_to_desktop(hwnd)
        win32.send_to_bottom(hwnd)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            QTimer.singleShot(0, self._sink_if_app_inactive)

    def _sink_if_app_inactive(self) -> None:
        # 앱의 대화상자·메뉴로 포커스가 옮겨간 경우에는 내리지 않는다.
        if QApplication.activeWindow() is None and self.isVisible():
            win32.send_to_bottom(int(self.winId()))

    # 위치·크기
    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self._geometry_timer.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._geometry_timer.start()

    def _emit_geometry(self) -> None:
        g = self.geometry()
        self.geometry_changed.emit(Rect(g.x(), g.y(), g.width(), g.height()))

    def _edges_at(self, pos: QPoint) -> Qt.Edge:
        edges = Qt.Edge(0)
        if pos.x() <= EDGE:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() >= self.width() - EDGE:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= EDGE:
            edges |= Qt.Edge.TopEdge
        elif pos.y() >= self.height() - EDGE:
            edges |= Qt.Edge.BottomEdge
        return edges

    def leaveEvent(self, event) -> None:
        self.unsetCursor()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event) -> None:
        cursor = None if self._locked else _CURSORS.get(self._edges_at(event.position().toPoint()))
        if cursor is None:
            self.unsetCursor()
        else:
            self.setCursor(cursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and not self._locked and self.windowHandle():
            edges = self._edges_at(event.position().toPoint())
            if edges:
                self.windowHandle().startSystemResize(edges)
                return
        super().mousePressEvent(event)
