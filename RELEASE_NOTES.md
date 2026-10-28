# RE2 Annotated Map - Survivor's Notes — 1.0.0

## 한국어

첫 공개 릴리스입니다.

- 지도 범례의 적 표시를 `적` / `ENEMIES`로 표기합니다.

- 재핑 항목은 아이템 이름과 구분되도록 `[Z]`로 표시합니다.

- 생성 시점부터 죽은 시체, 연출·동결 개체와 방 밖의 몬스터 스폰은 표시하지 않습니다. 잠복 후 활동하는 적은 유지합니다.
- 경찰서 1층 동쪽 사무실 금고 퍼즐을 미해결 상태에서 표시합니다.

- 원작 Resident Evil 2 PC판(GOG + Classic REbirth) 지도에 방 이름, 잠긴 문·열쇠, 핵심 아이템, 문서·지도, 퍼즐, 일반 아이템, 타자기·아이템 상자, 몬스터를 표시합니다.
- 레온/클레어, A/B 시나리오, 재핑 아이템을 반영합니다. 주운 아이템과 쓰러뜨린 몬스터는 사라지고, 아이템이 남은 방은 주황색으로 칠합니다.
- 숫자 키 0–9로 항목별 표시, 표시 범위, 언어를 바꿉니다. `-`/`+`로 이름 크기, Shift + `-`/`+`로 불투명도를 조절합니다.
- 상태 화면 지도에서 좌/우로 장소, 위/아래로 층을 고릅니다(방문한 층만).
- 랭크 예상치를 INI의 `Rank=1`로 켤 수 있습니다(기본 끔).
- `scripts/RE2.AnnotatedMap.asi`로 설치합니다. Ultimate ASI Loader v9.7.4(MIT)를 `dsound.dll`로 포함하며, Classic REbirth는 별도로 설치해야 합니다.

## English

First public release.

- The enemy legend uses `적` / `ENEMIES`.

- Zapping-related entries use a separate `[Z]` tag before the item name.

- Excludes initial corpses, cinematic/frozen actors and monster spawns outside their rooms, while retaining dormant enemies that can wake.
- Marks the Police Station 1F East Office safe until it is unlocked.

- Adds room names, locked doors and keys, key items, documents and maps, puzzles, common items, typewriters and item boxes, and monsters to the map of the original Resident Evil 2 PC release (GOG + Classic REbirth).
- Reflects Leon/Claire, scenarios A/B and zapping items. Picked-up items and killed monsters disappear; rooms with items left are tinted orange.
- Number keys 0–9 toggle categories, visibility scope and language. `-`/`+` changes name size; Shift + `-`/`+` changes opacity.
- On the status-screen map, left/right selects an area and up/down selects a floor (visited floors only).
- The rank estimate can be enabled with `Rank=1` in the INI (off by default).
- Installs as `scripts/RE2.AnnotatedMap.asi`. Ultimate ASI Loader v9.7.4 (MIT) is included as `dsound.dll`; Classic REbirth must be installed separately.
