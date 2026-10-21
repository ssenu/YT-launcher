"""트레이 아이콘."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..version import APP_NAME

NOTIFY_MS = 5000


class Tray(QSystemTrayIcon):
    show_requested = Signal()

    def __init__(self, icon: QIcon, menu: QMenu, parent=None):
        super().__init__(icon, parent)
        self.setToolTip(APP_NAME)
        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_requested.emit()

    def notify(self, message: str) -> None:
        self.showMessage(APP_NAME, message, self.icon(), NOTIFY_MS)
