# YT Launcher

바탕화면 우상단에 뜨는 타일형 런처. 타일을 누르면 크롬이 최대화 창으로 유튜브 검색 결과를 연다.

## 설치

[Releases](https://github.com/ssenu/YT-launcher/releases/latest)에서 `YT-Launcher-Setup-<버전>.exe`를 받아 실행한다.
코드 서명이 없어 처음에 "Windows의 PC 보호" 창이 뜨면 **추가 정보 → 실행**을 누른다.

## 개발

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m yt_launcher
```

로컬 설치 프로그램 빌드 (Inno Setup 6 필요): `./scripts/build.ps1`

## 릴리스

```powershell
git tag v0.2.0
git push origin v0.2.0
```

GitHub Actions가 테스트 → 빌드 → 릴리스 생성까지 한다. 설치된 앱은 하루 한 번 새 릴리스를 확인하고 "업데이트 있음" 배지를 띄운다.
릴리스 전에 `docs/manual-test-checklist.md`를 확인한다.
