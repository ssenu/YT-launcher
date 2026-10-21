from yt_launcher.models import PALETTE, Tile
from yt_launcher.ui.tile_dialog import TileDialog


def test_new_tile_requires_query(qapp):
    dialog = TileDialog()
    assert dialog.windowTitle() == "타일 추가"
    assert not dialog.ok_button.isEnabled()
    dialog.query_edit.setText("   ")
    assert not dialog.ok_button.isEnabled()
    dialog.query_edit.setText("  로파이 음악 ")
    assert dialog.ok_button.isEnabled()
    tile = dialog.result_tile()
    assert tile.query == "로파이 음악"
    assert tile.name == ""
    assert tile.color == ""


def test_pick_palette_color(qapp):
    dialog = TileDialog()
    dialog.query_edit.setText("뉴스")
    dialog.color_buttons[PALETTE[2]].click()
    assert dialog.selected_color() == PALETTE[2]
    dialog.auto_button.click()
    assert dialog.selected_color() == ""


def test_edit_prefills_and_keeps_id(qapp):
    tile = Tile(query="a", name="A", color=PALETTE[0])
    dialog = TileDialog(tile=tile)
    assert dialog.windowTitle() == "타일 수정"
    assert dialog.query_edit.text() == "a"
    assert dialog.name_edit.text() == "A"
    assert dialog.selected_color() == PALETTE[0]
    dialog.name_edit.setText(" B ")
    result = dialog.result_tile()
    assert result.id == tile.id
    assert result.name == "B"
    assert result.color == PALETTE[0]
