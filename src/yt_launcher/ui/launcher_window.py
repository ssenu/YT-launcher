"""바탕화면 위젯 형태의 런처 창."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
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
from . import themes
from .icons import MENU_ICON_SIZE, THEME_BUTTON_SIZE, dots_icon, palette_icon
from .theme_picker import ThemePicker
from .tile_grid import TileGrid

EDGE = 6
MIN_W = 240
MIN_H = 200
GEOMETRY_SAVE_DELAY_MS = 500
CORNER_RADIUS = 12
SYSTEM_CORNER_RADIUS = 8
PADDING = 14  # 창 안쪽 여백
THEME_FADE_MS = 200

BYLINE = "by_ssenu"

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
        byline = QLabel(BYLINE)
        byline.setObjectName("byline")
        self.update_button = QPushButton()
        self.update_button.setObjectName("updateBadge")
        self.update_button.setCursor(Qt.PointingHandCursor)
        self.update_button.hide()
        self.menu_button = QToolButton()
        self.menu_button.setObjectName("menuButton")
        self.menu_button.setIconSize(QSize(MENU_ICON_SIZE, MENU_ICON_SIZE))
        self.menu_button.setToolTip("메뉴")
        self.menu_button.setMenu(menu)
        self.menu_button.setPopupMode(QToolButton.InstantPopup)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 0, 10)
        layout.addWidget(title)
        layout.addSpacing(4)
        layout.addWidget(byline, 0, Qt.AlignVCenter)
        layout.addStretch(1)
        layout.addWidget(self.update_button)
        layout.addWidget(self.menu_button)

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
    theme_changed = Signal(str)

    def __init__(self, menu: QMenu):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnBottomHint)
        self.setObjectName("launcher")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # 둥근 모서리 바깥은 투명하게 비우고, 배경은 paintEvent에서 직접 그린다.
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(MIN_W, MIN_H)
        self.setMouseTracking(True)
        self._theme = themes.DEFAULT_THEME
        self.setStyleSheet(themes.stylesheet(self._theme))
        self._locked = False
        self._pinned = False
        self._backdrop = False  # Windows 11 아크릴 배경이 켜졌는지
        self._fade: QLabel | None = None

        self.header = Header(menu, lambda: not self._locked, self)
        self.progress = QProgressBar(self)
        self.progress.setObjectName("progress")
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.hide()
        self.grid = TileGrid(self)
        self.grid.setObjectName("tileGrid")
        self.theme_button = QToolButton(self)
        self.theme_button.setObjectName("themeButton")
        self.theme_button.setIconSize(QSize(THEME_BUTTON_SIZE, THEME_BUTTON_SIZE))
        self.theme_button.setFixedSize(THEME_BUTTON_SIZE + 2, THEME_BUTTON_SIZE + 2)
        self.theme_button.setToolTip("테마 색 설정")
        self.theme_button.clicked.connect(self._toggle_theme_picker)
        shadow = QGraphicsDropShadowEffect(self.theme_button)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.theme_button.setGraphicsEffect(shadow)
        self.theme_picker = ThemePicker(self)
        self.theme_picker.picked.connect(self._choose_theme)
        self._refresh_icons()
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 2, 2)
        footer.addStretch(1)
        footer.addWidget(self.theme_button)
        # 가장자리에서 바뀐 크기 조절 커서가 자식 위젯에 남지 않도록 고정한다.
        for child in (self.header, self.grid, self.progress, self.theme_button):
            child.setCursor(Qt.ArrowCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(PADDING, PADDING - 2, PADDING - 4, PADDING - 6)
        layout.setSpacing(8)
        layout.addWidget(self.header)
        layout.addWidget(self.progress)
        layout.addWidget(self.grid, 1)
        layout.addLayout(footer)

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

    @property
    def theme(self) -> str:
        return self._theme

    def set_theme(self, name: str) -> None:
        self._theme = themes.resolve_theme(name)
        self.setStyleSheet(themes.stylesheet(self._theme))
        self.grid.set_add_color(themes.add_tile_color(self._theme))
        self._refresh_icons()
        if self._backdrop:
            win32.set_dark_mode(int(self.winId()), themes.THEMES[self._theme]["dark"])
        self.update()

    def _refresh_icons(self) -> None:
        colors = themes.THEMES[self._theme]
        self.theme_button.setIcon(palette_icon(colors["header"], colors["border"], colors["title"]))
        self.header.menu_button.setIcon(dots_icon(colors["muted"]))

    def _toggle_theme_picker(self) -> None:
        if self.theme_picker.isVisible():
            self.theme_picker.close_picker()
            return
        center = self.theme_button.geometry().center()
        self.theme_picker.open_at(QPointF(center), self._theme)

    def _choose_theme(self, name: str) -> None:
        if name == self._theme:
            return
        self._start_theme_fade()
        self.set_theme(name)
        self.theme_changed.emit(self._theme)

    def _start_theme_fade(self) -> None:
        """이전 모습을 캡처해 덮어 두고 서서히 투명하게 만들어 새 테마로 자연스럽게 넘어간다."""
        if self._fade is not None:
            self._fade.deleteLater()
        fade = QLabel(self)
        fade.setPixmap(self.grab())
        fade.setGeometry(self.rect())
        fade.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        effect = QGraphicsOpacityEffect(fade)
        fade.setGraphicsEffect(effect)
        fade.show()
        fade.raise_()
        anim = QPropertyAnimation(effect, b"opacity", fade)
        anim.setDuration(THEME_FADE_MS)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.finished.connect(fade.deleteLater)
        anim.finished.connect(self._clear_fade)
        anim.start()
        self._fade = fade

    def _clear_fade(self) -> None:
        self._fade = None

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

    def paintEvent(self, event) -> None:
        colors = themes.THEMES[self._theme]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(colors["border"]), 1))
        bg = QColor(colors["bg"])
        if self._backdrop:
            bg.setAlpha(colors["alpha"])  # 뒤의 블러가 은은하게 비치도록
        p.setBrush(bg)
        # 블러 배경은 Windows가 자체 반경(약 8px)으로 둥글게 자르므로 그에 맞춘다.
        radius = SYSTEM_CORNER_RADIUS if self._backdrop else CORNER_RADIUS
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        p.end()

    # 바탕화면 레이어
    def showEvent(self, event) -> None:
        super().showEvent(event)
        hwnd = int(self.winId())
        if not self._pinned:
            self._pinned = win32.pin_to_desktop(hwnd)
            self._backdrop = win32.enable_backdrop(hwnd, themes.THEMES[self._theme]["dark"])
            self.update()
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
        self.theme_picker.close_picker()
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
