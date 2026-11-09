# Key item icon brief (RE2)

Brief for the 37 key-item icons that replaced the cyan star placeholder. Style, appearance, readability, method and review
rules are in the shared guide and are not repeated here:
the shared icon style guide (RE2 row: style "C", up to 32x32 RGBA, binary alpha,
16 colours or fewer, 1 px dark outline, tight crop).

16 other key items reuse the lock/key sprites already in `assets/icons/` (item ids 31, 52, 62, 63, 75, 88, 89, 90, 91, 92,
93, 94, 95, 97, 98, 99). The icon is drawn about 6 map pixels wide, roughly 30 screen pixels at 1600x1200.

## RE2 specifics

- Output: one `key-<id>.png` per item in a work folder; the coordinator copies approved files into `assets/icons/` and
  `assets/generate_key_art.py` repacks them into the atlas page (`assets/key_art.h`, `src/key_art.h`).
- References: the game's inventory icon cell of each item (`Common/Data/itemall.bin`, 40x30 texels) extracted to
  `local/key-icon-refs/<id>.png` (git-ignored; never committed or packaged).
- Deliver `key-icons-preview.png` (reference | new icon | previous icon at 4x) and `provenance.json` as the guide describes;
  provenance of the shipped set is in `assets/key-art-provenance.json`.
- Traps seen in earlier rounds: weapons and weapon parts have their own look (no generic gun); 15 Sub Machine Gun and 16
  Flamethrower are thin strips (about 31x12 texels), so draw them thin; 69, 70 and 80 are the same film canister pair, so keep
  them related and give B, C and D a different small mark; 84 and 85 are the same joint plug in blue and red; 50 is a red valve
  wheel; 47 shows the Lighter with its lid open; 71-73 are round coins with the animal in relief; 56 and 57 are the left and
  right Jaguar stones; 59 and 60 are chess-piece plugs.

## Items

| id | English | Korean | file |
|---|---|---|---|
| 5 | Magnum | 매그넘 | `key-5.png` |
| 7 | Shotgun | 샷건 | `key-7.png` |
| 9 | GrenadeLauncher | 유탄 발사기 | `key-9.png` |
| 12 | Bowgun | 보우건 | `key-12.png` |
| 15 | SubMachineGun | [Z] 기관단총 | `key-15.png` |
| 16 | Flamethrower | 화염 방사기 | `key-16.png` |
| 17 | RocketLauncher | 로켓 런처 | `key-17.png` |
| 32 | HandgunParts | 권총 부품 | `key-32.png` |
| 33 | MagnumParts | 매그넘 부품 | `key-33.png` |
| 34 | ShotgunParts | 샷건 부품 | `key-34.png` |
| 36 | AntiVirusBomb | 항바이러스 폭탄 | `key-36.png` |
| 47 | Lighter | 라이터 | `key-47.png` |
| 50 | ValveHandle | 밸브 핸들 | `key-50.png` |
| 51 | RedJewel | 붉은 보석 | `key-51.png` |
| 53 | BlueCard | 파란 카드 | `key-53.png` |
| 54 | SerpentStone | 뱀 석판 | `key-54.png` |
| 56 | JaguarStoneL | 석판 왼쪽 | `key-56.png` |
| 57 | JaguarStoneR | 석판 오른쪽 | `key-57.png` |
| 58 | EagleStone | 독수리 석판 | `key-58.png` |
| 59 | BishopPlug | 비숍 플러그 | `key-59.png` |
| 60 | RookPlug | 룩 플러그 | `key-60.png` |
| 64 | Detonator | 신관 | `key-64.png` |
| 67 | Crank | 크랭크 | `key-67.png` |
| 69 | FilmB | 필름 B | `key-69.png` |
| 70 | FilmC | 필름 C | `key-70.png` |
| 71 | UnicornMedal | 유니콘 메달 | `key-71.png` |
| 72 | EagleMedal | 독수리 메달 | `key-72.png` |
| 73 | WolfMedal | 늑대 메달 | `key-73.png` |
| 74 | Cog | 톱니바퀴 | `key-74.png` |
| 76 | MainFuse | 메인 퓨즈 | `key-76.png` |
| 77 | FuseCase | 퓨즈 케이스 | `key-77.png` |
| 79 | VaccineCart | 백신 카트리지 | `key-79.png` |
| 80 | FilmD | 필름 D | `key-80.png` |
| 84 | JointPlugBlue | 파란 조인트 | `key-84.png` |
| 85 | JointPlugRed | 빨간 조인트 | `key-85.png` |
| 86 | Cord | 전선 | `key-86.png` |
| 96 | MODisk | MO 디스크 | `key-96.png` |
