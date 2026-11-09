"""Generate installed-game room labels; requires Pillow and Unicorn like existing tooling."""
from pathlib import Path
import hashlib, json, os, re, struct
from PIL import Image, ImageDraw, ImageFont
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX
import category_colors

R = Path(__file__).resolve().parent
G = Path(os.environ['RE2_GAME'])
SOURCE = 'https://coregamers.com/walkthrough/resident-evil-2-8'
EXE_SHA = '21b2a647cbeddac1ec389be847f22a434a0264a18020589de91cb2824dcb1bf5'
FONT = Path(__file__).resolve().parent / 'fonts/Pretendard-SemiBold.otf'  # open font only (release rule 2026-10-26)
FONT_KO = FONT
FONT_EN = Path(__file__).resolve().parent / 'fonts/Pretendard-Medium.otf'
FONT_PX, STROKE, LABEL_SCALE = 24, 3, 4  # user: room names smaller (was 18px at 1/2)
HELP_FONT = Path(__file__).resolve().parent / 'fonts/Pretendard-Medium.otf'
HELP_FONT_PX, HELP_TITLE_PX, HELP_STROKE = 20, 22, 3
LANGUAGE = 'Korean'
ROOM_NAMES_FILE = 'room_names-ko.json'
# Text-only legend: ON rows use category colours; OFF rows are grey.
HELP_TEXT = {
    'Korean': ('지도 메모', '[0] 전체 켜짐', '[0] 전체 꺼짐', '[1] 방 이름 켜짐', '[1] 방 이름 꺼짐',
               '[2] 잠긴 문 켜짐', '[2] 잠긴 문 꺼짐', '[3] 핵심 아이템 켜짐', '[3] 핵심 아이템 꺼짐',
               '[4] 문서·지도 켜짐', '[4] 문서·지도 꺼짐', '[5] 퍼즐 켜짐', '[5] 퍼즐 꺼짐',
               '[\\] 언어: 한국어', '[\\] 언어: 영어', '[8] 적 켜짐', '[8] 적 꺼짐',
               '[7] 일반 아이템 켜짐', '[7] 일반 아이템 꺼짐',
               '[9] 방문 방', '[9] 공개 방', '[9] 전체 방'),
    'English': ('Map Notes', '[0] ALL: ON', '[0] ALL: OFF', '[1] ROOMS: ON', '[1] ROOMS: OFF',
                '[2] LOCKS: ON', '[2] LOCKS: OFF', '[3] KEY ITEMS: ON', '[3] KEY ITEMS: OFF',
                '[4] FILES & MAPS: ON', '[4] FILES & MAPS: OFF', '[5] PUZZLES: ON', '[5] PUZZLES: OFF',
                '[\\] LANGUAGE: KOREAN', '[\\] LANGUAGE: ENGLISH', '[8] ENEMIES: ON', '[8] ENEMIES: OFF',
                '[7] ITEMS: ON', '[7] ITEMS: OFF',
                '[9] VISITED', '[9] REVEALED', '[9] ALL ROOMS'),
}
# Title and [9] rows as in the RE0 HD map mod ('지도 메모' / 'Map Notes'; user 2026-11-07: same title in every map mod).
# Hint format of the RE0 HD map mod (candidate 49): a lone key in brackets ([~], [H], [결정]), '·' between alternatives,
# '+' for combinations. ids 22/23 zoom, 24 folded legend, 25 hide, 26/27 marker names on/off; 28.. the readout panel
# (re2_keymap.c readout_layout): two name hints, the Shift/Ctrl prefixes, two icon hints, then the values 10%..200%.
HELP_TEXT['Korean'] += ('[결정] 확대: 1배', '[결정] 확대: 2배', '[~] 범례', '[~] 숨김', '[H] 아이템 이름: 모두', '[H] 아이템 이름: 끔',
                        '[ · ] 이름 불투명도:', '- · + 이름 크기:', 'Shift +', 'Ctrl +', '[ · ] 아이콘 불투명도:', '- · + 아이콘 크기:')
HELP_TEXT['English'] += ('[Action] Zoom: 1x', '[Action] Zoom: 2x', '[~] Legend', '[~] Hide', '[H] NAMES: ALL', '[H] NAMES: OFF',
                         '[ · ] Name opacity:', '- · + Name size:', 'Shift +', 'Ctrl +', '[ · ] Icon opacity:', '- · + Icon size:')
for language in HELP_TEXT:
    HELP_TEXT[language] += tuple(f'{percent}%' for percent in range(10, 201, 10))
# The third [H] state (ItemNames=2) is appended so no earlier id moves: id 26 ALL, 27 OFF, 54 NO COMMON (re2_keymap.c HELP_ITEM_NAMES_NO_COMMON).
# Language row (ids 13/14) is '[\\]' since the number keys were renumbered (user 2026-11-08); it sits in the header next to [H].
HELP_TEXT['Korean'] += ('[H] 아이템 이름: 일반 제외',)
HELP_TEXT['English'] += ('[H] NAMES: NO COMMON',)
# Events (user 2026-11-08, legend renumbering): [6] ON/OFF appended as ids 55/56 so no earlier id moves.
HELP_TEXT['Korean'] += ('[6] 이벤트 켜짐', '[6] 이벤트 꺼짐')
HELP_TEXT['English'] += ('[6] EVENTS: ON', '[6] EVENTS: OFF')
HELP_SLOT = 6  # map pixels per marker slot (5 px marker + 1 px gap)
_WHITE, _OFF = (255, 255, 255), category_colors.OFF
# RE3 build_assets.py CATEGORY_COLOR/PALETTE, in HELP_TEXT order; marker sprites stay unchanged.
HELP_RGB = (_WHITE, _WHITE, _OFF, category_colors.ROOMS, _OFF, category_colors.NAME_RGB[category_colors.LOCK], _OFF,
            category_colors.NAME_RGB[category_colors.KEY], _OFF, category_colors.NAME_RGB[category_colors.DOCUMENT], _OFF,
            category_colors.NAME_RGB[category_colors.PUZZLE], _OFF, _WHITE, _WHITE, category_colors.MONSTERS, _OFF,
            category_colors.NAME_RGB[category_colors.COMMON], _OFF,
            _WHITE, _WHITE, _WHITE) + (_WHITE,) * 5 + (_OFF,) + (_WHITE,) * 27 + (category_colors.NAME_RGB[category_colors.EVENT], _OFF)
# Native rects reachable from several RDTs: (floor, index) -> room code whose name labels it.
# Floor 19 train map index 1 is the same rect as room 704's floor-18 train car, reached from 700/701/702/704.
SHARED_RECT = {(19, 1): '704'}


def native_rows():
    blob = (G / 'Resident Evil 2.exe').read_bytes()
    assert hashlib.sha256(blob).hexdigest() == EXE_SHA, 'Regenerate native address analysis for a different executable'
    pe = struct.unpack_from('<I', blob, 60)[0]
    sections = []
    u = Uc(UC_ARCH_X86, UC_MODE_32)
    u.mem_map(0x400000, 0x1000000)
    u.mem_map(0x20000000, 0x10000)
    for i in range(struct.unpack_from('<H', blob, pe + 6)[0]):
        o = pe + 24 + struct.unpack_from('<H', blob, pe + 20)[0] + i * 40
        _, rv, size, raw = struct.unpack_from('<IIII', blob, o + 8)
        sections.append((rv, size, raw))
        u.mem_write(0x400000 + rv, blob[raw:raw + size])
    def call(fn, a, b):
        u.mem_write(0x20008000, struct.pack('<III', 0x20000100, a, b))
        u.reg_write(UC_X86_REG_ESP, 0x20008000)
        u.emu_start(fn, 0x20000100, count=2000)
        return u.reg_read(UC_X86_REG_EAX)
    rows, gaps, hashes = {}, [], {}
    names = json.loads((R / ROOM_NAMES_FILE).read_text())
    for pl in (0, 1):
        for p in sorted((G / f'Pl{pl}/Rdt').glob('*.RDT')):
            code = p.stem[4:7]
            # shortcut: native engine stages 0..6 only, alternate/minigame RDT banks need separate identification.
            if code[0] not in '1234567':
                gaps.append(dict(pl=pl, room=p.name, reason='alternate/minigame stage bank'))
                continue
            hashes[str(p.relative_to(G))] = hashlib.sha256(p.read_bytes()).hexdigest()
            if code not in names:
                gaps.append(dict(pl=pl, room=p.name, reason='no reliable room identity'))
                continue
            stage, room = int(code[0], 16) - 1, int(code[1:], 16)
            found = set()
            # Native floor selection depends on player level, A/B, elevator flags, previous room and lab state.
            for level in range(6):
                for scenario in (0, 0x40000000):
                    for state in (0, 98, 99, 137, 190):
                        for prev, lab in ((0, 0), (0x602, 1)):
                            u.mem_write(0x989ff6, bytes([level]))
                            u.mem_write(0x989ed0, struct.pack('<I', scenario | pl << 31))
                            bank = bytearray(32)
                            if state:
                                struct.pack_into('<I', bank, state // 32 * 4, 0x80000000 >> (state % 32))
                            u.mem_write(0x98eb4c, bytes(bank))
                            u.mem_write(0x98eb1a, struct.pack('<H', prev))
                            u.mem_write(0x692fac, bytes([lab]))
                            floor = call(0x4faf80, stage, room)
                            if floor < 2 or floor >= 20:
                                continue
                            index = call(0x4fb1c0, floor, room)
                            ptr, count = struct.unpack('<IB', u.mem_read((0x53eb98 if pl else 0x53eaf8) + floor * 8, 5))
                            if index >= count:
                                continue
                            q = bytes(u.mem_read(ptr + index * 16, 16))
                            x, y = struct.unpack_from('<hh', q, 4)
                            w, h = q[2:4]
                            if not w or not h:
                                continue
                            key = (pl, floor, index)
                            value = dict(pl=pl, floor=floor, seen=q[12], x=x + w // 2, y=y + h // 2,
                                         ko=names[SHARED_RECT.get((floor, index), code)], rooms=[code], native_va=ptr + index * 16,
                                         native_raw=q.hex(), rect=[x, y, w, h])
                            if key in rows:
                                assert rows[key]['ko'] == value['ko'], (key, rows[key], value)
                                if code not in rows[key]['rooms']:
                                    rows[key]['rooms'].append(code)
                            else:
                                rows[key] = value
                            found.add((floor, index))
            if not found:
                gaps.append(dict(pl=pl, room=p.name, reason='no native drawable room on floors 2..19'))
    return list(rows.values()), gaps, hashes


def raster_labels(names, help_count=0):
    draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    pages, defs = [Image.new('RGB', (256, 256))], []
    x = y = row_h = 1
    for index, name in enumerate(names):
        is_help = index >= len(names) - help_count
        font_px, stroke = (HELP_TITLE_PX if index == len(names) - help_count else HELP_FONT_PX, HELP_STROKE) if is_help else (FONT_PX, STROKE)
        fill = HELP_RGB[index - (len(names) - help_count)] if is_help else (248, 240, 200)
        font = ImageFont.truetype(str(HELP_FONT if is_help else FONT), font_px, index=0)
        text = name
        if is_help and font.getlength(name.replace('\x01', '')) + 2 * stroke + 2 >= 254:
            words = name.split()
            split = min(range(1, len(words)), key=lambda n: abs(font.getlength(' '.join(words[:n])) - font.getlength(' '.join(words[n:]))))
            text = ' '.join(words[:split]) + '\n' + ' '.join(words[split:])
        slots = name.count('\x01')
        prefix, rest = (name.split('\x01')[0], name.split('\x01')[-1]) if slots else (text, '')
        box = (draw.multiline_textbbox((0, 0), text, font=font, spacing=0, align='center', stroke_width=stroke)
               if '\n' in text else font.getbbox(prefix + rest, stroke_width=stroke))
        box = tuple(round(v) for v in box)
        gap = slots * HELP_SLOT * LABEL_SCALE
        w, h = box[2] - box[0] + 2 + gap, box[3] - box[1] + 2
        w += w % 2; h += h % 2
        assert 0 < w < 255 and 0 < h < 255
        if x + w + 1 > 256:
            x, y, row_h = 1, y + row_h + 2, 0
        if y + h + 1 > 256:
            pages.append(Image.new('RGB', (256, 256)))
            x = y = 1; row_h = 0
        tile = Image.new('RGB', (w, h))
        painter = ImageDraw.Draw(tile)
        if '\n' in text:
            painter.multiline_text((1 - box[0], 1 - box[1]), text, font=font, spacing=0, align='center',
                                   fill=fill, stroke_width=stroke, stroke_fill=(16, 16, 16) if is_help else (8, 8, 8))
        else:
            painter.text((1 - box[0], 1 - box[1]), prefix, font=font, fill=fill, stroke_width=stroke, stroke_fill=(16, 16, 16) if is_help else (8, 8, 8))
            if slots:
                painter.text((1 - box[0] + round(font.getlength(prefix)) + gap, 1 - box[1]), rest, font=font,
                             fill=fill, stroke_width=stroke, stroke_fill=(16, 16, 16) if is_help else (8, 8, 8))
        pages[-1].paste(tile, (x, y))
        icon_x = round((1 - box[0] + font.getlength(prefix)) / LABEL_SCALE) if slots else 0
        defs.append(dict(page=len(pages)-1, u=x, v=y, w=w, h=h, text=name, font_px=font_px, icon_x=icon_x, slots=slots))
        x += w + 2; row_h = max(row_h, h)
    return pages, defs


GAP = 3
FIT = 0.9      # label box pixels that must sit on the room's own mask to stay inside
SMALL = 0.8    # ...or a SMALL-scaled label box must fit completely (old "80% of the name" rule, on the real shape)


def load_masks():
    """(pl, floor, native_va) -> (w, h, row-major bool mask) from Task F room_shapes.json."""
    out = {}
    for f in json.loads((R / 'room_shapes.json').read_text())['floors']:
        for s in f['rooms']:
            m = [[False] * s['w'] for _ in range(s['h'])]
            for y, runs in enumerate(s['runs']):
                for a, n in runs:
                    for x in range(a, min(a + n, s['w'])):
                        m[y][x] = True
            out[(f['pl'], f['floor'], s['va'])] = m
    return out


def erode(m):
    h, w = len(m), len(m[0])
    return [[m[y][x] and all(0 <= y + j < h and 0 <= x + i < w and m[y + j][x + i]
                             for j in (-1, 0, 1) for i in (-1, 0, 1)) for x in range(w)] for y in range(h)]


def sat_of(m):
    h, w = len(m), len(m[0])
    s = [[0] * (w + 1) for _ in range(h + 1)]
    for y in range(h):
        for x in range(w):
            s[y + 1][x + 1] = s[y][x + 1] + s[y + 1][x] - s[y][x] + m[y][x]
    return s


def box_sum(s, x, y, bw, bh):
    h, w = len(s) - 1, len(s[0]) - 1
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + bw, w), min(y + bh, h)
    return 0 if x1 <= x0 or y1 <= y0 else s[y1][x1] - s[y0][x1] - s[y1][x0] + s[y0][x0]


def hit(a, b):
    return a[0] < b[0] + b[2] + 1 and b[0] < a[0] + a[2] + 1 and a[1] < b[1] + b[3] + 1 and b[1] < a[1] + a[3] + 1


def pole(m):
    """Pole of inaccessibility: the mask pixel farthest from its edge (chessboard distance), ties nearest the centroid.
    The bounding-box centre of an L-shaped room can fall outside it (RE0 HD map mod rule)."""
    h, w = len(m), len(m[0])
    pts = [(x, y) for y in range(h) for x in range(w) if m[y][x]]
    dist = {p: 0 for p in pts if p[0] in (0, w - 1) or p[1] in (0, h - 1) or
            not all(m[p[1] + j][p[0] + i] for j in (-1, 0, 1) for i in (-1, 0, 1))}
    todo = list(dist)
    while todo:
        nxt = []
        for x, y in todo:
            for j in (-1, 0, 1):
                for i in (-1, 0, 1):
                    q = (x + i, y + j)
                    if 0 <= q[0] < w and 0 <= q[1] < h and m[q[1]][q[0]] and q not in dist:
                        dist[q] = dist[(x, y)] + 1; nxt.append(q)
        todo = nxt
    cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    return max(pts, key=lambda p: (dist[p], -((p[0] - cx) ** 2 + (p[1] - cy) ** 2)))


def fit_inside(m, s, ox, oy, lw, lh, placed):
    """Label centre (absolute) on the room's own mask nearest its pole of inaccessibility, among the spots within
    0.05 of the best coverage (or fully covered) that overlap no placed box; else None."""
    h, w = len(m), len(m[0])
    if not any(map(any, m)):
        return None
    qx, qy = pole(m)
    best = None
    for scale, need in ((1.0, FIT), (SMALL, 1.0)):
        bw, bh = max(1, -(-int(lw * scale * 100) // 100)), max(1, -(-int(lh * scale * 100) // 100))
        spots = []
        for by in range(-bh // 2, h - bh // 2):
            for bx in range(-bw // 2, w - bw // 2):
                cov = box_sum(s, bx, by, bw, bh) / (bw * bh)
                if cov < need:
                    continue
                px, py = bx + bw // 2, by + bh // 2        # label centre, sprite coords
                if not (0 <= px < w and 0 <= py < h and m[py][px]):
                    continue
                if any(hit((ox + px - lw // 2, oy + py - lh // 2, lw, lh), b) for b in placed):
                    continue
                spots.append((cov, px, py))
        if spots:
            top = max(c for c, _, _ in spots)
            _, px, py = min((sp for sp in spots if sp[0] >= top - 0.05 or sp[0] == 1.0),
                            key=lambda sp: ((sp[1] - qx) ** 2 + (sp[2] - qy) ** 2, -sp[0]))
            return ox + px, oy + py, box_sum(s, px - lw // 2, py - lh // 2, lw, lh) / (lw * lh)
    return None


LEADER_CLEAR, LEADER_MARGIN = 2, 3  # px clear of any room mask beside the line; px from its own room's corners at the start


def along_outline(own, occ, line):
    """A leader may not share a vertical/horizontal line with a room outline (user 2026-11-02, Evidence Room):
    it starts away from its own room's corners and runs clear of every room mask."""
    sx, sy, ex, ey = line
    px, py = (1, 0) if sx == ex else (0, 1)
    a = b = 0
    # occ, not own: where masks overlap the other room's wall is what shows.
    while occ.get((sx + px * (a + 1), sy + py * (a + 1))) == occ.get((sx, sy)):
        a += 1
    while occ.get((sx - px * (b + 1), sy - py * (b + 1))) == occ.get((sx, sy)):
        b += 1
    if min(a, b) < min(LEADER_MARGIN, (a + b) // 2) or not a + b:  # narrow rooms: their centre is the best available
        return True
    dx, dy = (ex > sx) - (ex < sx), (ey > sy) - (ey < sy)
    # A wall beside the line shows as a room change across it; enclosed rooms may still cross a neighbour at a right angle.
    return any(occ.get((sx + dx * k + px * d, sy + dy * k + py * d)) != occ.get((sx + dx * k, sy + dy * k))
               for k in range(1, max(abs(ex - sx), abs(ey - sy)) + 1)
               for d in (-LEADER_CLEAR, -1, 1, LEADER_CLEAR))


def near_spot(r, px, occ, blocked, lw, lh, placed, lines, kmax=45, side=None):
    """Shortest axis-aligned leader from a mask edge pixel to a label box standing in free space (no mask +1px margin)."""
    best = None
    own = set(px)
    for (sx, sy) in px:
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            if side and (('top' if dy < 0 else 'bottom') if dy else ('left' if dx < 0 else 'right')) != side:
                continue
            if (sx + dx, sy + dy) in own:
                continue
            for k in range(1, kmax):
                if best and k >= best[0]:
                    break
                ex, ey = sx + dx * k, sy + dy * k
                if (ex, ey) in occ:
                    break
                if along_outline(own, occ, (sx, sy, ex, ey)):
                    continue
                for sh in (0, 3, -3, 6, -6, 9, -9):
                    if abs(sh) > lw // 2 - 2 and dy or abs(sh) > lh // 2 - 1 and dx:
                        continue
                    if dy:
                        box = (ex - lw // 2 + sh, ey - lh + 1 if dy < 0 else ey, lw, lh)
                    else:
                        box = (ex - lw + 1 if dx < 0 else ex, ey - lh // 2 + sh, lw, lh)
                    if box[0] < 1 or box[1] < 1 or box[0] + lw > 318 or box[1] + lh > 238:
                        continue
                    if any((x, y) in blocked for y in range(box[1], box[1] + lh) for x in range(box[0], box[0] + lw)):
                        continue
                    if any(hit(box, b) for b in placed):
                        continue
                    lo_x, hi_x = sorted((sx, ex)); lo_y, hi_y = sorted((sy, ey))
                    if any(b[0] <= hi_x and lo_x < b[0] + b[2] and b[1] <= hi_y and lo_y < b[1] + b[3] for b in placed):
                        continue
                    if any(box[0] <= max(a, e) and min(a, e) < box[0] + box[2] and box[1] <= max(c, f) and min(c, f) < box[1] + box[3]
                           for a, c, e, f in lines):
                        continue
                    cx, cy = box[0] + lw // 2, box[1] + lh // 2
                    align = abs(sx - (r['rect'][0] + r['rect'][2] / 2)) if side in ('top', 'bottom') else 0
                    cost = k + abs(sh) * 0.1 + align * 0.05
                    if best is None or cost < best[0]:
                        best = (cost, cx, cy, (sx, sy, ex, ey), box)
    return best


# Room names are fixed first and nothing avoids them, and they avoid no marker (RE0 HD map mod rule, user 2026-11-07); they
# only keep off each other and the legend/readout panels (re2_keymap.c LEGEND_Y and readout_layout).
LEGEND_BOX = (1, 210, 317, 28)
# ponytail: room names live in map space, panels on the screen; the native pan (0x691fb8, (4,6) in the tests) shifts
# one against the other, so each panel is reserved PAN_MARGIN px larger toward the map. Per-floor pans would be exact.
PAN_MARGIN = 8


def readout_width(labels, help_start):
    """re2_keymap.c readout_layout: a name column (opacity over size) and an icon column (modifier + opacity over
    size); each value after its hint."""
    q = lambda i: (labels[help_start + i]['w'] + LABEL_SCALE // 2) // LABEL_SCALE
    value = max(q(i) for i in range(34, 54))
    prefix = max(q(30), q(31))
    return max(q(28), q(29)) + 2 + value + 6 + prefix + 2 + max(q(32), q(33)) + 2 + value


def place_labels(rows, labels, masks):
    """Inside the real room shape when the name fits; otherwise outside the floor bbox with a leader line
    that starts on an actual mask-edge pixel."""
    groups = {}
    for r in rows:
        groups.setdefault((r['pl'], r['floor']), []).append(r)
    for group in groups.values():
        bx0 = min(r['rect'][0] for r in group); by0 = min(r['rect'][1] for r in group)
        bx1 = max(r['rect'][0] + r['rect'][2] for r in group); by1 = max(r['rect'][1] + r['rect'][3] for r in group)
        occ = {}  # absolute pixel -> id of the row owning it
        for r in group:
            m = masks[(r['pl'], r['floor'], r['native_va'])]
            r['_m'] = m; r['_s'] = sat_of(m)
            for y, row in enumerate(m):
                for x, v in enumerate(row):
                    if v:
                        occ[(r['rect'][0] + x, r['rect'][1] + y)] = id(r)
            d = labels[r['label']]
            r['lw'], r['lh'] = (d['w'] + LABEL_SCALE // 2) // LABEL_SCALE, (d['h'] + LABEL_SCALE // 2) // LABEL_SCALE
            r['line'] = (0, 0, 0, 0)
            r['outside_reason'] = None
        blocked = {(x + i, y + j) for x, y in occ for j in (-1, 0, 1) for i in (-1, 0, 1)}
        placed, lines = list(PANELS), []
        for r in sorted(group, key=lambda r: sum(map(sum, r['_m']))):  # tightest rooms choose first
            spot = None  # 2px, then 1px wall margin, then none, before going outside
            for m, s in ((erode(erode(r['_m'])), None), (erode(r['_m']), None), (r['_m'], r['_s'])):  # outline is ~2px wide
                spot = fit_inside(m, s or sat_of(m), r['rect'][0], r['rect'][1], r['lw'], r['lh'], placed)
                if spot:
                    break
            if spot:
                r['x'], r['y'], r['cover'] = spot[0], spot[1], round(spot[2], 3)
                placed.append((r['x'] - r['lw'] // 2, r['y'] - r['lh'] // 2, r['lw'], r['lh']))
            else:
                r['outside_reason'] = 'fit'
        for r in sorted(group, key=lambda r: (r['rect'][1], r['rect'][0])):
            if not r['outside_reason']:
                continue
            lw, lh = r['lw'], r['lh']
            x0, y0 = r['rect'][:2]
            px = [(x0 + x, y0 + y) for y, row in enumerate(r['_m']) for x, v in enumerate(row) if v]
            # shortcut: the 2F emergency-stair label belongs below its stairwell, not beside the rooftop entrance.
            side = 'bottom' if r['floor'] == 3 and '116' in r['rooms'] else None
            best = near_spot(r, px, occ, blocked, lw, lh, placed, lines, side=side)
            r['outside_reason'] = 'near' if best else 'fit'
            for side in (() if best else ('top', 'bottom', 'left', 'right')):
                key = 0 if side in ('top', 'bottom') else 1
                vals = sorted({p[key] for p in px})
                n = len(vals)
                for k, c in enumerate(dict.fromkeys((vals[n // 2], vals[n // 4], vals[n * 3 // 4], vals[min(2, n - 1)], vals[max(n - 3, 0)], *vals))):
                    run = [p for p in px if p[key] == c]
                    # edge pixel of the mask in the outward direction
                    sx, sy = (min(run, key=lambda p: p[1]) if side == 'top' else max(run, key=lambda p: p[1])) if key == 0 else \
                             (min(run, key=lambda p: p[0]) if side == 'left' else max(run, key=lambda p: p[0]))
                    for along in (0, 1, -1):
                        for ring in range(6):
                            if side == 'top':
                                ly = by0 - GAP - lh // 2 - ring * (lh + 1); lx = c + along * (lw // 3); line = (c, sy, c, ly + lh // 2)
                            elif side == 'bottom':
                                ly = by1 + GAP + lh // 2 + ring * (lh + 1); lx = c + along * (lw // 3); line = (c, sy, c, ly - lh // 2)
                            elif side == 'left':
                                lx = bx0 - GAP - lw // 2 - ring * (lw + 2); ly = c + along * (lh // 2 + 1); line = (sx, c, lx + lw // 2, c)
                            else:
                                lx = bx1 + GAP + lw // 2 + ring * (lw + 2); ly = c + along * (lh // 2 + 1); line = (sx, c, lx - lw // 2, c)
                            box = (lx - lw // 2, ly - lh // 2, lw, lh)
                            if any(hit(box, b) for b in placed) or along_outline(set(px), occ, line):
                                continue
                            lo_x, hi_x = sorted((line[0], line[2])); lo_y, hi_y = sorted((line[1], line[3]))
                            crossed = sum(1 for yy in range(lo_y, hi_y + 1) for xx in range(lo_x, hi_x + 1)
                                          if (xx, yy) in occ and occ[(xx, yy)] != id(r))
                            off = box[0] < 1 or box[1] < 1 or box[0] + lw > 318 or box[1] + lh > 238
                            hits = sum(1 for b in placed if b[0] <= hi_x and lo_x < b[0] + b[2] and b[1] <= hi_y and lo_y < b[1] + b[3])
                            hits += sum(1 for a, c2, e, f in lines if box[0] <= max(a, e) and min(a, e) < box[0] + box[2]
                                        and box[1] <= max(c2, f) and min(c2, f) < box[1] + box[3])
                            cost = (crossed > 0) * 1000 + off * 5000 + hits * 3000 + along_outline(set(px), occ, line) * 2000 + (hi_x - lo_x) + (hi_y - lo_y) + abs(along) * 4 + k * 6
                            if best is None or cost < best[0]:
                                best = (cost, lx, ly, line, box)
                            break
            _, r['x'], r['y'], r['line'], box = best
            placed.append(box); lines.append(r['line'])


def generate():
    rows, gaps, hashes = native_rows()
    rows.sort(key=lambda r: (r['pl'], r['floor'], r['seen'], r['native_va']))
    raw_names = sorted({r['ko'] for r in rows})
    font = ImageFont.truetype(str(FONT), FONT_PX)
    wrapped = {}
    display_names = raw_names
    names = display_names + list(HELP_TEXT[LANGUAGE])
    pages, labels = raster_labels(names, len(HELP_TEXT[LANGUAGE]))
    for r in rows:
        r['label'] = names.index((wrapped if LANGUAGE == 'English' else {}).get(r['ko'], r['ko']))
    masks = load_masks()
    global PANELS
    width = readout_width(labels, len(labels) - len(HELP_TEXT[LANGUAGE]))
    PANELS = [(1, LEGEND_BOX[1] - PAN_MARGIN, 317, LEGEND_BOX[3] + PAN_MARGIN),  # re2_keymap.c READOUT_X/READOUT_Y:
              (8 - PAN_MARGIN, 1 - PAN_MARGIN, width + PAN_MARGIN, 16 + PAN_MARGIN)]
    place_labels(rows, labels, masks)
    # Wrap only between words: a single word is never split mid-word (user 2026-10-23: "Elev/ator"). Korean names
    # are wrapped the same way (between words) and otherwise stay on one line. Also wrapped: a one-line name wider
    # than 150% of its room (RE0 HD map mod rule).
    retry = {r['ko'] for r in rows if len(r['ko'].split()) > 1 and (r['outside_reason'] or r['lw'] > 1.5 * r['rect'][2])}
    for name in retry:
        parts = name.split()
        best = min(range(1, len(parts)), key=lambda n: abs(font.getlength(' '.join(parts[:n])) - font.getlength(' '.join(parts[n:]))))
        wrapped[name] = ' '.join(parts[:best]) + '\n' + ' '.join(parts[best:])
    if retry:
        display_names = [wrapped.get(n, n) for n in raw_names]
        names = display_names + list(HELP_TEXT[LANGUAGE])
        pages, labels = raster_labels(names, len(HELP_TEXT[LANGUAGE]))
        for r in rows:
            r['label'] = names.index(wrapped.get(r['ko'], r['ko']))
        place_labels(rows, labels, masks)
    if LANGUAGE == 'English':
        records = [r for r in rows if r['ko'] == 'Records Room' and r['floor'] == 2]
        # Wrapped either way; it may now sit outside on a leader when marker spots fill the room (user 2026-10-26).
        assert len(records) == 2 and all(labels[r['label']]['text'] == 'Records\nRoom' for r in records), \
            'RPD Records Room should use the two-line label'
    stairs = [r for r in rows if r['floor'] == 3 and '116' in r['rooms']]
    assert len(stairs) == 2 and all(not r['outside_reason'] or r['line'][3] > r['line'][1] for r in stairs), 'RPD 2F Emergency Stairway labels should sit below when outside'
    for r in rows:  # self-check: inside labels sit on their own mask; leader lines start on it
        m, (x0, y0) = r['_m'], r['rect'][:2]
        if r['outside_reason']:
            a, b = r['line'][:2]
            assert 0 <= a - x0 < len(m[0]) and 0 <= b - y0 < len(m) and m[b - y0][a - x0], ('line start off mask', r['ko'])
        else:
            assert r['cover'] >= SMALL * SMALL and m[r['y'] - y0][r['x'] - x0], ('inside label off mask', r['ko'], r['cover'])
    violations = []
    for r in rows:  # self-check: no leader shares a line with a room outline
        if r['outside_reason']:
            occ = {(o['rect'][0] + x, o['rect'][1] + y): id(o) for o in rows if (o['pl'], o['floor']) == (r['pl'], r['floor'])
                   for y, row in enumerate(o['_m']) for x, v in enumerate(row) if v}
            own = {(r['rect'][0] + x, r['rect'][1] + y) for y, row in enumerate(r['_m']) for x, v in enumerate(row) if v}
            if along_outline(own, occ, r['line']):
                violations.append((r['pl'], r['floor'], r['ko'], r['line']))
    assert not violations, ('leader along an outline', violations)
    for r in rows:  # self-check: outside labels overlap no room mask on their floor
        if r['outside_reason']:
            bx, by = r['x'] - r['lw'] // 2, r['y'] - r['lh'] // 2
            for o in rows:
                if (o['pl'], o['floor']) == (r['pl'], r['floor']):
                    ox, oy = o['rect'][:2]
                    assert not any(v for yy in range(max(by, oy), min(by + r['lh'], oy + o['rect'][3]))
                                   for xx, v in ((xx, o['_m'][yy - oy][xx - ox]) for xx in range(max(bx, ox), min(bx + r['lw'], ox + o['rect'][2])))), \
                        ('outside label on a room mask', r['ko'], o['ko'])
    for r in rows:  # self-check: no leader line runs through another room name on the same map
        a, b, c, e = r['line']
        if a | b | c | e:
            lo_x, hi_x = sorted((a, c)); lo_y, hi_y = sorted((b, e))
            for o in rows:
                if o is not r and (o['pl'], o['floor']) == (r['pl'], r['floor']):
                    bx, by = o['x'] - o['lw'] // 2, o['y'] - o['lh'] // 2
                    assert not (bx <= hi_x and lo_x < bx + o['lw'] and by <= hi_y and lo_y < by + o['lh']), (r['ko'], o['ko'])
    lines = ['/* Generated by generate_room_names.py; x/y are centered map anchors, add native map pan. */',
             'typedef struct { unsigned char pl,floor,seen; short x,y; unsigned short label; short lx0,ly0,lx1,ly1; } RoomName; /* x,y label centre; l* leader line, all 0 = none */',
             'static const RoomName room_names[]={']
    for r in rows:
        lines.append('{%d,%d,%d,%d,%d,%d,%d,%d,%d,%d}, /* %s %s */' %
                     ((r['pl'],r['floor'],r['seen'],r['x'],r['y'],r['label'])+tuple(r['line'])+(','.join(r['rooms']),r['ko'])))
    (R / 'room_names.h').write_text('\n'.join(lines + ['};\n']))
    header = ['/* RGB555: zero transparent, dark outline 0x421; draw labels at w/2,h/2. */',
              'typedef struct { unsigned char page,u,v,w,h; } RoomLabel;',
              f'#define ROOM_LABEL_PAGE_COUNT {len(pages)}', f'#define ROOM_LABEL_SCALE {LABEL_SCALE}', f'#define ROOM_LABEL_COUNT {len(labels)}',
              f'#define ROOM_HELP_LABEL {len(labels) - len(HELP_TEXT[LANGUAGE])}',
              f'#define ROOM_HELP_LABEL_COUNT {len(HELP_TEXT[LANGUAGE])}',
              f'#define ROOM_READOUT_W {PANELS[1][2]}',
              'static const RoomLabel room_labels[]={' + ','.join('{%d,%d,%d,%d,%d}' %
              (d['page'],d['u'],d['v'],d['w'],d['h']) for d in labels) + '};',
              '/* map-pixel x of the first marker slot inside each legend row (0 = none) */',
              'static const unsigned char room_help_icon_x[]={' + ','.join(str(d['icon_x']) for d in labels[-len(HELP_TEXT[LANGUAGE]):]) + '};',
              'static const unsigned short room_label_pixels[ROOM_LABEL_PAGE_COUNT][65536]={']
    for i, page in enumerate(pages):
        page.putpixel((0, 0), (200, 190, 150))
        page.save(R / f'room_names-atlas-{i}.png')
        pixels = [(r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10) for r,g,b in page.get_flattened_data()]
        header.append('{' + ','.join(hex(p) for p in pixels) + '},')
    (R / 'room_labels.h').write_text('\n'.join(header + ['};\n']))
    preview = Image.new('RGB', (640, ((len(names) + 3) // 4) * 32), (28, 32, 35))
    draw = ImageDraw.Draw(preview)
    for i, label in enumerate(labels):
        x, y = i % 4 * 160, i // 4 * 32
        tile = pages[label['page']].crop((label['u'],label['v'],label['u']+label['w'],label['v']+label['h']))
        preview.paste(tile,(x,y))
    preview.save(R / 'room_names-preview.png')
    for r in rows:
        r.pop('_m'); r.pop('_s')
    data = dict(as_of='2026-10-15', source=SOURCE, naming=f'Independent short {LANGUAGE} translations of factual room identities; not official patch strings',
                exe_sha256=EXE_SHA, font=FONT.name, font_sha256=hashlib.sha256(FONT.read_bytes()).hexdigest(),
                legend_font=HELP_FONT.name, legend_font_sha256=hashlib.sha256(HELP_FONT.read_bytes()).hexdigest(),
                legend_body_px=HELP_FONT_PX, legend_title_px=HELP_TITLE_PX, legend_stroke=HELP_STROKE,
                rows=rows, labels=labels, pages=len(pages), gaps=gaps, rdt_sha256=hashes)
    (R / 'room_names-provenance.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(rows)} map entries, {len(labels)} {LANGUAGE} labels, {len(pages)} pages, {len(gaps)} excluded files')
    return data

if __name__ == '__main__':
    generate()
