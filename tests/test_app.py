from yt_launcher.app import LauncherApp
from yt_launcher.autostart import AutoStart
from yt_launcher.geometry import Rect
from yt_launcher.models import Tile
from yt_launcher.storage import Config, Storage
from yt_launcher.updater import Asset, Release
from yt_launcher.version import __version__


class FakeBackend:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def delete(self):
        self.value = None


def make_app(qapp, storage, backend=None, frozen=False):
    return LauncherApp(
        qapp, storage, autostart=AutoStart(backend or FakeBackend()), frozen=frozen, show=False
    )


def test_tile_crud_and_reorder_persist(qapp, tmp_path):
    storage = Storage(tmp_path)
    app = make_app(qapp, storage)
    a, b = Tile(query="a"), Tile(query="b")
    app.add_tile(a)
    app.add_tile(b)
    assert app.window.grid.tile_ids() == [a.id, b.id]
    app.reorder([b.id, a.id])
    app.update_tile(Tile(query="a2", id=a.id))
    app.remove_tile(b.id)
    saved, _ = storage.load()
    assert [(t.id, t.query) for t in saved.tiles] == [(a.id, "a2")]
    assert app.window.grid.tile_ids() == [a.id]


def test_reorder_keeps_unknown_tiles(qapp, tmp_path):
    app = make_app(qapp, Storage(tmp_path))
    a, b, c = Tile(query="a"), Tile(query="b"), Tile(query="c")
    for tile in (a, b, c):
        app.add_tile(tile)
    app.reorder([c.id, a.id])
    assert [t.id for t in app.config.tiles] == [c.id, a.id, b.id]


def test_records_last_run_version(qapp, tmp_path):
    storage = Storage(tmp_path)
    make_app(qapp, storage)
    assert storage.load()[0].last_run_version == __version__


def test_restores_saved_geometry_or_defaults(qapp, tmp_path):
    storage = Storage(tmp_path)
    storage.save(Config(window=Rect(-9000, -9000, 300, 300)))
    app = make_app(qapp, storage)
    g = app.window.geometry()
    assert g.x() > -9000  # 화면 밖 위치는 기본 위치로 복구


def test_update_found_shows_badge_once(qapp, tmp_path):
    storage = Storage(tmp_path)
    app = make_app(qapp, storage)
    release = Release("v99.0.0", "99.0.0", "https://example/release", None, None)
    app._on_update_found(release)
    assert not app.window.header.update_button.isHidden()
    assert "99.0.0" in app.window.header.update_button.text()
    assert storage.load()[0].notified_version == "99.0.0"
    assert app.release is release


def test_frozen_applies_saved_autostart_preference(qapp, tmp_path):
    storage = Storage(tmp_path)
    storage.save(Config(autostart=False))
    backend = FakeBackend('"C:\\old\\YTLauncher.exe"')
    make_app(qapp, storage, backend=backend, frozen=True)
    assert backend.value is None


def test_dev_mode_does_not_touch_autostart(qapp, tmp_path):
    storage = Storage(tmp_path)
    storage.save(Config(autostart=False))
    backend = FakeBackend('"C:\\old\\YTLauncher.exe"')
    make_app(qapp, storage, backend=backend, frozen=False)
    assert backend.value == '"C:\\old\\YTLauncher.exe"'


def test_set_autostart_updates_config_and_registry(qapp, tmp_path):
    storage = Storage(tmp_path)
    backend = FakeBackend()
    app = make_app(qapp, storage, backend=backend)
    app.set_autostart(True)
    assert backend.value is not None
    assert storage.load()[0].autostart is True
    app.set_autostart(False)
    assert backend.value is None
    assert storage.load()[0].autostart is False


def test_set_locked_persists(qapp, tmp_path):
    storage = Storage(tmp_path)
    app = make_app(qapp, storage)
    app.set_locked(True)
    assert storage.load()[0].locked is True


def test_release_without_assets_shows_no_badge(qapp, tmp_path, monkeypatch):
    app = make_app(qapp, Storage(tmp_path))
    release = Release("v99.0.0", "99.0.0", "https://example/release", None, None)
    monkeypatch.setattr("yt_launcher.app.updater.fetch_latest", lambda repo: release)
    app._check_in_background(False)
    qapp.processEvents()
    assert app.window.header.update_button.isHidden()
    assert app.release is None


def test_release_with_assets_shows_badge(qapp, tmp_path, monkeypatch):
    app = make_app(qapp, Storage(tmp_path))
    asset = Asset("Setup.exe", "https://example/Setup.exe", 1)
    release = Release("v99.0.0", "99.0.0", "https://example/release", asset, asset)
    monkeypatch.setattr("yt_launcher.app.updater.fetch_latest", lambda repo: release)
    app._check_in_background(False)
    qapp.processEvents()
    assert not app.window.header.update_button.isHidden()
    assert app.release is release

def test_theme_change_persists_and_restores(qapp, tmp_path):
    storage = Storage(tmp_path)
    app = make_app(qapp, storage)
    assert app.window.theme == "dark"
    app.window.theme_menu.actions()[2].trigger()  # 세피아
    assert storage.load()[0].theme == "sepia"
    app2 = make_app(qapp, storage)
    assert app2.window.theme == "sepia"
