RE2 Annotated Map - Survivor's Notes - Resident Evil 2 (1998)
상세 지도: 생존자의 메모

지원: GOG판 Resident Evil 2(Resident Evil 2.exe) + Classic REbirth + Ultimate ASI Loader.
Classic REbirth는 별도로 설치해야 합니다(1.0.9에서 확인). Ultimate ASI Loader v9.7.4(MIT)는 dsound.dll로 포함되어 있습니다.
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
  5 퍼즐, 6 일반 아이템, 7 몬스터, 8 표시 범위(방문한 방 → 공개된 방 → 모든 방), 9 한국어 / English.
- 이름 크기: - / = (+), 불투명도: Shift + 위 키. 숫자패드 -/+도 지원합니다.
- 상태 화면 지도: 좌/우 장소 선택, 위/아래 층 선택. 이미 방문한 층만 보입니다.
  다른 장소가 있으면 좌우 가장자리에 초록 화살표가 깜빡입니다.
- 기본값: 영어, 이름 100%, 불투명도 70%, 몬스터 끔, 나머지 켬, 방문한 방만 표시.
- 설정은 scripts/RE2.AnnotatedMap.ini에 저장됩니다.
- 랭크 예상치는 INI의 Rank=1로 켭니다(기본 끔, 변경 후 게임 재실행).

제거
scripts/RE2.AnnotatedMap.asi와 .ini(.log)를 지웁니다. 다른 ASI 모드가 없으면 dsound.dll도 지웁니다.
EXE와 세이브는 수정하지 않습니다. 지원하지 않는 실행 파일에서는 아무것도 패치하지 않습니다.

비공식 팬 모드입니다. Capcom과 관련이 없으며 게임 파일을 포함하지 않습니다.
https://github.com/eggu/resident-evil-2-annotated-map

================================================================
English
================================================================

Supported: GOG Resident Evil 2 (Resident Evil 2.exe) + Classic REbirth + Ultimate ASI Loader.
Classic REbirth must be installed separately (tested with 1.0.9). Ultimate ASI Loader v9.7.4 (MIT) is included as dsound.dll.
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
  3 key items, 4 documents/maps, 5 puzzles, 6 common items, 7 monsters,
  8 visibility (visited/revealed/all rooms), 9 Korean/English.
- Name size: - / = (+); opacity: Shift + those keys. Numpad -/+ is supported.
- Status-screen map: left/right selects an area, up/down selects a floor. Only visited floors are shown.
  Blinking green arrows at the left/right edges show that another area is available.
- Defaults: English, size 100%, opacity 70%, monsters off, everything else on, visited rooms only.
- Settings are saved in scripts/RE2.AnnotatedMap.ini.
- The live rank estimate is enabled with Rank=1 in the INI (off by default; restart after changing).

Uninstall
Delete scripts/RE2.AnnotatedMap.asi and its .ini/.log. Also delete dsound.dll if no other ASI mod uses it.
The EXE and save files are not modified. Nothing is patched on an unsupported executable.

Unofficial fan mod, unaffiliated with Capcom. No game files are included.
https://github.com/eggu/resident-evil-2-annotated-map
