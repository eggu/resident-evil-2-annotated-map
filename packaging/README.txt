RE2 Annotated Map - Survivor's Notes - Resident Evil 2 (1998)
상세 지도: 생존자의 메모

지원: GOG판 Resident Evil 2(Resident Evil 2.exe) + Ultimate ASI Loader(HD 모드는 Classic REbirth 필요).
Classic REbirth는 별도로 설치하며 HD 모드에만 필요합니다(1.0.9에서 확인): https://classicrebirth.com/index.php/downloads/resident-evil-2-classic-rebirth/ Ultimate ASI Loader v9.7.4(MIT)는 dsound.dll로 포함되어 있습니다.
RE2 리메이크(2019)용이 아닙니다.
게임 지도에 방 이름, 잠긴 문과 열쇠, 핵심 아이템, 문서·지도, 퍼즐, 일반 아이템, 타자기·아이템 상자, 몬스터를 표시합니다.

설치
1. 게임을 종료합니다.
2. ZIP의 내용을 Resident Evil 2.exe가 있는 게임 폴더에 폴더 구조 그대로 복사합니다.
   (dsound.dll, scripts/RE2.AnnotatedMap.asi, scripts/RE2.AnnotatedMap.ini)
   한글 패치 등으로 Ultimate ASI Loader가 이미 dsound.dll로 설치되어 있으면 dsound.dll은 건너뛰어도 됩니다.
   ASI 로더가 아닌 다른 dsound.dll(예: DSOAL)이 있으면 덮어쓰지 말고, 포함된 dsound.dll을 winmm.dll 이름으로 복사하세요.
3. 게임을 실행하고 지도를 엽니다.
업그레이드할 때는 기존 scripts/RE2.AnnotatedMap.ini를 건너뛰거나 백업 후 복원하세요.

사용 (지도 화면에서만 작동)
- 숫자 키: 0 전체 표시, 1 방 이름·타자기·아이템 상자, 2 잠긴 문·열쇠, 3 핵심 아이템, 4 문서·지도,
  5 퍼즐, 6 이벤트(스포일러 장면, 보라색 ? 마름모), 7 일반 아이템, 8 적, 9 표시 범위(방문한 방 → 공개된 방 → 모든 방).
- \(₩) 키: 한국어 / English (범례 제목 줄의 [H] 옆에 표시).
- H: 표식 이름 3단계(누를 때마다 모두 표시 → 일반 아이템 제외 → 모두 숨김, 기본 숨김; 핵심 아이템·잠긴 문 열쇠·지도·일반 아이템 이름). 일반 아이템 이름은 빈 자리에만 표시합니다. 범례 제목 줄에 상태가 나옵니다.
- 범례와 값 표시: ~ (숫자 1 왼쪽) 키로 켜고 끕니다. 범례·값 표시에 닿는 표식은 그리지 않습니다.
- 이름 크기: - · = (+), 이름 불투명도: [ · ]. 숫자패드 - · +도 지원합니다.
- 아이콘 크기: Shift + - · = (+), 아이콘 불투명도: Shift + [ · ]. INI의 Modifier=Ctrl로 Shift 대신 Ctrl을 씁니다.
- 같은 키를 0.35초 안에 다시 누르면 무시합니다.
- 상태 화면 지도: 좌 · 우 장소 선택, 위 · 아래 층 선택. 이미 방문한 층만 보입니다.
  다른 장소가 있으면 좌우 가장자리에 초록 화살표가 깜빡입니다.
- 지도 2배 확대: 결정 버튼으로 켜고 끕니다. 확대 중에는 방향 입력으로 지도를 옮기며, 지도를 다시 열면 1배로 돌아옵니다.
- 기본값: 영어, 이름 크기 100%, 이름 불투명도 70%, 아이콘 크기 100%, 아이콘 불투명도 80%, 방문한 방만 표시,
  방 이름만 켬(2–7로 다른 항목 켬), 표식 이름 끔.
- 잠금 표식은 문 바로 옆, 열려 있는 쪽 방(잠긴 방이 아님)에 표시합니다(INI의 LockSide=0이면 문 위, 이전 버전 설정 파일은 한 번 1로 바뀜).
- 설정은 scripts/RE2.AnnotatedMap.ini에 저장됩니다.
- [Z]는 A/B 시나리오 사이의 선택·행동과 관련된 재핑 표식이며 아이템 이름의 일부가 아닙니다.
- 랭크 예상치는 INI의 Rank=1로 켭니다(기본 끔, 변경 후 게임 재실행).
- HD/SD: Classic REbirth에 HD 텍스처 팩(bio2hd.asi)이 로드되어 있고 config.ini [DLL]의 RetroMode·LowResEnable이 모두 꺼져 있을 때만 HD이고, 그 밖의 모든 경우(Classic REbirth가 없는 게임 포함)는 SD 방식(1배 픽셀 마커, 픽셀 글꼴 Galmuri9, 방 이름은 한 색으로 방 옆에 선으로 연결)으로 표시합니다. SD에서는 이름·아이콘 크기, 불투명도, 아이템 이름, 랭크를 쓸 수 없습니다. INI의 DisplayMode=Auto/HD/SD로 고정할 수 있습니다(변경 후 재실행).

제거
scripts/RE2.AnnotatedMap.asi와 .ini(.log)를 지웁니다. 다른 ASI 모드가 없으면 dsound.dll도 지웁니다.
EXE와 세이브는 수정하지 않습니다. 지원하지 않는 실행 파일에서는 아무것도 패치하지 않습니다.

제작: 커트씨. 비공식 팬 모드입니다. Capcom과 관련이 없으며 게임 파일을 포함하지 않습니다.
소스 라이선스는 LICENSE.txt(MIT), 참고 자료와 글꼴 출처는 NOTICE.md에 있습니다.
https://github.com/eggu/resident-evil-2-annotated-map

================================================================
English
================================================================

Supported: GOG Resident Evil 2 (Resident Evil 2.exe) + Ultimate ASI Loader (HD mode needs Classic REbirth).
Classic REbirth is installed separately and is needed only for HD mode (tested with 1.0.9): https://classicrebirth.com/index.php/downloads/resident-evil-2-classic-rebirth/ Ultimate ASI Loader v9.7.4 (MIT) is included as dsound.dll.
This is not for the 2019 remake.
Shows room names, locked doors and required keys, key items, documents and maps,
puzzles, common items, typewriters and item boxes, and monsters on the game's map.

Installation
1. Close the game.
2. Copy the ZIP contents into the folder containing Resident Evil 2.exe, preserving
   the directory structure (dsound.dll, scripts/RE2.AnnotatedMap.asi and scripts/RE2.AnnotatedMap.ini).
   If Ultimate ASI Loader is already installed as dsound.dll (e.g. by a translation patch), you can skip dsound.dll.
   If you have a different dsound.dll (e.g. DSOAL), do not overwrite it: copy the included one as winmm.dll.
3. Launch the game and open the map.
When upgrading, skip scripts/RE2.AnnotatedMap.ini or back it up and restore it.

Controls (on the map screen only)
- Number keys: 0 all annotations, 1 room names/typewriters/item boxes, 2 doors/keys,
  3 key items, 4 documents/maps, 5 puzzles, 6 events (story-scene spoilers, purple ? diamond), 7 common items,
  8 enemies, 9 visibility (visited/revealed/all rooms).
- \ key (the won sign on Korean keyboards): Korean/English (shown next to [H] in the legend's title line).
- H: marker names in three states, one per press: all -> all except common items -> all hidden (default hidden; key items, lock keys, maps, document names, some puzzles, common items). Document and common-item names only where there is room. The legend's title line shows the state.
- Legend and values: ~ (left of 1) shows or hides them. Markers touching them are not drawn.
- Name size: - · = (+); name opacity: [ · ]. Numpad - · + is supported.
- Icon size: Shift + - · = (+); icon opacity: Shift + [ · ]. Modifier=Ctrl in the INI uses Ctrl instead of Shift.
- A second press of the same key within 0.35 s is ignored.
- Status-screen map: left · right selects an area, up · down selects a floor. Only visited floors are shown.
  Blinking green arrows at the left/right edges show that another area is available.
- 2x map zoom: the Action button toggles it. While zoomed, directions move the map; reopening the map returns to 1x.
- Defaults: English, name size 100%, name opacity 70%, icon size 100%, icon opacity 80%, visited rooms only,
  only Rooms on (2-7 turn on other categories), marker names off.
- Lock markers sit beside the door on the open side, not in the locked room (LockSide=0 in the INI puts them on the door; settings files from older versions are switched to 1 once).
- Settings are saved in scripts/RE2.AnnotatedMap.ini.
- [Z] marks zapping-related items/interactions affected by choices or actions across scenarios A/B; it is not part of the item name.
- The live rank estimate is enabled with Rank=1 in the INI (off by default; restart after changing).
- HD/SD: HD only with Classic REbirth, the HD texture pack (bio2hd.asi) loaded and RetroMode and LowResEnable in config.ini [DLL] both off; every other case, including a game without Classic REbirth, uses SD mode (1x pixel markers, the Galmuri9 pixel font, room names in one colour beside their room on a leader line). Name/icon size, opacity, item names and rank are not available in SD. DisplayMode=Auto/HD/SD in the INI forces a mode (restart after changing).

Uninstall
Delete scripts/RE2.AnnotatedMap.asi and its .ini/.log. Also delete dsound.dll if no other ASI mod uses it.
The EXE and save files are not modified. Nothing is patched on an unsupported executable.

Created by 커트씨. Unofficial fan mod, unaffiliated with Capcom. No game files are included.
Source license: LICENSE.txt (MIT). References and font credits: NOTICE.md.
https://github.com/eggu/resident-evil-2-annotated-map
