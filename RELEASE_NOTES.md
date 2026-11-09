# RE2 Annotated Map - Survivor's Notes 1.2.0

## English

- Key items now have their own icons instead of the generic cyan star: weapons, weapon parts, medals, stones, plugs, films, cards, the Lighter, Valve Handle, Cog, fuses, the Vaccine Cartridge and more.
- New `H` key: marker names in three states, one per press (all names, all except common items, hidden). Names cover key items, lock keys, maps, documents, puzzles and common items, and are coloured like their legend row. Document names are the titles of the game's Files list; puzzle names are the device or structure. Document and common-item names appear only where there is room. Marker names are off by default.
- New events category (key `6`, spoilers): a purple `?` diamond marks where a story scene starts and disappears once the scene has played. It includes the self-destruct countdown on the Train Platform.
- Icon size (`Shift` + `-` / `+`, 50-200%) and icon opacity (`Shift` + `[` / `]`, default 80%) can be changed in game. Name opacity moved to `[` / `]`; name size stays on `-` / `+`. `Modifier=Ctrl` in the INI uses `Ctrl` instead of `Shift`.
- Number keys now follow the legend: 5 puzzles, 6 events, 7 common items, 8 enemies, 9 visibility. Language moved to the `\` key (the won sign on Korean keyboards).
- The legend is titled `Map Notes` and lists each key in brackets (for example `[H]`, `[~]`). Sizes and opacities are shown at the upper left of the map; `~` hides them together with the legend.
- Names and icons grow to about 1.43x at 2x map zoom. Name size 100% is now the former 80% size; your saved name size is converted once so it looks the same, and the range is 50-200%.
- Room names are placed from the innermost point of each room, are drawn under all icons, and wrap onto two lines when much wider than their room. Many room names have moved. Key-item names of eight or more characters wrap onto two lines. Markers that touch the legend or the values are not drawn.
- Korean item names now use the game's own names from the Korean HD patch (for example "초록 허브").
- New INI option `LockSide=1` shows lock markers in the room you have not entered yet instead of on the door (default: on the door).
- A second press of the same key within 0.35 seconds is ignored. Settings are saved through a temporary file, so a failed save keeps your previous settings.
- Upgrading: keep your `scripts/RE2.AnnotatedMap.ini` and replace only `scripts/RE2.AnnotatedMap.asi` (or copy the whole ZIP over the game folder and keep your INI). On first start the new settings are added to your INI and your existing values are kept.

## 한국어

- 핵심 아이템에 청록색 별 대신 아이템별 아이콘을 표시합니다. 무기, 무기 부품, 메달, 석판, 플러그, 필름, 카드, 라이터, 밸브 핸들, 톱니바퀴, 퓨즈, 백신 카트리지 등입니다.
- 새 키 `H`: 표식 이름을 누를 때마다 모두 표시, 일반 아이템 제외, 숨김 순서로 바꿉니다. 핵심 아이템, 잠긴 문 열쇠, 지도, 문서, 퍼즐, 일반 아이템의 이름이 나오며 범례 줄과 같은 색으로 그려집니다. 문서 이름은 게임의 파일 목록에 나오는 제목이고, 퍼즐 이름은 장치·구조물 이름입니다. 문서와 일반 아이템 이름은 빈 자리에만 표시합니다. 표식 이름은 기본으로 꺼져 있습니다.
- 이벤트 분류를 추가했습니다(키 `6`, 스포일러). 이야기 장면이 시작되는 자리에 보라색 `?` 마름모를 표시하고 장면이 지나가면 지웁니다. 열차 승강장의 자폭 카운트다운도 포함합니다.
- 게임 안에서 아이콘 크기(`Shift` + `-` / `+`, 50~200%)와 아이콘 불투명도(`Shift` + `[` / `]`, 기본 80%)를 바꿀 수 있습니다. 이름 불투명도는 `[` / `]`로 옮겼고 이름 크기는 그대로 `-` / `+`입니다. INI의 `Modifier=Ctrl`로 `Shift` 대신 `Ctrl`을 쓸 수 있습니다.
- 숫자 키가 범례 번호에 맞게 바뀌었습니다: 5 퍼즐, 6 이벤트, 7 일반 아이템, 8 적, 9 표시 범위. 언어 전환은 `\`(한국어 키보드의 ₩) 키로 옮겼습니다.
- 범례 제목이 `지도 메모`(영어 `Map Notes`)로 바뀌고 키를 `[H]`, `[~]`처럼 괄호로 표시합니다. 크기·불투명도 값은 지도 왼쪽 위에 표시되며 `~`로 범례와 함께 숨깁니다.
- 지도를 2배 확대하면 이름과 아이콘이 약 1.43배로 커집니다. 이름 크기 100%는 이전 버전의 80% 크기이며, 저장된 이름 크기는 처음 한 번 자동으로 바꿔 같은 크기로 보이게 합니다. 범위는 50~200%입니다.
- 방 이름을 방의 가장 안쪽 지점 기준으로 놓고 모든 아이콘 아래에 그리며, 방보다 많이 넓은 이름은 두 줄로 나눕니다. 많은 방 이름의 위치가 달라졌습니다. 8자 이상인 핵심 아이템 이름도 두 줄로 나눕니다. 범례나 값 표시에 닿는 표식은 그리지 않습니다.
- 한국어 아이템 이름이 한국어 HD 패치의 게임 자체 이름을 씁니다(예: "초록 허브").
- INI에 `LockSide=1`을 추가하면 잠금 표식을 문 위가 아니라 아직 들어가지 않은 쪽 방에 표시합니다(기본은 문 위).
- 같은 키를 0.35초 안에 다시 누르면 무시합니다. 설정은 임시 파일에 쓴 뒤 교체해 저장하므로 저장에 실패해도 이전 설정이 남습니다.
- 업그레이드: 기존 `scripts/RE2.AnnotatedMap.ini`는 그대로 두고 `scripts/RE2.AnnotatedMap.asi`만 바꾸면 됩니다(ZIP 전체를 게임 폴더에 덮어쓸 때도 INI는 유지하세요). 처음 실행할 때 새 설정이 INI에 추가되고 기존 값은 유지됩니다.
