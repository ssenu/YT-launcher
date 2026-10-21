"""앱 진입점."""

from __future__ import annotations

import getpass
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtWidgets import QApplication

from . import win32
from .app import LauncherApp
from .single_instance import SingleInstance
from .storage import Storage, default_dir
from .version import APP_NAME, MUTEX_NAME, __version__

LOG_MAX_BYTES = 1_000_000
LOG_BACKUPS = 3


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "launcher.log", maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    sys.excepthook = lambda *exc: logging.getLogger("yt_launcher").critical(
        "처리되지 않은 예외", exc_info=exc
    )


def main() -> int:
    data_dir = default_dir()
    setup_logging(data_dir / "logs")
    logging.getLogger(__name__).info("YT Launcher %s 시작", __version__)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    # 명명된 뮤텍스가 중복 실행 방지의 기준이다 (설치 프로그램의 실행 중 감지에도 쓴다).
    # 핸들은 프로세스가 끝날 때까지 일부러 닫지 않고 들고 있는다.
    mutex_handle, existed = win32.acquire_mutex(MUTEX_NAME)
    instance = SingleInstance(f"YTLauncher-{getpass.getuser()}")
    if existed:
        instance.notify_existing()
        return 0
    if mutex_handle is None:
        logging.getLogger(__name__).warning("뮤텍스를 만들지 못했습니다")
    instance.acquire()

    launcher = LauncherApp(app, Storage(data_dir))
    instance.activated.connect(launcher.show_launcher)
    return app.exec()
