import json

from yt_launcher.geometry import Rect
from yt_launcher.models import Tile
from yt_launcher.storage import Config, Storage, default_dir


def test_default_dir_under_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_dir() == tmp_path / "YT-Launcher"


def test_missing_file_returns_defaults(tmp_path):
    config, recovered = Storage(tmp_path).load()
    assert config == Config()
    assert recovered is False


def test_roundtrip(tmp_path):
    storage = Storage(tmp_path / "nested")
    config = Config(
        tiles=[Tile(query="로파이 음악"), Tile(query="뉴스", name="아침", color="#1E88E5")],
        window=Rect(10, 20, 360, 480),
        locked=True,
        autostart=False,
        last_run_version="0.1.0",
        notified_version="0.2.0",
        chrome_notice_shown=True,
    )
    storage.save(config)
    loaded, recovered = storage.load()
    assert loaded == config
    assert recovered is False


def test_save_is_utf8_and_leaves_no_temp_file(tmp_path):
    storage = Storage(tmp_path)
    storage.save(Config(tiles=[Tile(query="로파이")]))
    text = storage.path.read_text(encoding="utf-8")
    assert "로파이" in text
    assert json.loads(text)["schema"] == 1
    assert [p.name for p in tmp_path.iterdir()] == ["config.json"]


def test_corrupt_json_is_backed_up(tmp_path):
    storage = Storage(tmp_path)
    storage.path.write_text("{not json", encoding="utf-8")
    config, recovered = storage.load()
    assert config == Config()
    assert recovered is True
    assert (tmp_path / "config.json.bak").read_text(encoding="utf-8") == "{not json"
    assert not storage.path.exists()


def test_invalid_structure_is_backed_up(tmp_path):
    storage = Storage(tmp_path)
    storage.path.write_text(json.dumps({"tiles": [{"name": "x"}]}), encoding="utf-8")
    config, recovered = storage.load()
    assert config == Config()
    assert recovered is True


def test_non_utf8_file_is_backed_up(tmp_path):
    storage = Storage(tmp_path)
    storage.path.write_bytes(b"\xff\xfe\x00bad")
    config, recovered = storage.load()
    assert config == Config()
    assert recovered is True
    assert (tmp_path / "config.json.bak").read_bytes() == b"\xff\xfe\x00bad"
    assert not storage.path.exists()


def test_overflow_value_is_backed_up(tmp_path):
    storage = Storage(tmp_path)
    storage.path.write_text('{"window": {"x": 1e999, "y": 0, "w": 1, "h": 1}}', encoding="utf-8")
    assert storage.load() == (Config(), True)


def test_backup_failure_does_not_raise(tmp_path, monkeypatch):
    storage = Storage(tmp_path)
    storage.path.write_text("{not json", encoding="utf-8")

    def deny(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr("yt_launcher.storage.os.replace", deny)
    assert storage.load() == (Config(), True)