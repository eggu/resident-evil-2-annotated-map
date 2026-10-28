# RE2 Annotated Map - Survivor's Notes — 1.0.0

## 한국어

첫 공개 릴리스입니다.

- 원작 Resident Evil 2 PC판(GOG + Classic REbirth) 지도에 방 이름, 잠긴 문·열쇠, 핵심 아이템, 문서·지도, 퍼즐, 일반 아이템, 타자기·아이템 상자, 적을 표시합니다.
- 레온/클레어, A/B 시나리오를 반영합니다. 재핑 항목은 아이템 이름 앞의 `[Z]`로 구분합니다.
- 주운 아이템, 연 문, 푼 퍼즐, 쓰러뜨린 적은 사라지고, 아이템이 남은 방은 주황색으로 칠합니다.
- 적은 12종(좀비, 좀비견, 까마귀, 리커, 진화 리커, 거대 거미, 대형 바퀴, 거대 나방, 아이비, 포이즌 아이비, 타일런트, G)의 아이콘으로 표시합니다.
- 숫자 키 0–9로 항목별 표시, 표시 범위, 언어를 바꿉니다. `-`/`+`로 이름 크기, Shift + `-`/`+`로 불투명도를 조절합니다.
- 상태 화면 지도에서 좌/우로 장소, 위/아래로 층을 고릅니다(방문한 층만).
- 기본값: 영어, 이름 100%, 불투명도 70%, 방문한 방만 표시, 방 이름만 켬. 랭크 예상치는 INI의 `Rank=1`로 켭니다.
- 설치: Classic REbirth(1.0.9에서 확인)를 먼저 설치하고 ZIP의 `dsound.dll`, `scripts/`를 게임 폴더에 복사합니다. Ultimate ASI Loader v9.7.4(MIT)를 `dsound.dll`로 포함합니다.

## English

First public release.

- Adds room names, locked doors and keys, key items, documents and maps, puzzles, common items, typewriters and item boxes, and enemies to the map of the original Resident Evil 2 PC release (GOG + Classic REbirth).
- Reflects Leon/Claire and scenarios A/B. Zapping-related entries carry a `[Z]` tag before the item name.
- Picked-up items, opened doors, solved puzzles and killed enemies disappear; rooms with items left are tinted orange.
- Enemies use 12 icons (zombie, zombie dog, crow, licker, evolved licker, giant spider, large roach, giant moth, Ivy, poison Ivy, Tyrant, G).
- Number keys 0–9 toggle categories, visibility scope and language. `-`/`+` changes name size; Shift + `-`/`+` changes opacity.
- On the status-screen map, left/right selects an area and up/down selects a floor (visited floors only).
- Defaults: English, name size 100%, opacity 70%, visited rooms only, only Rooms on. Enable the rank estimate with `Rank=1` in the INI.
- Installation: install Classic REbirth first (tested with 1.0.9), then copy `dsound.dll` and `scripts/` from the ZIP into the game folder. Ultimate ASI Loader v9.7.4 (MIT) is included as `dsound.dll`.
