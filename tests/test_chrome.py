from pathlib import Path

from yt_launcher import chrome


def test_build_search_url_encodes_korean_and_specials():
    assert chrome.build_search_url("로파이 음악") == (
        "https://www.youtube.com/results?search_query="
        "%EB%A1%9C%ED%8C%8C%EC%9D%B4+%EC%9D%8C%EC%95%85"
    )
    assert chrome.build_search_url("lofi & chill #1").endswith("lofi+%26+chill+%231")
    assert chrome.build_search_url("  a b  ").endswith("=a+b")


def test_find_chrome_prefers_registry(tmp_path):
    exe = tmp_path / "chrome.exe"
    exe.write_bytes(b"")
    assert chrome.find_chrome(registry_lookup=lambda: exe, env={}) == exe


def test_find_chrome_falls_back_to_known_paths(tmp_path):
    local = tmp_path / "local"
    exe = local / "Google" / "Chrome" / "Application" / "chrome.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    env = {"PROGRAMFILES": str(tmp_path / "pf"), "LOCALAPPDATA": str(local)}
    assert chrome.find_chrome(registry_lookup=lambda: None, env=env) == exe


def test_find_chrome_returns_none_when_missing(tmp_path):
    env = {"PROGRAMFILES": str(tmp_path)}
    assert chrome.find_chrome(registry_lookup=lambda: None, env=env) is None


def test_registry_lookup_does_not_crash():
    result = chrome.registry_chrome_path()
    assert result is None or result.is_file()


def test_open_search_launches_chrome_and_focuses():
    calls = []
    used = chrome.open_search(
        "lofi",
        Path(r"C:\chrome.exe"),
        popen=lambda args, **kw: calls.append(("popen", args)),
        focus=lambda: calls.append(("focus",)),
        browser_open=lambda url: calls.append(("browser", url)),
        allow_foreground=lambda: calls.append(("allow",)),
    )
    assert used is True
    assert calls == [
        ("allow",),
        ("popen", [r"C:\chrome.exe", "https://www.youtube.com/results?search_query=lofi"]),
        ("focus",),
    ]


def test_open_search_falls_back_to_default_browser():
    calls = []
    used = chrome.open_search(
        "lofi",
        None,
        popen=lambda args, **kw: calls.append("popen"),
        focus=lambda: calls.append("focus"),
        browser_open=lambda url: calls.append(url),
        allow_foreground=lambda: calls.append("allow"),
    )
    assert used is False
    assert calls == ["https://www.youtube.com/results?search_query=lofi"]
