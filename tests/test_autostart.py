import sys

from yt_launcher.autostart import AutoStart, RunKeyBackend, launch_command


class FakeBackend:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def delete(self):
        self.value = None


def test_enable_disable_with_fake_backend():
    backend = FakeBackend()
    autostart = AutoStart(backend)
    assert not autostart.is_enabled()
    autostart.enable('"C:\\app\\YTLauncher.exe"')
    assert autostart.is_enabled()
    assert backend.value == '"C:\\app\\YTLauncher.exe"'
    autostart.disable()
    assert not autostart.is_enabled()


def test_launch_command_in_dev_uses_pythonw(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    command = launch_command()
    assert command.endswith('pythonw.exe" -m yt_launcher')


def test_launch_command_when_frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\YT-Launcher\YTLauncher.exe")
    assert launch_command() == '"C:\\Apps\\YT-Launcher\\YTLauncher.exe"'


def test_real_run_key_roundtrip():
    backend = RunKeyBackend(value_name="YTLauncherPytest")
    try:
        backend.set('"C:\\nonexistent\\yt-launcher-test.exe"')
        assert backend.get() == '"C:\\nonexistent\\yt-launcher-test.exe"'
    finally:
        backend.delete()
    assert backend.get() is None
    backend.delete()  # 없는 값 삭제도 예외 없음
