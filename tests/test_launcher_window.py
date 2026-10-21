from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from yt_launcher.geometry import Rect
from yt_launcher.models import Tile
from yt_launcher.resources import app_icon
from yt_launcher.ui.launcher_window import LauncherWindow
from yt_launcher.ui.tray import Tray


def test_window_flags_make_desktop_widget(qapp):
    window = LauncherWindow(QMenu())
    flags = window.windowFlags()
    assert flags & Qt.FramelessWindowHint
    assert flags & Qt.WindowStaysOnBottomHint
    assert (flags & Qt.Tool) == Qt.Tool
    assert window.minimumSize().width() == 240
    assert window.minimumSize().height() == 200


def test_tiles_badge_and_progress(qapp):
    window = LauncherWindow(QMenu())
    window.set_tiles([Tile(query="a"), Tile(query="b")])
    assert window.grid.count() == 3
    assert window.header.update_button.isHidden()
    window.show_update_badge("업데이트 있음 v0.2.0")
    assert not window.header.update_button.isHidden()
    assert window.header.update_button.text() == "업데이트 있음 v0.2.0"
    window.hide_update_badge()
    assert window.header.update_button.isHidden()
    assert window.progress.isHidden()
    window.set_progress(5, 10)
    assert not window.progress.isHidden()
    assert window.progress.value() == 5
    window.hide_progress()
    assert window.progress.isHidden()


def test_update_badge_click_emits(qapp):
    window = LauncherWindow(QMenu())
    clicked = []
    window.update_clicked.connect(lambda: clicked.append(True))
    window.show_update_badge("업데이트 있음 v0.2.0")
    window.header.update_button.click()
    assert clicked == [True]


def test_edges_at(qapp):
    window = LauncherWindow(QMenu())
    window.resize(300, 300)
    assert window._edges_at(QPoint(1, 1)) == Qt.Edge.LeftEdge | Qt.Edge.TopEdge
    assert window._edges_at(QPoint(299, 150)) == Qt.Edge.RightEdge
    assert window._edges_at(QPoint(150, 299)) == Qt.Edge.BottomEdge
    assert window._edges_at(QPoint(150, 150)) == Qt.Edge(0)


def test_geometry_signal_reports_rect(qapp):
    window = LauncherWindow(QMenu())
    got = []
    window.geometry_changed.connect(got.append)
    window.setGeometry(10, 20, 300, 400)
    window._emit_geometry()
    assert got[-1] == Rect(10, 20, 300, 400)


def test_tray_click_requests_show(qapp):
    tray = Tray(app_icon(), QMenu())
    shown = []
    tray.show_requested.connect(lambda: shown.append(True))
    tray._on_activated(QSystemTrayIcon.ActivationReason.Trigger)
    tray._on_activated(QSystemTrayIcon.ActivationReason.Context)
    assert shown == [True]


def test_children_use_arrow_cursor(qapp):
    window = LauncherWindow(QMenu())
    window.setCursor(Qt.SizeHorCursor)  # 가장자리에서 바뀐 커서가 자식에게 새지 않아야 한다
    assert window.grid.cursor().shape() == Qt.ArrowCursor
    assert window.header.cursor().shape() == Qt.ArrowCursor
    assert window.progress.cursor().shape() == Qt.ArrowCursor
    assert window.header.update_button.cursor().shape() == Qt.PointingHandCursor

def test_header_shows_byline(qapp):
    from PySide6.QtWidgets import QLabel

    window = LauncherWindow(QMenu())
    labels = {label.objectName(): label.text() for label in window.header.findChildren(QLabel)}
    assert labels["title"] == "YT Launcher"
    assert labels["byline"] == "by_ssenu"


def test_theme_menu_lists_three_themes(qapp):
    window = LauncherWindow(QMenu())
    assert window.theme_button.objectName() == "themeButton"
    assert [a.text() for a in window.theme_menu.actions()] == ["라이트", "다크", "세피아"]
    assert window.theme == "dark"


def test_choosing_theme_restyles_and_emits(qapp):
    from yt_launcher.ui import themes
    from yt_launcher.ui.tile_grid import ADD_ID, COLOR_ROLE, ID_ROLE

    window = LauncherWindow(QMenu())
    window.set_tiles([Tile(query="a")])
    got = []
    window.theme_changed.connect(got.append)
    light = window.theme_menu.actions()[0]
    light.trigger()
    assert got == ["light"]
    assert window.theme == "light"
    assert light.isChecked()
    assert themes.THEMES["light"]["bg"] in window.styleSheet()
    add_item = window.grid.item(window.grid.count() - 1)
    assert add_item.data(ID_ROLE) == ADD_ID
    assert add_item.data(COLOR_ROLE) == themes.THEMES["light"]["add"]
    light.trigger()  # 같은 테마를 다시 고르면 신호 없음
    assert got == ["light"]


def test_set_theme_keeps_add_color_after_retile(qapp):
    from yt_launcher.ui import themes
    from yt_launcher.ui.tile_grid import COLOR_ROLE

    window = LauncherWindow(QMenu())
    window.set_theme("sepia")
    window.set_tiles([Tile(query="a")])
    assert window.grid.item(1).data(COLOR_ROLE) == themes.THEMES["sepia"]["add"]


def test_unknown_theme_falls_back_to_dark(qapp):
    window = LauncherWindow(QMenu())
    window.set_theme("neon")
    assert window.theme == "dark"


def test_theme_button_uses_drawn_palette_icon(qapp):
    window = LauncherWindow(QMenu())
    assert window.theme_button.text() == ""
    assert not window.theme_button.icon().isNull()
    before = window.theme_button.icon().pixmap(30).toImage()
    window.set_theme("light")
    assert window.theme_button.icon().pixmap(30).toImage() != before  # 테마에 맞춰 다시 그림
