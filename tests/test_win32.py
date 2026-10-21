from yt_launcher import win32


def test_is_chrome_exe():
    assert win32.is_chrome_exe(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    assert win32.is_chrome_exe(r"C:\X\CHROME.EXE")
    assert not win32.is_chrome_exe(r"C:\Program Files\Microsoft VS Code\Code.exe")
    assert not win32.is_chrome_exe("")


def test_list_chrome_windows_returns_pairs():
    windows = win32.list_chrome_windows()
    assert isinstance(windows, list)
    for hwnd, title in windows:
        assert isinstance(hwnd, int)
        assert title


def test_create_mutex_returns_handle():
    assert win32.create_mutex("YTLauncherTestMutex") is not None


def test_bottom_and_pin_ignore_invalid_window():
    win32.send_to_bottom(0)  # 잘못된 핸들이어도 예외 없음
    assert win32.pin_to_desktop(0) is False
