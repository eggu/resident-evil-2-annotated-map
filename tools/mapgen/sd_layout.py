"""SD room-name layout for every map screen and language -> data/sd-layout.json (screen coordinates, 320x240).

Inputs: data/room_shapes.json (room masks), src/room_names-{en,ko}.h (which rooms are named, in runtime order), the marker
headers (positions of everything that can be drawn), fonts/Galmuri9.ttf. Slow (minutes, parallel): run when names, rooms or
markers change, then tools/mapgen/build_sd.py. RE2 maps are single-floor screens that always fit 320x240 (RE3 'small
pages'), so names keep out of the native screen furniture, the folded legend and the screen edges."""
import json, re, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sd_place
from sd_place import Sat, abbr, place, split

FONT = ImageFont.truetype(str(ROOT / 'fonts/Galmuri9.ttf'), 10)
LINE_H = 11   # 10 px Galmuri9 + 1 px shadow
LEADER_INSET = 3   # leaders start this far inside their room
W, H = 320, 240
PROJ_CENTRE = 6   # re2_keymap.c: marker data x,y + 6 = the marker centre
MARK = 4          # 9x9 markers: 4 px each side of the centre

# Native screen furniture seen in the 1600x1200 game at 5x (docs/screenshots/1.3.0): area title, compass, the four green
# floor/area arrows (re2_keymap.c nav_arrows_draw), the folded legend and a 6 px frame (x, y, w, h).
HUD = [(8, 14, 100, 36), (252, 24, 30, 44), (154, 18, 12, 9), (154, 196, 12, 9), (5, 114, 9, 12), (306, 114, 9, 12), (2, 224, 62, 14),
       (0, 0, 320, 6), (0, 232, 320, 8), (0, 0, 6, 240), (314, 0, 6, 240)]


def ink(text):
    """Glyph pixels of a name (Galmuri9, lines LINE_H apart) cropped to their bounding box: the layout box and the sprite are
    this box (the sprite adds the 1 px shadow), so a leader's 1 px to the name is real, not blank font rows."""
    lines = text.split('\n')
    m = Image.new('1', (max(int(FONT.getlength(l)) for l in lines) + 2, LINE_H * len(lines) + 1))
    d = ImageDraw.Draw(m)
    for i, l in enumerate(lines):
        d.text((0, LINE_H * i), l, font=FONT, fill=1)
    g = np.array(m, bool)
    ys, xs = np.nonzero(g)
    return g[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]


def size_of(text):
    g = ink(text)
    return g.shape[1], g.shape[0]


def header_rows(path):
    """(pl, floor, seen, room code, name) in the header's runtime order."""
    out = []
    for l in open(path, encoding='utf-8'):
        m = re.match(r'\{(\d+),(\d+),(\d+),.*\}, /\* ([\w,]+) (.*) \*/', l)
        if m:
            out.append((int(m[1]), int(m[2]), int(m[3]), m[4], m[5]))
    return out


def struct_rows(path, name):
    t = Path(path).read_text()
    t = t[t.index(name + '[]') :]
    t = t[: t.index('};')]
    return [tuple(int(v) for v in re.findall(r'-?\d+', m)) for m in re.findall(r'\{([^{}]*)\}', t[t.index('{') + 1 :])]


def markers():
    """(pl, floor) -> [(centre x, centre y)] of every marker that can be drawn there (non-enemy)."""
    out = {}
    def add(pl, floor, x, y): out.setdefault((pl & 1, floor), set()).add((x, y))
    for r in struct_rows(ROOT / 'src/items.h', 'map_items'): add(r[0], r[1], r[2] + PROJ_CENTRE, r[3] + PROJ_CENTRE)
    for r in struct_rows(ROOT / 'src/overlay_data.h', 'map_markers'): add(r[0], r[1], r[4] + PROJ_CENTRE, r[5] + PROJ_CENTRE)
    for r in struct_rows(ROOT / 'src/overlay_data.h', 'map_documents'): add(r[0], r[1], r[5] + PROJ_CENTRE, r[6] + PROJ_CENTRE)
    for r in struct_rows(ROOT / 'src/overlay_data.h', 'map_interactions'):
        if r[3] in (6, 20): add(r[0], r[1], r[4] + PROJ_CENTRE, r[5] + PROJ_CENTRE)
    for r in struct_rows(ROOT / 'src/doors-all.h', 'doors'): add(r[0], r[1], r[2], r[3])
    return out


def rect_cells(rect):
    cells = set()
    for y, runs in enumerate(rect['runs']):
        for a, n in runs:
            cells |= {(rect['x'] + x, rect['y'] + y) for x in range(a, min(a + n, rect['w']))}
    return cells


def edge_mids(own):
    """Middle pixel of every straight edge run (3 px or longer) of the room, with its outward direction, pulled up to
    LEADER_INSET px into the room. A side with no such run still offers the middle of its longest run."""
    out = []
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        key = (lambda c: (c[1], c[0])) if dy else (lambda c: (c[0], c[1]))
        edge = sorted((c for c in own if (c[0] + dx, c[1] + dy) not in own), key=key)
        run, runs = [], []
        for c in edge + [None]:
            if c is not None and run and key(c)[0] == key(run[-1])[0] and key(c)[1] == key(run[-1])[1] + 1:
                run.append(c); continue
            if run: runs.append(run)
            run = [c] if c is not None else []
        long = [r for r in runs if len(r) >= 3] or ([max(runs, key=len)] if runs else [])
        for r in long:
            x, y = r[len(r) // 2]
            k = 0
            while k < LEADER_INSET and (x - dx * (k + 1), y - dy * (k + 1)) in own: k += 1
            out.append(((x - dx * k, y - dy * k), (dx, dy)))
    return out


def boundary(cells):
    return {c for c in cells if any((c[0] + a, c[1] + b) not in cells for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))}


def depth_map(mask):
    """Chessboard distance of every room cell to the nearest outside cell (repeated erosion)."""
    d = np.zeros(mask.shape, np.int32)
    cur, k = mask.copy(), 0
    while cur.any():
        k += 1
        d[cur] = k
        e = cur.copy()
        e[1:] &= cur[:-1]; e[:-1] &= cur[1:]; e[:, 1:] &= cur[:, :-1]; e[:, :-1] &= cur[:, 1:]
        e[0] = e[-1] = False; e[:, 0] = e[:, -1] = False
        cur = e
    return d


def inside_boxes(cells, todo, marks):
    """Names that fit inside their room at 2x zoom (user 2026-11-13): the room's mask doubled, the 9x9 markers kept at 1:1 size
    (centre doubled), a 1 px margin round the name and its shadow. Returns {index: (text, x, y)} with x, y in the doubled map's
    coordinates (the view offset is subtracted at runtime). One line first, two lines when only they fit; the spot nearest the
    room's deepest point; names of different rooms never overlap."""
    mk = np.zeros((2 * H + 2, 2 * W + 2), bool)
    for x, y in marks:
        mk[max(0, 2 * y - 5) : 2 * y + 6, max(0, 2 * x - 5) : 2 * x + 6] = True
    placed, out = [], {}
    for i, seen, name in sorted(todo, key=lambda t: len(cells[t[1]])):
        m = np.zeros(mk.shape, bool)
        for x, y in cells[seen]:
            m[2 * y : 2 * y + 2, 2 * x : 2 * x + 2] = True
        depth = depth_map(m)
        py, px = np.unravel_index(depth.argmax(), depth.shape)
        bad = ~m | mk
        ii = np.pad(bad.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        for text in [name] + ([split(name)] if ' ' in name else []):
            w, h = size_of(text)
            w, h = w + 1, h + 1   # with the shadow
            bw, bh = w + 2, h + 2   # and the margin
            Hh, Ww = bad.shape
            ys, xs = np.mgrid[0 : Hh - bh + 1, 0 : Ww - bw + 1]
            free = (ii[ys + bh, xs + bw] - ii[ys, xs + bw] - ii[ys + bh, xs] + ii[ys, xs]) == 0
            for bx, by, bw2, bh2 in placed:   # keep clear of this floor's other inside names
                free[max(0, by - bh - 1) : max(0, by + bh2 + 2), max(0, bx - bw - 1) : max(0, bx + bw2 + 2)] = False
            if not free.any():
                continue
            cy, cx = np.nonzero(free)
            k = np.argmin((cx + 1 + w / 2 - px) ** 2 + (cy + 1 + h / 2 - py) ** 2)
            bx, by = int(cx[k]) + 1, int(cy[k]) + 1
            placed.append((bx, by, w, h))
            out[i] = (text, bx, by)
            break
    return out


def floor_layout(pl, floor, rects, rows, marks, lang):
    """rows: [(index, room code, name)] named rooms of this screen; returns {index: placement}."""
    cells = {r['seen']: rect_cells(r) for r in rects}
    by_seen = {r['seen']: r for r in rects}
    todo = [(i, seen, name) for i, seen, name in rows if seen in cells and cells[seen]]
    pix = set().union(*cells.values()) if cells else set()
    grow = lambda s, k: {(x + i, y + j) for x, y in s for j in range(-k, k + 1) for i in range(-k, k + 1) if 0 <= x + i < W and 0 <= y + j < H}
    marked = {(x + i, y + j) for x, y in marks for j in range(-MARK - 1, MARK + 2) for i in range(-MARK - 1, MARK + 2)}
    hud = {(x + i, y + j) for x, y, w, h in HUD for j in range(h) for i in range(w)}
    blocked = Sat(grow(pix, 2) | marked | hud, (H + 2, W + 2))
    grey = set().union(*(boundary(c) for c in cells.values())) if cells else set()
    named = {seen for _, seen, _ in todo}
    other = set().union(*(c for s, c in cells.items() if s not in named)) if cells else set()
    def label(row, long):
        return row[2] if lang == 'ko' or long else abbr(row[2])
    def run(long_names):
        prs = [dict(key=i, name=long_names.get(i, abbr(n) if lang == 'en' else n), cells=cells[seen]) for i, seen, n in todo]
        occ = {c: r['key'] for r in prs for c in r['cells']}
        return prs, place(prs, size_of, occ, grey, blocked, W, H, edge_mids, refine=(lang == 'en'), other=other)
    longs = {i: n for i, _, n in todo}   # full names first; abbreviate only what finds no place (RE3 small maps)
    prs, placed = run(longs)
    forced = {k for k, o in placed.items() if o.get('forced')}
    if forced and lang == 'en':
        longs = {i: (abbr(n) if i in forced else n) for i, _, n in todo}
        prs, placed = run(longs)
        if any(o.get('forced') for o in placed.values()):
            prs2, again = run({})
            if sum(bool(o.get('forced')) for o in again.values()) < sum(bool(o.get('forced')) for o in placed.values()): placed = again
    out = {}
    for i, seen, n in todo:
        o = placed[i]
        box = o.get('box')
        out[i] = dict(text=o['text'], x=box[0] if box else round(o['x'] - size_of(o['text'])[0] / 2),
                      y=box[1] if box else round(o['y'] - size_of(o['text'])[1] / 2),
                      leader=[list(p) for p in (o.get('poly') or [])][:3], forced=bool(o.get('forced')))
    for i, (text, bx, by) in inside_boxes(cells, todo, marks).items():
        out[i]['inside'] = dict(text=text, x=bx, y=by)
    add_zoom_leaders(pl, floor, rects, rows, out)
    print(f'pl {pl} floor {floor} {lang}: {len(out)} names, forced {[o["text"] for o in out.values() if o["forced"]]}', flush=True)
    return out


def add_zoom_leaders(pl, floor, rects, rows, entries):
    """2x leaders (user 2026-11-13): at 2x zoom a leader is horizontal or vertical, with at most one right-angle bend. The 1x layout
    uses a slightly slanted leader when no straight one fits beside the room's edge-run middle; doubled, that slant is plain to see.
    At 2x the rooms are twice as big, so the leader is rebuilt from the name's end (the doubled 1x end, the name keeps its offset to
    it): straight along the axis the name hangs on into its own room, else one L. It starts 3 px inside the room, crosses no other
    room and no other name. Sets entry['zoom'] = [[x, y], ...] (start, optional bend; doubled-map coordinates) where one exists."""
    cells = {r['seen']: rect_cells(r) for r in rects}
    cells2 = {seen: {(2 * x + i, 2 * y + j) for x, y in cs for i in (0, 1) for j in (0, 1)} for seen, cs in cells.items()}
    seen_of = {i: seen for i, seen, _ in rows}
    ends = {}
    for i, e in entries.items():
        e.pop('zoom', None)
        if len(e['leader']) >= 2 and not e.get('inside'):
            w, h = size_of(e['text']); ex, ey = e['leader'][-1]
            ends[i] = (2 * ex + (e['x'] - ex), 2 * ey + (e['y'] - ey), w, h, 2 * ex, 2 * ey)   # name box at 2x (anchored to its end)
    for i, (bx, by, w, h, ex, ey) in ends.items():
        e = entries[i]
        own = cells2.get(seen_of[i], set())
        others = set().union(*(c for s2, c in cells2.items() if s2 != seen_of[i])) if cells2 else set()
        boxes = [(b2[0] - 1, b2[1] - 1, b2[2] + 3, b2[3] + 3) for k, b2 in ends.items() if k != i]
        mine = (bx, by, w, h)
        cross = [False]   # second pass: a leader may cross other rooms, as at 1x when nothing else is free
        free = lambda p: (0 <= p[0] < 2 * W and 0 <= p[1] < 2 * H and (cross[0] or p not in others)
                          and not any(x0 <= p[0] < x0 + bw and y0 <= p[1] < y0 + bh for x0, y0, bw, bh in boxes))
        def into(p, d):
            """Walk from p along d to the own room and LEADER_INSET px into it: (length, start) or None."""
            for k in range(1, 260):
                q = (p[0] + d[0] * k, p[1] + d[1] * k)
                if q in own and not (0 <= q[0] < 2 * W and 0 <= q[1] < 2 * H): return None
                if not free(q) and q not in own: return None
                if q in own:
                    n = 0
                    while n < LEADER_INSET and (q[0] + d[0] * (n + 1), q[1] + d[1] * (n + 1)) in own: n += 1
                    return (k + n, (q[0] + d[0] * n, q[1] + d[1] * n)) if n >= 1 else None
            return None
        dirs = ((0, -1), (0, 1), (-1, 0), (1, 0))
        in_mine = lambda p: mine[0] <= p[0] < mine[0] + mine[2] and mine[1] <= p[1] < mine[1] + mine[3]
        best = None
        for cross[0] in (False, True):
            for d in dirs:   # straight
                if in_mine((ex + d[0], ey + d[1])): continue
                r = into((ex, ey), d)
                if r and (not best or r[0] < best[0]): best = (r[0], [r[1]])
            if not best:   # one L: out along d1 for a px, then toward the room along a perpendicular
                for d1 in dirs:
                    for a in range(3, 120):
                        q = (ex + d1[0] * a, ey + d1[1] * a)
                        if not free(q) or q in own or in_mine(q): break
                        for d2 in ((d1[1], d1[0]), (-d1[1], -d1[0])):
                            r = into(q, d2)
                            if r and (not best or a + r[0] + 8 < best[0]): best = (a + r[0] + 8, [r[1], q])
            if best: break
        if best: e['zoom'] = [list(p) for p in best[1]]


def _job(args):
    pl, floor, lang = args
    shapes = json.loads((ROOT / 'data/room_shapes.json').read_text())['floors']
    rects = next(f['rooms'] for f in shapes if (f['pl'], f['floor']) == (pl, floor))
    rows = [(i, r[2], r[4]) for i, r in enumerate(header_rows(ROOT / f'src/room_names-{lang}.h')) if (r[0], r[1]) == (pl, floor)]
    return pl, floor, lang, floor_layout(pl, floor, rects, rows, markers().get((pl, floor), set()), lang)


def zoom_only():
    """Recompute only the 2x leaders of data/sd-layout.json (seconds)."""
    path = ROOT / 'data/sd-layout.json'
    layout = json.loads(path.read_text())
    shapes = json.loads((ROOT / 'data/room_shapes.json').read_text())['floors']
    for lang in ('en', 'ko'):
        hr = header_rows(ROOT / f'src/room_names-{lang}.h')
        for key, rooms in layout.items():
            pl, floor = (int(v) for v in key.split(','))
            rects = next(f['rooms'] for f in shapes if (f['pl'], f['floor']) == (pl, floor))
            rows = [(i, r[2], r[4]) for i, r in enumerate(hr) if (r[0], r[1]) == (pl, floor)]
            ents = {int(j): o[lang] for j, o in rooms.items() if lang in o}
            add_zoom_leaders(pl, floor, rects, rows, ents)
    path.write_text(json.dumps(layout, ensure_ascii=False, indent=0, sort_keys=True) + '\n')


def main():
    from concurrent.futures import ProcessPoolExecutor
    shapes = json.loads((ROOT / 'data/room_shapes.json').read_text())['floors']
    keys = sorted({(r[0], r[1]) for r in header_rows(ROOT / 'src/room_names-en.h')})
    only = {tuple(int(v) for v in a.split(',')) for a in sys.argv[1:]}
    path = ROOT / 'data/sd-layout.json'
    result = json.loads(path.read_text()) if path.exists() and only else {}
    jobs = [(pl, f, l) for l in ('en', 'ko') for pl, f in keys if not only or (pl, f) in only]
    with ProcessPoolExecutor() as pool:
        for pl, f, lang, out in pool.map(_job, jobs):
            for i, o in out.items(): result.setdefault(f'{pl},{f}', {}).setdefault(str(i), {})[lang] = o
    path.write_text(json.dumps(result, ensure_ascii=False, indent=0, sort_keys=True) + '\n')


if __name__ == '__main__':
    zoom_only() if sys.argv[1:] == ['--zoom'] else main()
