"""애플리케이션 컨트롤러: 설정·창·트레이·크롬 실행·업데이트를 연결한다."""

from __future__ import annotations

import logging
import shutil
import sys
import tempfile
import threading
import time
import webbrowser
from pathlib import Path

from PySide6.QtCore import QObject, QRect, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QMenu, QMessageBox

from . import chrome, updater
from .autostart import AutoStart, launch_command
from .geometry import Rect, default_rect, is_visible_on_any
from .models import Tile
from .resources import app_icon
from .storage import Storage
from .ui.launcher_window import LauncherWindow
from .ui.tile_dialog import TileDialog
from .ui.tray import Tray
from .version import REPO, __version__

log = logging.getLogger(__name__)

FIRST_CHECK_DELAY_MS = 30_000
CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000
CLICK_DEBOUNCE_S = 1.0
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"
UPDATE_DIR_NAME = "YT-Launcher-update"


def _to_rect(rect: QRect) -> Rect:
    return Rect(rect.x(), rect.y(), rect.width(), rect.height())


class _Signals(QObject):
    """백그라운드 스레드 → UI 스레드 전달용."""

    update_found = Signal(object)
    update_none = Signal(bool, bool)  # manual, ok
    download_progress = Signal(int, int)
    download_done = Signal(object)
    download_failed = Signal(str)
    chrome_done = Signal(bool)


class LauncherApp(QObject):
    def __init__(
        self,
        qapp,
        storage: Storage,
        *,
        autostart: AutoStart | None = None,
        frozen: bool | None = None,
        show: bool = True,
    ):
        super().__init__()
        self.qapp = qapp
        self.storage = storage
        self.autostart = autostart or AutoStart()
        self.frozen = getattr(sys, "frozen", False) if frozen is None else frozen
        self.config, recovered = storage.load()
        self.release: updater.Release | None = None
        self._downloading = False
        self._last_click: dict[str, float] = {}
        self.signals = _Signals()

        self.menu = QMenu()
        self._build_menu()
        self.window = LauncherWindow(self.menu)
        self.tray = Tray(app_icon(), self.menu)
        self._connect()

        self._restore_geometry()
        self.window.set_locked(self.config.locked)
        self.window.set_tiles(self.config.tiles)
        self._apply_autostart_preference()

        self._update_timer = QTimer(self)
        self._update_timer.setInterval(CHECK_INTERVAL_MS)
        self._update_timer.timeout.connect(lambda: self.check_updates(manual=False))

        if show:
            self.window.show()
            self.tray.show()
            QTimer.singleShot(FIRST_CHECK_DELAY_MS, lambda: self.check_updates(manual=False))
            self._update_timer.start()

        self._announce_updated()
        if recovered:
            self.tray.notify("설정 파일이 손상되어 초기화했습니다. 이전 파일은 config.json.bak에 있습니다.")

    # 구성
    def _build_menu(self) -> None:
        self.action_show = self.menu.addAction("런처 보이기")
        self.action_reset = self.menu.addAction("위치·크기 초기화")
        self.action_lock = self.menu.addAction("위치 잠금")
        self.action_lock.setCheckable(True)
        self.action_lock.setChecked(self.config.locked)
        self.action_autostart = self.menu.addAction("윈도우 시작 시 실행")
        self.action_autostart.setCheckable(True)
        self.menu.addSeparator()
        self.action_check = self.menu.addAction("업데이트 확인")
        self.action_releases = self.menu.addAction("릴리스 페이지 열기")
        self.menu.addSeparator()
        self.action_quit = self.menu.addAction("종료")
        self.menu.aboutToShow.connect(
            lambda: self.action_autostart.setChecked(self.autostart.is_enabled())
        )

    def _connect(self) -> None:
        self.action_show.triggered.connect(self.show_launcher)
        self.action_reset.triggered.connect(self.reset_geometry)
        self.action_lock.toggled.connect(self.set_locked)
        self.action_autostart.triggered.connect(self.set_autostart)
        self.action_check.triggered.connect(lambda: self.check_updates(manual=True))
        self.action_releases.triggered.connect(self.open_releases_page)
        self.action_quit.triggered.connect(self.quit)
        self.tray.show_requested.connect(self.show_launcher)

        w = self.window
        w.tile_clicked.connect(self.open_tile)
        w.add_requested.connect(self._add_with_dialog)
        w.edit_requested.connect(self._edit_with_dialog)
        w.delete_requested.connect(self._confirm_delete)
        w.order_changed.connect(self.reorder)
        w.update_clicked.connect(self.start_update)
        w.geometry_changed.connect(self._save_geometry)

        s = self.signals
        s.update_found.connect(self._on_update_found)
        s.update_none.connect(self._on_update_none)
        s.download_progress.connect(w.set_progress)
        s.download_done.connect(self._on_download_done)
        s.download_failed.connect(self._on_download_failed)
        s.chrome_done.connect(self._on_chrome_done)

    def _save(self) -> None:
        try:
            self.storage.save(self.config)
        except OSError:
            log.exception("설정 저장 실패")

    # 창 위치
    def _primary_work_area(self) -> Rect:
        return _to_rect(QGuiApplication.primaryScreen().availableGeometry())

    def _restore_geometry(self) -> None:
        works = [_to_rect(screen.availableGeometry()) for screen in QGuiApplication.screens()]
        rect = self.config.window
        if rect is None or not is_visible_on_any(rect, works):
            rect = default_rect(self._primary_work_area())
        self.window.setGeometry(rect.x, rect.y, rect.w, rect.h)

    def reset_geometry(self) -> None:
        rect = default_rect(self._primary_work_area())
        self.window.setGeometry(rect.x, rect.y, rect.w, rect.h)
        self._save_geometry(rect)

    def _save_geometry(self, rect: Rect) -> None:
        self.config.window = rect
        self._save()

    def set_locked(self, locked: bool) -> None:
        self.config.locked = locked
        self.window.set_locked(locked)
        self._save()

    def show_launcher(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    # 타일
    def _find(self, tile_id: str) -> Tile | None:
        return next((t for t in self.config.tiles if t.id == tile_id), None)

    def _tiles_changed(self) -> None:
        self.window.set_tiles(self.config.tiles)
        self._save()

    def add_tile(self, tile: Tile) -> None:
        self.config.tiles.append(tile)
        self._tiles_changed()

    def update_tile(self, tile: Tile) -> None:
        self.config.tiles = [tile if t.id == tile.id else t for t in self.config.tiles]
        self._tiles_changed()

    def remove_tile(self, tile_id: str) -> None:
        self.config.tiles = [t for t in self.config.tiles if t.id != tile_id]
        self._tiles_changed()

    def reorder(self, ids: list[str]) -> None:
        # 그리드는 이미 새 순서로 그려져 있으므로 설정만 갱신한다 (dropEvent 도중 호출됨).
        by_id = {t.id: t for t in self.config.tiles}
        ordered = [by_id.pop(tile_id) for tile_id in ids if tile_id in by_id]
        self.config.tiles = ordered + list(by_id.values())
        self._save()

    def _add_with_dialog(self) -> None:
        dialog = TileDialog(self.window)
        if dialog.exec() == QDialog.Accepted:
            self.add_tile(dialog.result_tile())

    def _edit_with_dialog(self, tile_id: str) -> None:
        tile = self._find(tile_id)
        if tile is None:
            return
        dialog = TileDialog(self.window, tile)
        if dialog.exec() == QDialog.Accepted:
            self.update_tile(dialog.result_tile())

    def _confirm_delete(self, tile_id: str) -> None:
        tile = self._find(tile_id)
        if tile is None:
            return
        answer = QMessageBox.question(self.window, "타일 삭제", f"'{tile.label}' 타일을 삭제할까요?")
        if answer == QMessageBox.StandardButton.Yes:
            self.remove_tile(tile_id)

    def open_tile(self, tile_id: str) -> None:
        tile = self._find(tile_id)
        if tile is None:
            return
        now = time.monotonic()
        if now - self._last_click.get(tile_id, -CLICK_DEBOUNCE_S) < CLICK_DEBOUNCE_S:
            return
        self._last_click[tile_id] = now
        threading.Thread(target=self._open_in_background, args=(tile.query,), daemon=True).start()

    def _open_in_background(self, query: str) -> None:
        try:
            used_chrome = chrome.open_search(query, chrome.find_chrome())
        except Exception:
            log.exception("검색 열기 실패")
            return
        self.signals.chrome_done.emit(used_chrome)

    def _on_chrome_done(self, used_chrome: bool) -> None:
        if used_chrome or self.config.chrome_notice_shown:
            return
        self.config.chrome_notice_shown = True
        self._save()
        self.tray.notify("크롬을 찾지 못해 기본 브라우저로 열었습니다.")

    # 자동 실행
    def set_autostart(self, enabled: bool) -> None:
        self.config.autostart = enabled
        self._save()
        self._sync_autostart(enabled)

    def _sync_autostart(self, enabled: bool) -> None:
        try:
            if enabled:
                self.autostart.enable(launch_command())
            else:
                self.autostart.disable()
        except OSError:
            log.exception("자동 실행 설정 실패")

    def _apply_autostart_preference(self) -> None:
        # 업데이트 설치가 Run 키를 되살려도 사용자가 앱에서 고른 값을 유지한다.
        if self.frozen and self.config.autostart is not None:
            self._sync_autostart(self.config.autostart)

    # 업데이트
    def _announce_updated(self) -> None:
        previous = self.config.last_run_version
        if previous == __version__:
            return
        if previous and updater.is_newer(__version__, previous):
            self.tray.notify(f"v{__version__} 버전으로 업데이트되었습니다.")
        self.config.last_run_version = __version__
        self._save()

    def check_updates(self, manual: bool = False) -> None:
        threading.Thread(target=self._check_in_background, args=(manual,), daemon=True).start()

    def _check_in_background(self, manual: bool) -> None:
        try:
            release = updater.fetch_latest(REPO)
        except Exception:
            log.warning("업데이트 확인 실패", exc_info=True)
            self.signals.update_none.emit(manual, False)
            return
        if release and updater.is_newer(release.version, __version__):
            if release.installer is not None and release.sums is not None:
                self.signals.update_found.emit(release)
            else:
                log.warning("릴리스 %s에 설치 파일 또는 SHA256SUMS가 없어 건너뜁니다", release.tag)
                self.signals.update_none.emit(manual, True)
        else:
            self.signals.update_none.emit(manual, True)

    def _on_update_found(self, release: updater.Release) -> None:
        self.release = release
        if not self._downloading:
            self.window.show_update_badge(f"업데이트 있음 v{release.version}")
        if self.config.notified_version != release.version:
            self.config.notified_version = release.version
            self._save()
            self.tray.notify(f"새 버전(v{release.version})이 나왔습니다. 런처의 업데이트 버튼을 눌러 설치하세요.")

    def _on_update_none(self, manual: bool, ok: bool) -> None:
        if manual:
            self.tray.notify("최신 버전입니다." if ok else "업데이트를 확인하지 못했습니다. 인터넷 연결을 확인하세요.")

    def start_update(self) -> None:
        if self.release is None or self._downloading:
            return
        answer = QMessageBox.question(
            self.window,
            "업데이트",
            f"v{self.release.version} 버전으로 업데이트할까요?\n런처가 잠시 꺼졌다 켜집니다.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._downloading = True
        self.window.hide_update_badge()
        self.window.set_progress(0, 1)
        threading.Thread(target=self._download_in_background, args=(self.release,), daemon=True).start()

    def _download_in_background(self, release: updater.Release) -> None:
        dest = Path(tempfile.gettempdir()) / UPDATE_DIR_NAME
        try:
            shutil.rmtree(dest, ignore_errors=True)  # 이전 시도의 찌꺼기 제거
            path = updater.download_and_verify(release, dest, progress=self.signals.download_progress.emit)
        except Exception as exc:
            log.warning("업데이트 다운로드 실패: %s", exc)
            self.signals.download_failed.emit(str(exc))
            return
        self.signals.download_done.emit(path)

    def _on_download_done(self, path: Path) -> None:
        try:
            updater.launch_installer(path)
        except Exception as exc:
            self._on_download_failed(str(exc))
            return
        self.quit()

    def _on_download_failed(self, message: str) -> None:
        self._downloading = False
        self.window.hide_progress()
        self.window.show_update_badge("업데이트 실패 · 다시 시도")
        self.tray.notify(f"업데이트에 실패했습니다: {message}")

    def open_releases_page(self) -> None:
        url = self.release.html_url if self.release and self.release.html_url else RELEASES_URL
        webbrowser.open(url)

    def quit(self) -> None:
        # 디바운스 중인 위치·크기 저장을 종료 전에 즉시 반영한다.
        if self.window._geometry_timer.isActive():
            self.window._geometry_timer.stop()
            self.window._emit_geometry()
        self.tray.hide()
        self.qapp.quit()
