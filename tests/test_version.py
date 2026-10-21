from packaging.version import Version

from yt_launcher import version


def test_version_is_valid_pep440():
    Version(version.__version__)


def test_release_constants():
    assert version.REPO == "ssenu/YT-launcher"
    assert version.APP_NAME == "YT Launcher"
    assert version.MUTEX_NAME == "YTLauncherMutex"
