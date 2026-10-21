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

    instance = SingleInstance(f"YTLauncher-{getpass.getuser()}")
    if not instance.acquire():
        return 0
    mutex = win32.create_mutex(MUTEX_NAME)  # 설치 프로그램이 실행 중 여부를 감지하는 데 쓴다

    launcher = LauncherApp(app, Storage(data_dir))
    instance.activated.connect(launcher.show_launcher)
    code = app.exec()
    del mutex
    return code
