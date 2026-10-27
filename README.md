# RE2 Annotated Map - Survivor's Notes — Resident Evil 2 (1998)

[English](README.en.md) | 한국어

**상세 지도: 생존자의 메모** — 원작 Resident Evil 2 PC판(GOG판 `Resident Evil 2.exe` + [Classic REbirth](https://classicrebirth.com/))의 지도에 방 이름, 잠긴 문과 필요한 열쇠, 핵심 아이템, 문서·지도, 퍼즐, 일반 아이템, 타자기·아이템 상자, 몬스터를 표시하는 ASI 모드입니다. 한국어/영어를 지원합니다. RE2 리메이크(2019)용이 아닙니다.

- 게임 자체의 지도 화면에 표시합니다. 주운 아이템, 연 문, 푼 퍼즐, 쓰러뜨린 몬스터는 지도에서 사라집니다. 아이템이 남은 방은 주황색으로 칠합니다.
- 레온/클레어, A/B 시나리오에 따른 아이템·잠긴 문 차이를 반영합니다. 재핑 아이템도 표시합니다.
- 상태 화면 지도에서 좌/우로 장소, 위/아래로 층을 고를 수 있습니다. 이미 방문한 층만 보입니다.
- 원작 결과 화면 공식으로 계산한 랭크 예상치를 켤 수 있습니다(기본 끔).

## 표시 범위와 기본값

새 설정은 **영어, 이름 크기 100%, 불투명도 70%, 방문한 방만 표시**로 시작합니다. 몬스터와 랭크 예상치는 꺼져 있고 다른 항목은 켜져 있습니다. `8`로 범위를 바꿉니다. **모든 방**은 미방문 구역과 아이템을 미리 보여줍니다. 방문한 층만 장소·층 선택에 나타납니다.

## 설치

1. [Releases](https://github.com/eggu/resident-evil-2-annotated-map/releases)에서 `RE2-Annotated-Map-<버전>.zip`을 받습니다. `Source code`는 설치 파일이 아닙니다.
2. 게임을 종료하고 ZIP의 내용(`dsound.dll`, `scripts/`)을 `Resident Evil 2.exe`가 있는 게임 폴더에 폴더 구조 그대로 복사합니다.
3. Classic REbirth는 별도로 설치해야 합니다(1.0.9에서 확인). ASI 로더인 [Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader) v9.7.4(MIT)가 `dsound.dll`로 포함되어 있습니다.
   - 한글 패치 등으로 Ultimate ASI Loader가 이미 `dsound.dll`로 설치되어 있으면 `dsound.dll`은 건너뛰어도 됩니다.
   - ASI 로더가 아닌 다른 `dsound.dll`(예: DSOAL)이 있으면 덮어쓰지 말고, 포함된 `dsound.dll`을 `winmm.dll` 이름으로 복사하세요.

업그레이드할 때는 `scripts/RE2.AnnotatedMap.ini`를 건너뛰거나 백업 후 복원하세요.

제거: `scripts/RE2.AnnotatedMap.asi`, `.ini`, `.log`를 지웁니다. 다른 ASI 모드가 없으면 `dsound.dll`도 지웁니다. EXE와 세이브는 수정하지 않습니다. 지원 대상이 아닌 실행 파일에서는 코드 서명을 확인한 뒤 아무것도 패치하지 않고 로그만 남깁니다.

## 단축키

지도 화면에서만 작동하며, 현재 상태가 왼쪽 아래 범례에 표시됩니다.

| 키 | 동작 |
|---|---|
| 0 | 전체 표시 켜기/끄기 |
| 1 | 방 이름·타자기·아이템 상자 |
| 2 | 잠긴 문·열쇠 |
| 3 | 핵심 아이템 (+ 재핑 아이템) |
| 4 | 문서·지도 |
| 5 | 퍼즐 |
| 6 | 일반 아이템(탄약·회복·잉크 리본) |
| 7 | 몬스터 (방문한 방, 기본 끔) |
| 8 | 표시 범위: 방문한 방 → 공개된 방(층 지도 획득) → 모든 방 |
| 9 | 한국어 / English |
| - / = (+), 숫자패드 - / + | 이름 크기 10%씩 (50–150%) |
| Shift + 위 키 | 이름 불투명도 10%씩 (10–100%) |
| 좌/우, 위/아래 (상태 화면 지도) | 장소·층 선택 (방문한 층만) |

## 설정 (`scripts/RE2.AnnotatedMap.ini`)

배포 ZIP에 설명 주석이 담긴 기본 설정 파일을 포함합니다. 편집 전 게임을 종료하고, 저장 후 게임을 다시 실행하세요. 게임 안에서 바꾼 설정은 자동으로 저장됩니다. 업그레이드할 때 기존 INI를 보존해야 사용자 설정을 유지할 수 있습니다.

| 항목 | 기본값 | 설명 |
|---|---|---|
| `All` | `1` | 전체 표시 스위치 |
| `Rooms` | `1` | 방 이름·타자기·아이템 상자 |
| `Locks` | `1` | 잠긴 문·열쇠 |
| `Items` | `1` | 핵심 아이템 |
| `Documents` | `1` | 문서·지도 |
| `Puzzles` | `1` | 퍼즐·장치 |
| `CommonItems` | `1` | 탄약·회복·잉크 리본 등 일반 아이템 |
| `Monsters` | `0` | 몬스터 |
| `English` | `1` | `1` 영어, `0` 한국어 |
| `Scope` | `1` | `1` 방문한 방, `2` 층 지도로 공개된 방, `3` 모든 방(스포일러) |
| `NameSize` | `100` | 이름 크기(50–150) |
| `NameOpacity` | `70` | 이름 불투명도(10–100) |
| `Rank` | `0` | `1`이면 랭크 예상치 표시. 변경 후 재실행 |

모든 항목은 `[MapOverlay]` 섹션에 있습니다.

확대한 이름은 기존 위치를 유지하므로 겹칠 수 있습니다.

릴리스 변경 사항: [한글·영문 릴리스 노트](RELEASE_NOTES.md).

## 문제 신고

[Issues](https://github.com/eggu/resident-evil-2-annotated-map/issues)에 게임 판본, Classic REbirth 버전, 캐릭터·시나리오, 방·층, 언어·표시 범위와 스크린샷을 함께 남겨 주세요. 로딩 문제는 `scripts/RE2.AnnotatedMap.log`도 첨부하면 도움이 됩니다. 로그의 개인 경로는 지워 주세요.

## 빌드

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python build.py                                              # dist/ ZIP
.venv/bin/python build.py --game-exe '/path/to/Resident Evil 2.exe'    # + 원본 EXE 네이티브 테스트
```

`src/re2_keymap.c`가 런타임 소스이고, 나머지 헤더는 고정된 지도·이름·아이콘 데이터입니다. 자세한 내용은 [개발 문서](docs/DEVELOPMENT.md)를 참고하세요.

## 라이선스

소스는 [MIT License](LICENSE)입니다. 비공식 팬 모드이며 Capcom 및 Classic REbirth와 관련이 없습니다. 참고 자료, 이미지·글꼴 출처는 [NOTICE](NOTICE.md)에 있습니다.
