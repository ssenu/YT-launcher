"""HKCU Run 키로 윈도우 시작 시 자동 실행을 켜고 끈다."""

from __future__ import annotations

import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "YTLauncher"


class RunKeyBackend:
    def __init__(self, value_name: str = VALUE_NAME):
        self.value_name = value_name

    def get(self) -> str | None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                value, _ = winreg.QueryValueEx(key, self.value_name)
        except FileNotFoundError:
            return None
        return str(value)

    def set(self, value: str) -> None:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, self.value_name, 0, winreg.REG_SZ, value)

    def delete(self) -> None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, self.value_name)
        except FileNotFoundError:
            pass


def launch_command() -> str:
    """Run 키에 등록할 실행 명령."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    return f'"{pythonw}" -m yt_launcher'


class AutoStart:
    def __init__(self, backend=None):
        self.backend = backend or RunKeyBackend()

    def is_enabled(self) -> bool:
        return self.backend.get() is not None

    def enable(self, command: str | None = None) -> None:
        self.backend.set(command or launch_command())

    def disable(self) -> None:
        self.backend.delete()
