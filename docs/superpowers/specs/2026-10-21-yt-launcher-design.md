# YT Launcher 설계

- 작성일: 2026-10-21
- 저장소: https://github.com/ssenu/YT-launcher
- 상태: 승인됨 (구현 계획 작성 전)

## 1. 목표

윈도우 부팅 시 바탕화면 우상단에 PC방 게임 선택 화면 같은 타일형 런처 위젯을 띄운다.
사용자가 검색어로 타일을 추가하고, 타일을 누르면 크롬이 유튜브 검색 결과를 최대화 창으로 연다.
GitHub Releases로 설치 프로그램을 배포하고, 새 버전이 나오면 앱 안에서 원클릭으로 업데이트한다.

### 범위 밖 (YAGNI)

- 타일 썸네일·아이콘 이미지, 그룹/카테고리 탭
- 첫 영상 자동 재생 등 브라우저 자동화
- 크롬 외 브라우저 선택 (크롬이 없을 때 기본 브라우저 폴백만 제공)
- 코드 서명 (SmartScreen 경고는 수용)

## 2. 확정된 요구사항

| 항목 | 결정 |
|---|---|
| 타일 클릭 동작 | 유튜브 검색 결과 페이지까지만 연다: `https://www.youtube.com/results?search_query=<quote_plus 인코딩>` |
| 크롬 창 상태 | 최대화 (`SW_MAXIMIZE`, 타이틀바 더블클릭과 동일). F11 전체화면 아님 |
| 크롬이 이미 실행 중 | 기존 창에 새 탭으로 열고, 그 창을 최대화한 뒤 전면으로 가져온다 |
| 런처 창 레이어 | 바탕화면 위젯: 다른 창 뒤에 깔림, 작업표시줄 아이콘 없음, 트레이 아이콘만 |
| 기본 위치/크기 | 주 모니터 작업 영역 우상단, 여백 16px, 360×480. 이동·크기 조절 가능, 위치 기억 |
| 타일 구성 | 이름(기본값 = 검색어, 수정 가능) + 색상(자동 또는 8색 팔레트). 우클릭 수정/삭제, 드래그로 순서 변경 |
| 기술 스택 | Python + PySide6(Qt 6), PyInstaller(onedir), Inno Setup, GitHub Actions |
| 업데이트 | 헤더 배지 "업데이트 있음 vX.Y.Z" → 클릭 시 원클릭 자동 업데이트 |

## 3. 구조

```
YT-launcher/
├─ src/yt_launcher/
│  ├─ main.py          # 진입점, 단일 인스턴스 보장
│  ├─ version.py       # __version__, REPO = "ssenu/YT-launcher"
│  ├─ models.py        # Tile(id, name, query, color)
│  ├─ storage.py       # config.json 로드/원자적 저장
│  ├─ chrome.py        # 크롬 탐색, 실행, 창 최대화·전면화
│  ├─ updater.py       # 릴리스 확인, 다운로드, 해시 검증, 설치 실행
│  ├─ autostart.py     # HKCU Run 키 on/off
│  └─ ui/
│     ├─ launcher_window.py  # 프레임리스 위젯 창
│     ├─ tile_grid.py        # 반응형 타일 그리드 + 드래그 재정렬
│     ├─ tile_dialog.py      # 타일 추가/수정 대화상자
│     └─ tray.py             # 트레이 아이콘·메뉴
├─ tests/
├─ installer/setup.iss
└─ .github/workflows/release.yml
```

원칙: `storage`, `chrome`, `updater`, `autostart`, `models`는 Qt UI에 의존하지 않는 로직 모듈로 두고 단독 테스트한다. `ui/`는 표시와 입력만 담당하고 로직 모듈을 호출한다. (`updater`의 비동기 실행은 UI 쪽에서 QThread로 감싼다.)

### 3.1 모듈 책임

- **models**: `Tile` dataclass. `id`는 UUID 문자열. `name`이 비면 `query`를 표시명으로 사용.
- **storage**: `%APPDATA%\YT-Launcher\config.json`.
  - 스키마: `{ "schema": 1, "tiles": [Tile...], "window": {x, y, w, h}, "locked": bool }`
  - 저장은 임시 파일에 쓴 뒤 `os.replace`로 교체 (원자적).
  - JSON 파싱 실패 시 `config.json.bak`으로 옮기고 기본 설정으로 시작, UI에 1회 알림.
  - 리스트 순서 = 타일 표시 순서.
- **chrome**:
  - `build_search_url(query) -> str`
  - `find_chrome() -> Path | None`: `HKCU`/`HKLM` `SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe` → `%ProgramFiles%`, `%ProgramFiles(x86)%`, `%LOCALAPPDATA%` 아래 `Google\Chrome\Application\chrome.exe` 순.
  - `open_search(query)`: `subprocess.Popen([chrome, url])` 실행 후 최대 3초간 폴링으로 `Chrome_WidgetWin_1` 클래스의 보이는 최상위 창(최근 전면 창 우선)을 찾아 `ShowWindow(SW_MAXIMIZE)` + `SetForegroundWindow`. 전면화가 거부되면 `AttachThreadInput`으로 재시도.
  - 크롬 미설치 시 `webbrowser.open(url)` 폴백.
  - 같은 타일 1초 이내 재클릭은 무시 (디바운스는 UI 쪽).
- **updater**:
  - `fetch_latest(repo) -> Release | None`: `GET https://api.github.com/repos/{repo}/releases/latest` (timeout 10s, User-Agent 지정). draft/prerelease 제외.
  - `is_newer(latest_tag, current) -> bool`: `packaging.version.Version` 비교, 앞의 `v` 제거.
  - `pick_installer_asset(release)`: 이름이 `YT-Launcher-Setup-*.exe`인 자산.
  - `download(asset, dest, progress_cb)`: `%TEMP%`로 스트리밍 다운로드.
  - `verify_sha256(file, sums_text)`: 릴리스의 `SHA256SUMS.txt`와 대조.
  - `launch_installer(path)`: `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`로 분리 실행.
- **autostart**: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 값 `YTLauncher` = 설치된 exe 경로. `is_enabled()/enable()/disable()`.

## 4. 창 동작

- 창 플래그: `FramelessWindowHint | Tool | WindowStaysOnBottomHint`. 활성화 이벤트 시 Win32 `SetWindowPos(HWND_BOTTOM, SWP_NOACTIVATE|SWP_NOMOVE|SWP_NOSIZE)`로 다시 최하단.
- 이동: 헤더 드래그 (`startSystemMove`). 크기 조절: 가장자리/모서리 (`startSystemResize`). 최소 크기 240×200.
- "위치 잠금"이 켜져 있으면 이동/크기 조절 비활성.
- 위치/크기는 조작 종료 500ms 후 저장 (디바운스).
- 시작 시 저장된 사각형이 어떤 모니터의 작업 영역과도 충분히 겹치지 않으면(모니터 제거 등) 기본 위치로 리셋.
- Win+D(바탕화면 보기): 위젯이 보이도록 유지하는 것이 목표. 구현 시 Windows 11 실기에서 검증하고, 바탕화면 부착 방식이 불안정하면 "바탕화면 보기 해제/전환 시 자동 재표시"로 대체한다. 어떤 경우에도 트레이 아이콘 클릭으로 재표시 가능.
- 단일 인스턴스: `QLocalServer`(이름 `YTLauncher-<user>`)로 보장. 두 번째 실행은 기존 인스턴스에 "show" 메시지를 보내고 종료. 설치 프로그램 연동을 위해 Win32 named mutex `YTLauncherMutex`도 생성.

### 4.1 화면 구성

```
┌──────────────────────────────┐
│ YT Launcher        [업데이트]  ⋯ │  헤더 (드래그 이동, 배지, 메뉴)
├──────────────────────────────┤
│ [타일] [타일] [타일]            │  창 너비에 따라 열 수 자동 조정
│ [ ＋ ]                         │  추가 버튼은 항상 마지막
└──────────────────────────────┘
```

- 헤더 `⋯` 메뉴와 트레이 메뉴 항목: 런처 보이기, 위치·크기 초기화, 위치 잠금, 윈도우 시작 시 실행, 업데이트 확인, 종료.
- 다운로드 중에는 헤더 아래 진행 막대 표시.

### 4.2 타일 흐름

- 추가: `＋` → 대화상자(검색어 필수, 이름 선택, 색상 자동/8색) → 저장 → 그리드 갱신.
- 우클릭: 수정 / 삭제(확인 대화상자).
- 드래그: 순서 변경 후 즉시 저장.
- 클릭: `chrome.open_search(tile.query)`를 워커 스레드에서 실행 (폴링 대기로 UI가 멈추지 않도록).

## 5. 설치·배포

### 5.1 Inno Setup (`installer/setup.iss`)

- `PrivilegesRequired=lowest`, 설치 경로 `{localappdata}\Programs\YT-Launcher` → UAC 없음, "설정 → 앱"에 등록/제거 가능.
- 고정 `AppId` GUID로 업그레이드 시 덮어쓰기.
- `AppMutex=YTLauncherMutex`로 실행 중 감지, `CloseApplications=yes`.
- 시작 메뉴 바로가기 기본, 바탕화면 바로가기는 선택 태스크.
- 태스크 "윈도우 시작 시 실행"(기본 체크) → HKCU Run 등록. 제거 시 Run 값 삭제(`uninsdeletevalue`).
- `[Run]` 항목은 `postinstall` 플래그 없이(조용한 설치에서도 실행되도록) `nowait`로 앱 재실행. 일반 설치에서는 마지막 페이지에서 실행 체크박스 제공.
- 제거 시 `%APPDATA%\YT-Launcher` 설정은 남긴다.

### 5.2 GitHub Actions (`.github/workflows/release.yml`)

- 트리거: `v*` 태그 push.
- `windows-latest`에서: PySide6가 공식 지원하는 Python 버전 고정 설치 → 의존성 설치 → `pytest` → 태그에서 버전 주입(`version.py`) → PyInstaller onedir `--windowed` → Inno Setup(`iscc`, 미설치 시 choco로 설치) → `SHA256SUMS.txt` 생성 → 릴리스 생성 및 `YT-Launcher-Setup-X.Y.Z.exe`, `SHA256SUMS.txt` 첨부.
- 릴리스 절차: `git tag vX.Y.Z && git push origin vX.Y.Z`.

## 6. 업데이트

- 확인 시점: 앱 시작 30초 후 1회, 이후 24시간마다(앱이 계속 켜져 있는 경우), 메뉴의 "업데이트 확인" 수동 실행.
- 새 버전 발견: 헤더 배지 "업데이트 있음 vX.Y.Z" + 트레이 알림 1회 (같은 버전은 다시 알리지 않음).
- 배지 클릭 흐름:
  1. 확인 대화상자 "vX.Y.Z로 업데이트할까요? (런처가 잠시 꺼졌다 켜집니다)"
  2. 설치 파일을 `%TEMP%`로 다운로드 (진행 막대)
  3. `SHA256SUMS.txt`로 해시 검증, 불일치 시 중단
  4. 설치 프로그램을 조용한 모드로 분리 실행하고 런처 즉시 종료
  5. 설치 프로그램이 덮어쓰기 후 런처 재실행
  6. 재실행된 런처가 버전 상승을 감지하면 "vX.Y.Z로 업데이트됨" 1회 알림 (마지막 실행 버전은 config에 저장)

## 7. 오류 처리

| 상황 | 동작 |
|---|---|
| 업데이트 확인 실패 (오프라인, API 레이트리밋 등) | 표시 없이 다음 주기 재시도 |
| 다운로드 실패 / 해시 불일치 | 배지를 "업데이트 실패 · 다시 시도"로 변경, 메뉴에 "릴리스 페이지 열기" 제공 |
| 크롬 미설치 | 기본 브라우저로 열기, 최초 1회 안내 |
| 크롬 창 최대화/전면화 실패 | 검색은 열렸으므로 무시, 로그 기록 |
| 설정 파일 손상 | `.bak` 백업 후 기본 설정으로 시작, 알림 |
| 중복 실행 | 기존 인스턴스 전면 표시 후 새 프로세스 종료 |

- 로그: `%APPDATA%\YT-Launcher\logs\launcher.log`, `RotatingFileHandler` (1MB × 3).

## 8. 테스트

- **자동 (pytest, CI 필수 통과)**: UI 비의존 로직 모듈 대상.
  - storage: 저장/로드 왕복, 원자적 저장, 손상 파일 복구
  - chrome: URL 인코딩(한글·공백·`&`·`#`), 크롬 경로 탐색(레지스트리/파일 존재 모킹)
  - updater: 버전 비교, 릴리스 JSON 파싱, 자산 선택, SHA256 검증
  - autostart: Run 키 on/off (winreg 모킹)
- **수동 체크리스트 (릴리스 전)**:
  - 첫 실행 시 우상단 배치, 이동·크기 조절 후 재시작 시 복원
  - 다른 창 뒤에 깔림, 작업표시줄 미표시, Win+D 동작
  - 크롬 꺼짐/켜짐 각각에서 최대화·전면화
  - 다중 모니터, 모니터 제거 후 위치 리셋
  - 설치 → 앱 목록 등록 확인 → 원클릭 업데이트 → 제거
  - 재부팅 후 자동 실행
