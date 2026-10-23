"""Win32 API 래퍼 (ctypes). 실패해도 예외 대신 False/None을 돌려준다."""

from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes
from pathlib import Path

log = logging.getLogger(__name__)

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")

SW_MAXIMIZE = 3
HWND_BOTTOM = wintypes.HWND(1)
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
GWLP_HWNDPARENT = -8
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
ERROR_ALREADY_EXISTS = 183
ASFW_ANY = 0xFFFFFFFF
CHROME_CLASS = "Chrome_WidgetWin_1"

LONG_PTR = ctypes.c_ssize_t
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
user32.AllowSetForegroundWindow.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
user32.SetWindowLongPtrW.restype = LONG_PTR
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE


def is_chrome_exe(path: str) -> bool:
    return bool(path) and Path(path).name.lower() == "chrome.exe"


def _class_name(hwnd) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _window_text(hwnd) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _process_image(hwnd) -> str:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def list_chrome_windows() -> list[tuple[int, str]]:
    """보이는 크롬 최상위 창을 Z순서(위가 먼저)로 돌려준다."""
    found: list[tuple[int, str]] = []

    @WNDENUMPROC
    def callback(hwnd, _lparam):
        if hwnd and user32.IsWindowVisible(hwnd) and _class_name(hwnd) == CHROME_CLASS:
            title = _window_text(hwnd)
            if title and is_chrome_exe(_process_image(hwnd)):
                found.append((int(hwnd), title))
        return True

    user32.EnumWindows(callback, 0)
    return found


def maximize_and_focus(hwnd: int) -> bool:
    user32.ShowWindow(hwnd, SW_MAXIMIZE)
    if user32.SetForegroundWindow(hwnd):
        return True
    foreground = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(foreground, None) if foreground else 0
    current = kernel32.GetCurrentThreadId()
    attached = bool(fg_thread and fg_thread != current and user32.AttachThreadInput(current, fg_thread, True))
    try:
        user32.BringWindowToTop(hwnd)
        return bool(user32.SetForegroundWindow(hwnd))
    finally:
        if attached:
            user32.AttachThreadInput(current, fg_thread, False)


def focus_chrome_window(timeout: float = 5.0, settle: float = 0.5, poll: float = 0.1) -> bool:
    """방금 연 유튜브 탭의 크롬 창을 찾아 최대화하고 전면으로 가져온다."""
    time.sleep(settle)
    deadline = time.monotonic() + timeout
    while True:
        windows = list_chrome_windows()
        target = next((hwnd for hwnd, title in windows if "YouTube" in title), None)
        if target is not None or time.monotonic() >= deadline:
            break
        time.sleep(poll)
    if target is None and windows:
        target = windows[0][0]
    if target is None:
        log.warning("크롬 창을 찾지 못했습니다")
        return False
    return maximize_and_focus(target)


def allow_any_foreground() -> None:
    user32.AllowSetForegroundWindow(ASFW_ANY)


def send_to_bottom(hwnd: int) -> None:
    user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)


def pin_to_desktop(hwnd: int) -> bool:
    """창의 소유자를 바탕화면(Progman)으로 지정해 Win+D에도 남도록 한다."""
    progman = user32.FindWindowW("Progman", None)
    if not progman or not hwnd:
        return False
    user32.SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, progman)
    return True


def acquire_mutex(name: str) -> tuple[int | None, bool]:
    """명명된 뮤텍스를 만든다. (핸들, 이미 다른 프로세스가 가지고 있었는지)를 돌려준다."""
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, False, name)
    existed = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
    return (int(handle) if handle else None), existed


def create_mutex(name: str) -> int | None:
    return acquire_mutex(name)[0]


DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMWCP_ROUND = 2
DWMSBT_TRANSIENTWINDOW = 3  # 아크릴(뒤가 흐리게 비치는 재질)


class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


dwmapi.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long
dwmapi.DwmExtendFrameIntoClientArea.argtypes = [wintypes.HWND, ctypes.POINTER(MARGINS)]
dwmapi.DwmExtendFrameIntoClientArea.restype = ctypes.c_long


def _set_dwm_int(hwnd: int, attribute: int, value: int) -> bool:
    data = ctypes.c_int(value)
    return dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data)) == 0


def set_dark_mode(hwnd: int, dark: bool) -> bool:
    """블러 배경의 밝기 톤(어두운/밝은)을 정한다."""
    return bool(hwnd) and _set_dwm_int(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, int(dark))


def enable_backdrop(hwnd: int, dark: bool) -> bool:
    """Windows 11 아크릴 배경을 켠다. 지원하지 않는 Windows(10 등)면 False."""
    if not hwnd:
        return False
    set_dark_mode(hwnd, dark)
    _set_dwm_int(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND)
    margins = MARGINS(-1, -1, -1, -1)
    dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
    return _set_dwm_int(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_TRANSIENTWINDOW)
