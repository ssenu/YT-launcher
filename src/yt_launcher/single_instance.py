"""QLocalServer로 앱 중복 실행을 막는다."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

log = logging.getLogger(__name__)

CONNECT_TIMEOUT_MS = 300


class SingleInstance(QObject):
    activated = Signal()

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.server: QLocalServer | None = None

    def notify_existing(self) -> bool:
        """실행 중인 인스턴스에 "show"를 보낸다. 연결되면 True."""
        socket = QLocalSocket()
        socket.connectToServer(self.name)
        if not socket.waitForConnected(CONNECT_TIMEOUT_MS):
            return False
        socket.write(b"show")
        socket.flush()
        socket.waitForBytesWritten(CONNECT_TIMEOUT_MS)
        socket.disconnectFromServer()
        return True

    def acquire(self) -> bool:
        if self.notify_existing():
            return False
        QLocalServer.removeServer(self.name)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_new_connection)
        if not self.server.listen(self.name):
            # 중복 실행 방지는 뮤텍스가 맡으므로 계속 실행한다 (다만 두 번째 실행의 알림은 못 받는다).
            log.warning("로컬 서버 시작 실패: %s", self.server.errorString())
        return True

    def _on_new_connection(self) -> None:
        while self.server.hasPendingConnections():
            connection = self.server.nextPendingConnection()
            connection.disconnected.connect(connection.deleteLater)
            connection.disconnectFromServer()
            self.activated.emit()
