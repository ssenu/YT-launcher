import pytest

from yt_launcher.models import PALETTE, Tile, auto_color


def test_palette_has_eight_colors():
    assert len(PALETTE) == 8
    assert PALETTE[0] == "#B5544C"


def test_label_falls_back_to_query():
    assert Tile(query="로파이 음악").label == "로파이 음악"
    assert Tile(query="로파이 음악", name="  ").label == "로파이 음악"
    assert Tile(query="로파이 음악", name="공부").label == "공부"


def test_auto_color_is_deterministic_and_in_palette():
    assert auto_color("lofi") == auto_color("lofi")
    assert auto_color("lofi") in PALETTE


def test_display_color_prefers_explicit_color():
    assert Tile(query="lofi", color="#123456").display_color == "#123456"
    assert Tile(query="lofi").display_color == auto_color("lofi")


def test_ids_are_unique():
    assert Tile(query="a").id != Tile(query="a").id


def test_dict_roundtrip():
    tile = Tile(query="뉴스", name="아침 뉴스", color=PALETTE[3])
    assert Tile.from_dict(tile.to_dict()) == tile


def test_from_dict_generates_missing_id():
    tile = Tile.from_dict({"query": "운동"})
    assert tile.query == "운동"
    assert tile.name == ""
    assert len(tile.id) == 32


def test_from_dict_rejects_empty_or_missing_query():
    with pytest.raises(ValueError):
        Tile.from_dict({"query": "   "})
    with pytest.raises(KeyError):
        Tile.from_dict({"name": "x"})


def test_legacy_bright_colors_map_to_muted_palette():
    from yt_launcher.models import migrate_color

    assert migrate_color("#E53935") == PALETTE[0]
    assert migrate_color("#f4511e") == PALETTE[7]
    assert migrate_color("#123456") == "#123456"
    assert Tile(query="a", color="#1E88E5").display_color == PALETTE[4]
