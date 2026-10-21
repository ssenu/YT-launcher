import hashlib
import io
import json
import subprocess
from urllib.error import HTTPError, URLError

import pytest

from yt_launcher import updater
from yt_launcher.updater import Asset, Release, UpdateError

INSTALLER = b"installer-bytes"
INSTALLER_SHA = "204676736cea68d6411da9d3aa3fab0a5e70b023ba30cd560cfa9c8e7250f4df"


def release_json(**overrides):
    data = {
        "tag_name": "v0.2.0",
        "html_url": "https://github.com/ssenu/YT-launcher/releases/tag/v0.2.0",
        "draft": False,
        "prerelease": False,
        "assets": [
            {"name": "YT-Launcher-Setup-0.2.0.exe", "browser_download_url": "https://dl/setup.exe", "size": len(INSTALLER)},
            {"name": "SHA256SUMS.txt", "browser_download_url": "https://dl/sums.txt", "size": 100},
            {"name": "source.zip", "browser_download_url": "https://dl/src.zip", "size": 5},
        ],
    }
    data.update(overrides)
    return data


class FakeOpener:
    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        result = self.responses[request.full_url]
        if isinstance(result, Exception):
            raise result
        return io.BytesIO(result)


def test_parse_release_picks_assets():
    release = updater.parse_release(release_json())
    assert release.tag == "v0.2.0"
    assert release.version == "0.2.0"
    assert release.installer == Asset("YT-Launcher-Setup-0.2.0.exe", "https://dl/setup.exe", len(INSTALLER))
    assert release.sums.name == "SHA256SUMS.txt"


def test_parse_release_skips_draft_and_prerelease():
    assert updater.parse_release(release_json(draft=True)) is None
    assert updater.parse_release(release_json(prerelease=True)) is None
    assert updater.parse_release(release_json(tag_name="")) is None


@pytest.mark.parametrize(
    ("candidate", "current", "expected"),
    [
        ("v0.2.0", "0.1.0", True),
        ("0.1.0", "0.1.0", False),
        ("v0.1.0", "0.2.0", False),
        ("v0.10.0", "0.9.0", True),
        ("garbage", "0.1.0", False),
    ],
)
def test_is_newer(candidate, current, expected):
    assert updater.is_newer(candidate, current) is expected


def test_fetch_latest_parses_and_sends_headers():
    url = "https://api.github.com/repos/ssenu/YT-launcher/releases/latest"
    opener = FakeOpener({url: json.dumps(release_json()).encode()})
    release = updater.fetch_latest("ssenu/YT-launcher", opener=opener)
    assert release.version == "0.2.0"
    assert opener.requests[0].get_header("User-agent").startswith("YT-Launcher/")


def test_fetch_latest_404_means_no_release():
    url = "https://api.github.com/repos/ssenu/YT-launcher/releases/latest"
    opener = FakeOpener({url: HTTPError(url, 404, "Not Found", None, None)})
    assert updater.fetch_latest("ssenu/YT-launcher", opener=opener) is None


def test_fetch_latest_network_error_raises():
    url = "https://api.github.com/repos/ssenu/YT-launcher/releases/latest"
    opener = FakeOpener({url: URLError("offline")})
    with pytest.raises(UpdateError):
        updater.fetch_latest("ssenu/YT-launcher", opener=opener)


def test_parse_sums():
    text = f"{INSTALLER_SHA.upper()}  YT-Launcher-Setup-0.2.0.exe\nabc *other.exe\n\n"
    assert updater.parse_sums(text) == {
        "YT-Launcher-Setup-0.2.0.exe": INSTALLER_SHA,
        "other.exe": "abc",
    }


def test_sha256_file(tmp_path):
    path = tmp_path / "f"
    path.write_bytes(INSTALLER)
    assert updater.sha256_file(path) == hashlib.sha256(INSTALLER).hexdigest() == INSTALLER_SHA


def test_download_and_verify_success(tmp_path):
    release = updater.parse_release(release_json())
    opener = FakeOpener({
        "https://dl/sums.txt": f"{INSTALLER_SHA}  YT-Launcher-Setup-0.2.0.exe\n".encode(),
        "https://dl/setup.exe": INSTALLER,
    })
    progress = []
    path = updater.download_and_verify(release, tmp_path, progress=lambda d, t: progress.append((d, t)), opener=opener)
    assert path == tmp_path / "YT-Launcher-Setup-0.2.0.exe"
    assert path.read_bytes() == INSTALLER
    assert progress[-1] == (len(INSTALLER), len(INSTALLER))
    assert not list(tmp_path.glob("*.part"))


def test_download_and_verify_hash_mismatch(tmp_path):
    release = updater.parse_release(release_json())
    opener = FakeOpener({
        "https://dl/sums.txt": f"{'0' * 64}  YT-Launcher-Setup-0.2.0.exe\n".encode(),
        "https://dl/setup.exe": INSTALLER,
    })
    with pytest.raises(UpdateError):
        updater.download_and_verify(release, tmp_path, opener=opener)
    assert not (tmp_path / "YT-Launcher-Setup-0.2.0.exe").exists()


def test_download_and_verify_requires_assets(tmp_path):
    release = Release("v0.2.0", "0.2.0", "", None, None)
    with pytest.raises(UpdateError):
        updater.download_and_verify(release, tmp_path, opener=FakeOpener({}))


def test_download_network_error_cleans_partial(tmp_path):
    asset = Asset("YT-Launcher-Setup-0.2.0.exe", "https://dl/setup.exe", 10)
    opener = FakeOpener({"https://dl/setup.exe": URLError("offline")})
    with pytest.raises(UpdateError):
        updater.download(asset, tmp_path / asset.name, opener=opener)
    assert list(tmp_path.iterdir()) == []


def test_launch_installer_runs_silently(tmp_path):
    calls = []
    updater.launch_installer(tmp_path / "setup.exe", popen=lambda args, **kw: calls.append((args, kw)))
    args, kwargs = calls[0]
    assert args == [str(tmp_path / "setup.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
    assert kwargs["creationflags"] & subprocess.DETACHED_PROCESS
