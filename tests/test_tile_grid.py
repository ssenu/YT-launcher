from yt_launcher.models import Tile
from yt_launcher.ui.tile_grid import ADD_ID, ID_ROLE, TileGrid


def test_set_tiles_puts_add_button_last(qapp):
    grid = TileGrid()
    a, b = Tile(query="a"), Tile(query="b", name="비")
    grid.set_tiles([a, b])
    assert grid.count() == 3
    assert grid.item(0).text() == "a"
    assert grid.item(1).text() == "비"
    assert grid.item(2).data(ID_ROLE) == ADD_ID
    assert grid.tile_ids() == [a.id, b.id]


def test_set_tiles_replaces_previous_items(qapp):
    grid = TileGrid()
    grid.set_tiles([Tile(query="a"), Tile(query="b")])
    grid.set_tiles([Tile(query="c")])
    assert grid.count() == 2


def test_click_emits_tile_or_add(qapp):
    grid = TileGrid()
    tile = Tile(query="a")
    grid.set_tiles([tile])
    clicked, added = [], []
    grid.tile_clicked.connect(clicked.append)
    grid.add_requested.connect(lambda: added.append(True))
    grid.itemClicked.emit(grid.item(0))
    grid.itemClicked.emit(grid.item(1))
    assert clicked == [tile.id]
    assert added == [True]


def test_keep_add_last_after_reorder(qapp):
    grid = TileGrid()
    a, b = Tile(query="a"), Tile(query="b")
    grid.set_tiles([a, b])
    grid.insertItem(0, grid.takeItem(grid.count() - 1))
    grid._keep_add_last()
    assert grid.item(grid.count() - 1).data(ID_ROLE) == ADD_ID
    assert grid.tile_ids() == [a.id, b.id]
