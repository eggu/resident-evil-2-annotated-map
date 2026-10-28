"""Generate bilingual reference tables from the headers used by the mod (stdlib only)."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/wiki'


def records(file, array):
    text = (ROOT / 'src' / file).read_text()
    match = re.search(r'\b' + re.escape(array) + r'\[\s*\]\s*=\s*\{(.*?)\};', text, re.S)
    assert match, (file, array)
    result = []
    for row in re.findall(r'\{([^{}]+)\}', match[1]):
        values = tuple(int(n.strip(), 0) for n in row.split(','))
        result.append(values)
    assert result, array
    return result


def labelled(file):
    text = (ROOT / 'src' / file).read_text()
    return [(tuple(int(n.strip(), 0) for n in row.split(',')), note.strip())
            for row, note in re.findall(r'\{([\d, -]+)\},\s*/\* (.*?) \*/', text)]


items = records('items.h', 'map_items')
item_guards = records('items.h', 'map_item_guards')
doors = records('doors-all.h', 'doors')
interactions = records('overlay_data.h', 'map_interactions')
interaction_guards = records('overlay_data.h', 'interaction_guards')
documents = records('overlay_data.h', 'map_documents')
document_guards = records('overlay_data.h', 'document_guards')
markers = records('overlay_data.h', 'map_markers')
monsters = records('monsters.h', 'map_monsters')
monster_guards = records('monsters.h', 'monster_guards')
rooms = labelled('room_names-en.h')
assert rooms and all(len(row) == 10 for row, _ in rooms)
room_keys = {(r[0], r[1], r[2]): note.split()[0] for r, note in rooms}
room_names = {lang: json.loads((ROOT / f'data/room_names-{lang}.json').read_text()) for lang in ('ko', 'en')}
item_names = {lang: {r[0]: note.split(' ', 1)[1] for r, note in labelled(f'item_labels-{lang}.h')}
              for lang in ('ko', 'en')}
common = {20, 21, 22, 24, 25, 26, 27, 29, 30, 35, 38, 39, 40}
maps = set(range(200, 206))
assert set(item_names['ko']) == set(item_names['en'])
assert len(doors[0]) == 9 and len(items[0]) == 10 and len(monsters[0]) == 10
for rows, guards, start, count in ((items, item_guards, 8, 9), (documents, document_guards, 8, 9),
                                   (interactions, interaction_guards, 6, 7), (monsters, monster_guards, 8, 9)):
    assert all(0 <= r[start] <= r[start] + r[count] <= len(guards) for r in rows)

PAGES = [
    ('01-native-map', '원작 지도와 표시 범위', 'Native map and visibility'),
    ('02-data-pipeline', '데이터 구성', 'Data pipeline'),
    ('03-rooms', '방 목록', 'Rooms'),
    ('04-locks-keys', '잠긴 문과 열쇠', 'Locked doors and keys'),
    ('05-key-items', '핵심 아이템', 'Key items'),
    ('06-puzzles', '퍼즐과 장치', 'Puzzles and devices'),
    ('07-documents-maps', '문서와 지도', 'Documents and maps'),
    ('08-common-items', '일반 아이템', 'Common items'),
    ('09-save-points', '타자기와 아이템 상자', 'Typewriters and item boxes'),
    ('10-sources', '출처와 라이선스', 'Sources and licenses'),
    ('11-monsters', '몬스터', 'Monsters'),
    ('12-rank-settings', '랭크와 설정', 'Rank and settings'),
]


def generate(lang):
    ko = lang == 'ko'
    suffix = '' if ko else '.en'
    name = lambda k: k[1] if ko else k[2]
    mode_names = ['레온', '클레어', '익스트림 배틀 · 레온 데이터', '익스트림 배틀 · 클레어 데이터'] if ko else [
        'Leon', 'Claire', 'Extreme Battle · Leon data', 'Extreme Battle · Claire data']
    def mode(pl):
        assert 0 <= pl < 4, pl
        return mode_names[pl]
    def room(pl, floor, seen):
        key = room_keys.get((pl & 1, floor, seen))
        return f'{room_names[lang].get(key, key)} (`{key}`)' if key else f'`seen={seen}`'
    def item(i):
        return f'{item_names[lang].get(i, "ID " + str(i))} (`{i}`)'
    def conditions(guards, start, count):
        return ' ∧ '.join(f'`{b}:{bit}={v}`' for b, bit, v in guards[start:start+count]) or '—'
    def table(headers, rows):
        heading = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |']
        grouped = len(headers) >= 5 and headers[1] in ('지도 ID', 'Map ID')
        if grouped:
            rows = sorted(rows, key=lambda r: (mode_names.index(r[0]), r[1]))
        lines, previous = ([] if grouped else heading.copy()), None
        for row in rows:
            assert len(row) == len(headers), row
            if grouped and row[:2] != previous:
                lines += ['', f'## {row[0]} · {headers[1]} {row[1]}', ''] + heading
                previous = row[:2]
            lines.append('| ' + ' | '.join(str(c).replace('|', '&#124;') for c in row) + ' |')
        return '\n'.join(lines) + '\n'
    def write(slug, title, body):
        nav = f'[한국어]({slug}.md) | [English]({slug}.en.md) · [Index](README{suffix}.md)'
        (OUT / f'{slug}{suffix}.md').write_text(f'# {title}\n\n{nav}\n\n{body.rstrip()}\n')

    intro = ('원작 Resident Evil 2 (1998) PC판 지도 모드의 기능과 지도 데이터를 정리한 자료입니다. '
             '표에는 게임 진행 내용과 미방문 장소가 포함됩니다. 스포일러를 피하려면 게임에서는 기본 표시 범위인 방문한 방을 사용하세요.' if ko else
             'Reference for the map features and data in the original Resident Evil 2 (1998) PC mod. '
             'Tables reveal progression information and unexplored locations. Use the default Visited scope in game if you prefer to avoid spoilers.')
    body = intro + '\n\n' + table(['문서' if ko else 'Page', '내용' if ko else 'Contents'],
        [(f'[{name(p)}]({p[0]}{suffix}.md)', name(p)) for p in PAGES])
    body += ('\n## 표 읽는 법\n\n' if ko else '\n## Reading the tables\n\n')
    body += ('- 지도 ID는 모드의 0–19번 지도 인덱스입니다. 게임의 층 이름이나 화면 해상도가 아닙니다.\n'
             '- `seen`은 방 방문 플래그 번호이며, 방 코드와 별개입니다. 방 코드가 대응되지 않는 슬롯은 번호 그대로 표시합니다.\n'
             '- 조건 `bank:bit=value`는 해당 플래그의 참/거짓 판정이며, `∧`로 연결한 조건은 모두 만족해야 합니다. 130/131번 bank는 각각 SCD 변수 0x1e/0x1f 비교이며, `130:n=1`은 변수 값이 n과 같음, `130:n=0`은 다름을 뜻합니다.\n'
             '- 같은 위치도 시나리오·아이템·이벤트 조건에 따라 여러 행이 될 수 있습니다. 행 수는 고유 아이템 수나 동시 표시 수가 아닙니다.\n'
             '- 좌표는 소스 데이터의 논리 지도 좌표입니다. 화면 이동·아이콘 중심 보정 전 값이며 PC 출력 픽셀과 다릅니다.\n' if ko else
             '- Map IDs are the mod\'s indices 0–19, not floor names or display resolutions.\n'
             '- `seen` is a room-visit flag index, separate from a room code. Unmapped slots retain their numeric identifier.\n'
             '- Conditions `bank:bit=value` describe flag truth values. All conditions joined by `∧` must pass. Banks 130/131 compare SCD variables 0x1e/0x1f: `130:n=1` means equal to n, and `130:n=0` means unequal.\n'
             '- A location may have multiple scenario, item or event variants. Row counts are not unique item counts or simultaneous marker counts.\n'
             '- Coordinates are logical source-map coordinates before panning and marker-centre offsets, not PC output pixels.\n')
    body += ('\n[설치와 단축키](../../README.md) · [라이선스](../../NOTICE.md)\n' if ko else
             '\n[Installation and controls](../../README.en.md) · [Credits](../../NOTICE.md)\n')
    write('README', 'RE2 지도 모드 위키' if ko else 'RE2 Annotated Map Wiki', body)

    floors = json.loads((ROOT / 'data/room_shapes.json').read_text())['floors']
    areas = [('도시', 'City', [0, 1]), ('경찰서', 'Police station', [4, 3, 2, 5, 6]),
             ('하수도', 'Sewers', [7, 8]), ('공장', 'Factory', [9, 10, 11, 12]),
             ('연구소', 'Laboratory', [13, 14, 15, 16, 17]), ('열차', 'Train', [18, 19])]
    body = ('표시 범위는 `8`로 방문한 방 → 공개된 방 → 모든 방 순서로 바꿉니다. 공개된 방은 층 지도 획득 여부와 방의 시나리오 마스크를 함께 적용합니다. 모든 방은 방 방문 제한을 해제하지만, 이미 주운 아이템이나 완료된 이벤트를 되돌려 표시하지 않습니다.\n\n'
            '상태 화면 지도에서 좌/우는 장소, 위/아래는 층을 바꿉니다. 방문한 층만 선택할 수 있고 끝에서 처음으로 순환하지 않습니다. 범위가 모든 방이어도 방문하지 않은 층이 선택 목록에 추가되지는 않습니다.\n\n' if ko else
            'Press `8` to cycle Visited → Revealed → All. Revealed requires the acquired floor-map flag and the room\'s scenario visibility mask. All removes the room-visit gate; it does not restore collected items or completed events.\n\n'
            'On the status-screen map, left/right selects an area and up/down selects a floor. Only visited floors are selectable, without wraparound. All scope does not add unvisited floors to the selection list.\n\n')
    body += table(['구역' if ko else 'Area', '위→아래 지도 ID' if ko else 'Map IDs, top to bottom'],
                  [(a[0] if ko else a[1], ', '.join(map(str, a[2]))) for a in areas])
    body += '\n' + table(['캐릭터' if ko else 'Character', '지도 ID' if ko else 'Map ID', '리소스' if ko else 'Resource', '방 슬롯' if ko else 'Room slots'],
        [(mode(f['pl']), f['floor'], f['file'], len(f['rooms'])) for f in floors])
    body += ('\n방 이름과 마커는 원작 지도 위에 덧그립니다. 남은 아이템이 있는 방에는 주황색을 더합니다. 이름·연결선의 불투명도는 아이콘·범례·랭크와 별도로 적용됩니다.\n' if ko else
             '\nNames and markers are overlaid on the native map. Rooms with remaining items receive an orange tint. Name/leader opacity is independent of icons, legend and rank.\n')
    body += ('\n## 원작 데이터 참조\n\n주소는 지원 대상 PC 실행 파일 기준입니다. 출력 해상도와 논리 지도 좌표는 별개입니다.\n\n' if ko else
             '\n## Native data reference\n\nAddresses refer to the supported PC executable. Display resolution is separate from logical map coordinates.\n\n')
    body += table(['주소' if ko else 'Address', '내용' if ko else 'Meaning'], [
        ('`0x691f7a`', '현재 표시 지도 ID' if ko else 'Displayed map ID'),
        ('`0x691fb8 / 0x691fba`', '지도 이동 x/y (signed short)' if ko else 'Map pan x/y (signed short)'),
        ('`0x98ec00`', '방문한 층 비트' if ko else 'Visited-floor bits'),
        ('`0x98ec04`', '방 방문 비트' if ko else 'Room-visit bits'),
        ('`0x98ec1c`', '획득한 층 지도 비트' if ko else 'Acquired floor-map bits'),
        ('`0x98ed2c`', '문 해제 비트' if ko else 'Door-unlock bits'),
        ('`0x53eaf8 / 0x53eb98`', '레온/클레어 층 테이블' if ko else 'Leon/Claire floor tables'),
        ('`0x53b218`', 'SCD 플래그 bank 포인터 테이블' if ko else 'SCD flag-bank pointer table'),
    ])
    write(PAGES[0][0], name(PAGES[0]), body)

    pipeline = [
        ('방 이름과 방 모양', 'Room names and shapes', '`data/room_names-*.json`, `data/room_shapes.json`'),
        ('잠긴 문', 'Locked doors', '`src/doors-all.h`'),
        ('아이템과 조건', 'Items and conditions', '`src/items.h`'),
        ('문서·퍼즐·세이브 지점·잔여 아이템', 'Documents, puzzles, save points and remaining pickups', '`src/overlay_data.h`'),
        ('몬스터 출현과 조건', 'Monster spawns and conditions', '`src/monsters.h`'),
        ('한·영 이름과 렌더링 데이터', 'Bilingual labels and rendering data', '`src/room_names-*.h`, `src/room_labels-*.h`, `src/item_labels-*.h`'),
        ('아이콘·방 채움·랭크 글자', 'Icons, room fills and rank glyphs', '`src/atlas.h`, `src/overlay_icons.h`, `src/fill_masks.h`, `src/rank_glyphs.h`'),
    ]
    body = table(['종류' if ko else 'Data', '파일' if ko else 'File'], [(a if ko else b, c) for a, b, c in pipeline])
    body += ('\n실행 중에는 캐릭터·게임 모드·현재 지도·방문 상태·획득/해제 플래그·조건식을 적용해 표시 여부를 결정합니다. A/B 시나리오 차이는 조건과 문 마스크에 반영됩니다.\n\n'
             '빌드는 고정된 헤더를 컴파일합니다. JSON의 이름이나 좌표만 바꿔도 렌더링 헤더가 자동 갱신되지는 않습니다. 이 위키의 표는 `python3 tools/gen_wiki.py`로 해당 헤더에서 다시 생성합니다. 게임 파일은 필요하지 않습니다.\n\n'
             '[빌드 안내](../DEVELOPMENT.md)\n' if ko else
             '\nAt runtime, character, game mode, current map, visit state, collection/unlock flags and guard conditions determine visibility. Scenario A/B differences are encoded in guards and door masks.\n\n'
             'Builds compile pinned headers. Editing JSON names or coordinates alone does not regenerate the rendered headers. Regenerate these wiki tables from the headers with `python3 tools/gen_wiki.py`; no game files are needed.\n\n'
             '[Build documentation](../DEVELOPMENT.md)\n')
    write(PAGES[1][0], name(PAGES[1]), body)

    body = table(['캐릭터' if ko else 'Character', '지도 ID' if ko else 'Map ID', '방 코드' if ko else 'Room code', '한국어', 'English', 'seen', 'x,y'],
                 [(mode(r[0]), r[1], f'`{note.split()[0]}`', room_names['ko'].get(note.split()[0], '—'),
                   room_names['en'].get(note.split()[0], '—'), r[2], f'{r[3]},{r[4]}') for r, note in rooms])
    write(PAGES[2][0], name(PAGES[2]), body)

    body = ('열쇠 아이콘은 아직 잠겨 있고 현재 시나리오에서 유효한 문에 표시합니다. `bank=255`는 원작 문 해제 비트 배열을 뜻합니다. 그 외 값은 공통 플래그 bank를 사용합니다. 시나리오 마스크 64는 A 및 클레어 B에서 제외, 128은 B에서 제외됩니다. 하강 열쇠(93)는 A 전용, 상승 열쇠(94)·동력실 열쇠(95)·마스터 키(98)·플랫폼 열쇠(99)는 B 전용으로 거릅니다.\n\n' if ko else
            'Key icons mark doors that remain locked and are valid for the current scenario. `bank=255` selects the native door-unlock bit array; other values use the shared flag banks. Scenario mask 64 excludes A and Claire B; mask 128 excludes B. Down Key (93) is A-only; Up Key (94), Power Room Key (95), Master Key (98) and Platform Key (99) are B-only.\n\n')
    body += table(['모드' if ko else 'Mode', '지도 ID' if ko else 'Map ID', '방/슬롯' if ko else 'Room/slot', '열쇠' if ko else 'Key', 'x,y', '해제 bank:bit' if ko else 'Unlock bank:bit', 'Mask'],
        [(mode(p), f, room(p, f, seen), item(k), f'{x},{y}', f'`{b}:{u}`', mask) for p, f, x, y, seen, u, k, mask, b in doors])
    write(PAGES[3][0], name(PAGES[3]), body)

    def item_table(rows):
        return table(['모드' if ko else 'Mode', '지도 ID' if ko else 'Map ID', '방/슬롯' if ko else 'Room/slot', '아이템' if ko else 'Item', 'x,y', '획득 bank:bit' if ko else 'Pickup bank:bit', '표시 조건' if ko else 'Conditions'],
                     [(mode(p), f, room(p, f, seen), item(i), f'{x},{y}', f'`{b}:{bit}`', conditions(item_guards, start, count))
                      for p, f, x, y, seen, i, b, bit, start, count in rows])
    body = ('핵심 아이템은 청록색 별과 이름으로 표시하며 획득 플래그가 켜지면 숨깁니다. `[Z]`는 시나리오 사이에 영향을 주고받는 재핑 항목의 표식으로, 아이템 이름의 일부가 아닙니다. 무기·필름·진행 아이템 등 일반 소모품으로 분류하지 않는 표시 항목을 포함합니다. 퍼즐과 같은 위치에서는 별·마름모 결합 마커를 사용합니다.\n\n' if ko else
            'Key items use a cyan star and name and disappear when their collection flag is set. `[Z]` identifies zapping-related entries affected across scenarios; it is not part of the item name. This category includes weapons, films and progression items outside the common-consumable group. At a shared puzzle location, a combined star/diamond marker is used.\n\n')
    body += item_table([r for r in items if r[5] not in common | maps and r[5] in item_names[lang]])
    write(PAGES[4][0], name(PAGES[4]), body)

    body = ('주황색 마름모는 `kind=6`인 퍼즐·장치 상호작용입니다. 경찰서 1층 동쪽 사무실 금고는 열기 전까지 표시합니다. 조건이 더 이상 맞지 않으면 사라집니다. 퍼즐 이름을 임의로 붙이지 않고 방/슬롯·위치·조건을 나열합니다.\n\n' if ko else
            'Amber diamonds represent puzzle/device interactions with `kind=6`. The East Office safe on Police Station 1F remains marked until unlocked. They disappear when their conditions no longer pass. The table identifies room/slot, position and conditions without inventing puzzle names.\n\n')
    body += table(['모드' if ko else 'Mode', '지도 ID' if ko else 'Map ID', '방/슬롯' if ko else 'Room/slot', 'x,y', '표시 조건' if ko else 'Conditions'],
        [(mode(p), f, room(p, f, seen), f'{x},{y}', conditions(interaction_guards, start, count))
         for p, f, seen, kind, x, y, start, count in interactions if kind == 6])
    write(PAGES[5][0], name(PAGES[5]), body)

    body = ('문서는 문서 아이콘, 층 지도는 접힌 지도 아이콘으로 표시합니다. 200–205는 모드 내부의 지도 ID이며 인벤토리에 쓰는 아이템 번호가 아닙니다. 문서 제목 데이터가 없는 행은 ID로 표시합니다.\n\n' if ko else
            'Documents use a file icon and floor maps use a folded-map icon. IDs 200–205 are synthetic overlay map identifiers, not item IDs written to inventory. Documents without title data retain their numeric ID.\n\n')
    body += table(['모드' if ko else 'Mode', '지도 ID' if ko else 'Map ID', '방/슬롯' if ko else 'Room/slot', 'ID', 'x,y', '획득 bank:bit' if ko else 'Pickup bank:bit', '표시 조건' if ko else 'Conditions'],
        [(mode(p), f, room(p, f, seen), i, f'{x},{y}', f'`{b}:{bit}`', conditions(document_guards, start, count))
         for p, f, seen, b, i, x, y, bit, start, count in documents])
    body += '\n' + item_table([r for r in items if r[5] in maps])
    write(PAGES[6][0], name(PAGES[6]), body)

    body = ('탄약·회복·잉크 리본은 `6`으로 표시합니다. 같은 자리에 놓이는 시나리오/모드별 변형은 각각의 조건으로 구분합니다. 주황색 방 채움은 개별 아이콘 표시 스위치와 별도로 남은 획득 항목을 기준으로 합니다.\n\n' if ko else
            'Toggle ammunition, recovery items and Ink Ribbons with `6`. Scenario/mode variants at one position retain separate conditions. Orange room tint follows remaining pickup records independently of individual icon-category toggles.\n\n')
    body += item_table([r for r in items if r[5] in common])
    write(PAGES[7][0], name(PAGES[7]), body)

    body = ('타자기와 아이템 상자는 방 이름과 함께 `1`로 표시합니다. 방의 표시 범위를 따르며, 소모품처럼 획득 플래그로 지우지 않습니다.\n\n' if ko else
            'Typewriters and item boxes share the room-name toggle `1`. They follow room visibility and do not use consumable pickup flags.\n\n')
    body += table(['모드' if ko else 'Mode', '지도 ID' if ko else 'Map ID', '방/슬롯' if ko else 'Room/slot', '종류' if ko else 'Type', 'x,y'],
        [(mode(p), f, room(p, f, seen), ('타자기' if ko else 'Typewriter') if kind == 9 else ('아이템 상자' if ko else 'Item box'), f'{x},{y}')
         for p, f, seen, kind, x, y in markers])
    write(PAGES[8][0], name(PAGES[8]), body)

    body = ('게임 데이터는 원작 PC판의 방·지도·스크립트·플래그에 기반합니다. 게임 실행 파일이나 원본 방 스크립트는 배포하지 않습니다. 외부 자료는 이름·진행 동선·그림 참고용이며 원문이나 이미지를 재배포하지 않습니다.\n\n' if ko else
            'Map data derives from the original PC game\'s rooms, maps, scripts and flags. Game executables and original room scripts are not distributed. External references inform naming, progression and visual references; their text and images are not redistributed.\n\n')
    sources = [('[Classic REbirth](https://classicrebirth.com/)', '필수 호환 패치' if ko else 'Required compatibility patch'),
               ('[CoreGamers](https://coregamers.com/walkthrough/resident-evil-2-8)', '방 이름 참고' if ko else 'Room-name reference'),
               ('[Brandon W. Dennis FAQ](https://gamefaqs.gamespot.com/ps/198458-resident-evil-2/faqs/4110)', '레온 B 열차 진행 참고' if ko else 'Leon B transport progression reference'),
               ('[Evil Resource](https://www.evilresource.com)', '몬스터 그림 참고' if ko else 'Monster visual reference'),
               ('[Pretendard](https://github.com/orioncactus/pretendard)', '한국어·영어 글꼴 (SIL OFL 1.1)' if ko else 'Korean/English font (SIL OFL 1.1)'),
               ('[Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader)', '포함된 ASI 로더 (MIT)' if ko else 'Bundled ASI loader (MIT)')]
    body += table(['자료' if ko else 'Source', '용도' if ko else 'Use'], sources)
    body += ('\n소스 코드: [MIT](../../LICENSE). 게임 및 제3자 자료의 권리는 각 권리자에게 있습니다. 전체 표기: [NOTICE](../../NOTICE.md).\n' if ko else
             '\nSource code: [MIT](../../LICENSE). Game and third-party material retain their respective rights. Full credits: [NOTICE](../../NOTICE.md).\n')
    write(PAGES[9][0], name(PAGES[9]), body)

    body = ('몬스터는 `7`로 켜며 기본값은 끔입니다. 처음부터 죽은 시체, 강제 연출·동결 개체, 방 모양 밖의 스폰은 제외합니다. 다시 일어날 수 있는 잠복 개체는 표시 대상입니다. 원래 출현 지점을 표시하므로 실시간 적 위치 추적 지도가 아닙니다. 출현 조건·방 표시 범위·사망 비트를 적용합니다. `gid=255`인 행은 개별 사망 비트로 숨기지 않습니다. 보너스 모드에서는 사망 bank 선택 규칙이 달라집니다.\n\n' if ko else
            'Monster markers are toggled with `7` and start off. Initial corpses, forced-animation/frozen actors and spawns outside their room shapes are excluded. Dormant enemies that can wake remain eligible. Markers show spawn positions, not real-time enemy tracking. Spawn conditions, room visibility and death flags apply. Rows with `gid=255` have no individual death-bit suppression. Bonus modes use different death-bank selection rules.\n\n')
    cats = dict((int(i)-50, n) for i, n in re.findall(r'\{(5[0-6]),\d+,\d+\}, /\* monster-([^ ]+) \*/', (ROOT/'src/overlay_icons.h').read_text()))
    assert set(cats) == set(range(7))
    categories = ['좀비', '개', '리커', '비행형', '식물형', '곤충형', '보스'] if ko else [cats[i].capitalize() for i in range(7)]
    body += table(['모드' if ko else 'Mode', '지도 ID' if ko else 'Map ID', '방/슬롯' if ko else 'Room/slot', '종류' if ko else 'Category', 'x,y', '사망 bank:gid' if ko else 'Death bank:gid', '표시 조건' if ko else 'Conditions'],
        [(mode(p), f, room(p, f, seen), categories[cat], f'{x},{y}', f'`{b}:{gid}`', conditions(monster_guards, start, count))
         for p, f, x, y, seen, cat, b, gid, start, count in monsters])
    write(PAGES[10][0], name(PAGES[10]), body)

    body = ('랭크 예상치는 `[MapOverlay]`의 `Rank=1`로 켭니다. 저장 후 게임을 다시 실행하세요. 시간·저장 횟수·응급 스프레이 사용·무한 무기 플래그에 따라 계속 바뀌며 최종 결과를 보장하는 값은 아닙니다. 쉬움·보너스 모드에서는 표시하지 않습니다.\n\n'
            '점수 = 시간 점수 + 저장 점수 + 스프레이 점수 − 무한 무기 감점(최저 0).\n\n'
            '- 시간: 2시간 30분까지 100점, 이후 시작한 1시간마다 10점 감소, 최저 0점.\n'
            '- 저장: 0–19회는 `100−5×횟수`, 20회부터 0점. 새 게임의 미설정 값은 0회로 취급합니다.\n'
            '- 스프레이: 0–5회는 `100−15×횟수`, 6회부터 0점.\n'
            '- 무한 무기 플래그가 설정되면 50점 감점합니다.\n\n' if ko else
            'Enable the rank estimate with `Rank=1` under `[MapOverlay]` and restart the game. It changes with elapsed time, saves, First Aid Spray use and the infinite-weapon flag; it is not a guaranteed final result. It is hidden in Easy and bonus modes.\n\n'
            'Score = time points + save points + spray points − infinite-weapon penalty, clamped at zero.\n\n'
            '- Time: 100 through 2h30m, then minus 10 per started additional hour, minimum zero.\n'
            '- Saves: `100−5×count` for 0–19; zero from 20. The new-game sentinel counts as zero saves.\n'
            '- Sprays: `100−15×count` for 0–5; zero from 6.\n'
            '- Subtract 50 when the infinite-weapon flag is set.\n\n')
    body += table(['랭크' if ko else 'Rank', '점수' if ko else 'Score'], [('A', '269–300'), ('B', '199–268'), ('C', '144–198'), ('D', '99–143'), ('E', '0–98')])
    body += ('\n## 설정\n\n설정 파일은 `scripts/RE2.AnnotatedMap.ini`입니다. 게임 안에서 바꾼 값은 자동 저장됩니다. 이름 크기는 50–150%, 불투명도는 10–100%이며 10%씩 조절합니다. 확대하면 좁은 지도에서 이름이 겹칠 수 있습니다.\n\n[전체 기본값과 단축키](../../README.md)\n' if ko else
             '\n## Settings\n\nSettings are stored in `scripts/RE2.AnnotatedMap.ini`. In-game changes are saved automatically. Name size ranges from 50–150% and opacity from 10–100%, in 10% steps. Enlarged names may overlap on crowded maps.\n\n[All defaults and controls](../../README.en.md)\n')
    write(PAGES[11][0], name(PAGES[11]), body)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    for language in ('ko', 'en'):
        generate(language)
    pages = list(OUT.glob('*.md'))
    assert len(pages) == 2 * (len(PAGES) + 1)
    for page in pages:
        text = page.read_text()
        for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', text):
            if not link.startswith(('https://', 'http://')):
                assert (page.parent / link).is_file(), (page, link)
    print(f'Generated {len(pages)} bilingual wiki pages; source references and links checked.')
