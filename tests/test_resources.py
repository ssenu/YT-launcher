from yt_launcher.resources import app_icon, asset_path


def test_icon_files_exist():
    assert asset_path("icon.png").is_file()
    ico = asset_path("icon.ico").read_bytes()
    assert ico[:4] == b"\x00\x00\x01\x00"


def test_app_icon_loads(qapp):
    assert not app_icon().isNull()
