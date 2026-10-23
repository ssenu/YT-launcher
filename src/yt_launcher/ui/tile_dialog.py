"""타일 추가·수정 대화상자."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QToolButton,
)

from ..models import PALETTE, Tile, migrate_color


class TileDialog(QDialog):
    def __init__(self, parent=None, tile: Tile | None = None):
        super().__init__(parent)
        self._tile = tile
        self.setWindowTitle("타일 수정" if tile else "타일 추가")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(340)

        self.query_edit = QLineEdit(tile.query if tile else "")
        self.query_edit.setPlaceholderText("유튜브에서 검색할 단어")
        self.name_edit = QLineEdit(tile.name if tile else "")
        self.name_edit.setPlaceholderText("비우면 검색어를 그대로 사용")

        self.color_group = QButtonGroup(self)
        self.color_group.setExclusive(True)
        colors = QHBoxLayout()
        colors.setSpacing(4)
        self.auto_button = self._color_button("", "자동")
        colors.addWidget(self.auto_button)
        self.color_buttons: dict[str, QToolButton] = {}
        for color in PALETTE:
            button = self._color_button(color, "")
            self.color_buttons[color] = button
            colors.addWidget(button)
        current = migrate_color(tile.color) if tile else ""
        (self.color_buttons.get(current) or self.auto_button).setChecked(True)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = self.buttons.button(QDialogButtonBox.Ok)
        self.ok_button.setText("저장")
        self.buttons.button(QDialogButtonBox.Cancel).setText("취소")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        form = QFormLayout(self)
        form.addRow("검색어", self.query_edit)
        form.addRow("표시 이름", self.name_edit)
        form.addRow("색상", colors)
        form.addRow(self.buttons)

        self.query_edit.textChanged.connect(self._update_ok)
        self._update_ok()

    def _color_button(self, color: str, text: str) -> QToolButton:
        button = QToolButton(self)
        button.setCheckable(True)
        button.setProperty("color", color)
        button.setText(text)
        button.setFixedSize(QSize(44 if text else 24, 24))
        if color:
            button.setStyleSheet(
                f"QToolButton {{ background: {color}; border: 2px solid transparent; border-radius: 4px; }}"
                "QToolButton:checked { border-color: #202020; }"
            )
        self.color_group.addButton(button)
        return button

    def _update_ok(self) -> None:
        self.ok_button.setEnabled(bool(self.query_edit.text().strip()))

    def selected_color(self) -> str:
        button = self.color_group.checkedButton()
        return str(button.property("color") or "") if button else ""

    def result_tile(self) -> Tile:
        query = self.query_edit.text().strip()
        name = self.name_edit.text().strip()
        color = self.selected_color()
        if self._tile is not None:
            return Tile(query=query, name=name, color=color, id=self._tile.id)
        return Tile(query=query, name=name, color=color)
