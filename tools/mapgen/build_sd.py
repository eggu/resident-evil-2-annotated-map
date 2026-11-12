"""SD atlas (Classic REbirth without the HD pack; user decisions 2026-11-12) -> src/sd_assets.h.

1:1 sprites in 256x256 RGB555 pages like the HD pages (zero = transparent, black stored as 0x421): 9x9 markers (enemies 5x5),
the approved lock table, Galmuri9 room names (cream, 1 px black shadow) placed by tools/mapgen/sd_layout.py, the legend.
Page groups: shared (markers, legend), English names, Korean names, so one language stays resident at a time (texture
handle budget, see re2_keymap.c cached_texture)."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import ImageDraw, ImageFont, Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sd_icons, category_colors as cc
from sd_layout import header_rows, ink

FONT = ImageFont.truetype(str(ROOT / 'fonts/Galmuri9.ttf'), 10)
LINE_H = 11
CREAM, SHADOW, OFF, WHITE = (255, 240, 200), (8, 8, 8), cc.OFF, (255, 255, 255)
PAGE = 256

LEGEND = {  # row -> (colour, English, Korean); on rows use the colour, off rows the grey
    'all': (WHITE, '[0] ALL', '[0] 전체'), 'rooms': (cc.ROOMS, '[1] ROOMS', '[1] 방 이름'), 'locks': (cc.NAME_RGB[cc.LOCK], '[2] LOCKS', '[2] 잠긴 문'),
    'key': (cc.NAME_RGB[cc.KEY], '[3] KEY ITEMS', '[3] 핵심 아이템'), 'docs': (cc.NAME_RGB[cc.DOCUMENT], '[4] FILES & MAPS', '[4] 문서·지도'),
    'puzzles': (cc.NAME_RGB[cc.PUZZLE], '[5] PUZZLES', '[5] 퍼즐'), 'events': (cc.NAME_RGB[cc.EVENT], '[6] EVENTS', '[6] 이벤트'),
    'common': (cc.NAME_RGB[cc.COMMON], '[7] ITEMS', '[7] 일반 아이템'), 'enemies': (cc.MONSTERS, '[8] ENEMIES', '[8] 적')}
SCOPE = (('[9] VISITED', '[9] REVEALED', '[9] ALL ROOMS'), ('[9] 방문 방', '[9] 공개 방', '[9] 전체 방'))
LANG = ('[\\] LANGUAGE: ENGLISH', '[\\] 언어: 한국어')   # indexed by Korean (0 English, 1 Korean)
ZOOM = (('[Action] Zoom: 1x', '[Action] Zoom: 2x'), ('[결정] 확대: 1배', '[결정] 확대: 2배'))
TITLE, HIDE, FOLD = ('Map Notes', '지도 메모'), ('[~] Hide', '[~] 숨김'), ('[~] Legend', '[~] 범례')


def pack555(rgba):
    r, g, b = (rgba[..., i].astype(np.uint16) >> 3 for i in range(3))
    v = r | g << 5 | b << 10
    v = np.where(v == 0, 0x421, v)
    return np.where(rgba[..., 3] > 0, v, 0).astype(np.uint16)


def text_image(text, colour):
    """Name or legend sprite: the ink box of sd_layout.ink() plus a 1 px black shadow down-right."""
    g = ink(text)
    a = np.zeros((g.shape[0] + 1, g.shape[1] + 1, 4), np.uint8)
    sh = np.zeros(a.shape[:2], bool)
    sh[1:, 1:] = g
    a[sh] = SHADOW + (255,)
    a[:-1, :-1][g] = colour + (255,)
    return a


class Packer:
    """Shelf packer; sprites keep u + w < 256 and v + h < 256 (8-bit texture coordinates)."""
    def __init__(self): self.pages, self.x, self.y, self.h = [np.zeros((PAGE, PAGE), np.uint16)], 0, 0, 0
    def place(self, a):
        h, w = a.shape[:2]
        if self.x + w > PAGE - 1: self.x, self.y, self.h = 0, self.y + self.h + 1, 0
        if self.y + h > PAGE - 1: self.pages.append(np.zeros((PAGE, PAGE), np.uint16)); self.x = self.y = self.h = 0
        pg = len(self.pages) - 1
        self.pages[pg][self.y : self.y + h, self.x : self.x + w] = pack555(a)
        r = (pg, self.x, self.y, w, h); self.x += w + 1; self.h = max(self.h, h)
        return r


def main():
    layout = json.loads((ROOT / 'data/sd-layout.json').read_text())
    groups = {g: Packer() for g in range(4)}   # markers, English names, Korean names, legend (both languages)
    sprites, index = [], {}   # (group, array)
    def add(key, a, group=0):   # group: 0 markers, 1 English names, 2 Korean names, 3 legend
        if key not in index: index[key] = len(sprites); sprites.append((group, a))
        return index[key]
    for k in sd_icons.ICONS: add(('icon', k), sd_icons.icon_image(k))
    for it in sd_icons.LOCKS: add(('lock', sd_icons.lock(*sd_icons.LOCKS[it])), sd_icons.lock_image(it))
    add(('leader',), np.tile(np.array(CREAM + (255,), np.uint8), (4, 4, 1)))
    for lang in (0, 1):
        for r, (col, en, ko) in LEGEND.items():
            for on in (0, 1): add(('legend', lang, r, on), text_image((en, ko)[lang], col if on else OFF), 3)
        for s in range(3): add(('scope', lang, s), text_image(SCOPE[lang][s], WHITE), 3)
        add(('lang', lang), text_image(LANG[lang], WHITE), 3)
        for z in (0, 1): add(('zoom', lang, z), text_image(ZOOM[lang][z], WHITE), 3)
        add(('title', lang), text_image(TITLE[lang], WHITE), 3); add(('hide', lang), text_image(HIDE[lang], WHITE), 3); add(('fold', lang), text_image(FOLD[lang], WHITE), 3)
    rooms = {}
    for li, lang in enumerate(('en', 'ko')):
        rows = header_rows(ROOT / f'src/room_names-{lang}.h')
        table = []
        for j, (pl, floor, seen, code, name) in enumerate(rows):
            o = layout.get(f'{pl},{floor}', {}).get(str(j), {}).get(lang)
            if not o: table.append(None); continue
            table.append((add(('room', lang, o['text']), text_image(o['text'], CREAM), 1 + li), o))
        rooms[lang] = table
    # pack: shared group first, then each language; tallest first within a group
    rects = [None] * len(sprites)
    for g in range(4):
        for i in sorted((i for i, s in enumerate(sprites) if s[0] == g), key=lambda i: (-sprites[i][1].shape[0], -sprites[i][1].shape[1])):
            rects[i] = groups[g].place(sprites[i][1])
    pages, page_lang, base = [], [], {}
    for g in range(4):
        base[g] = len(pages); pages += groups[g].pages; page_lang += [g] * len(groups[g].pages)
    sid = lambda key: index[key]
    L = ['/* generated by tools/mapgen/build_sd.py from data/sd-layout.json: the SD atlas (no HD pack). Do not edit. */',
         '#ifndef RE2_SD_ASSETS_H', '#define RE2_SD_ASSETS_H',
         f'#define SD_PAGES {len(pages)}',
         'static const unsigned char sd_page_lang[SD_PAGES] = {' + ','.join(map(str, page_lang)) + '}; /* 0 markers, 1 English names, 2 Korean names, 3 legend */',
         'typedef struct { unsigned char page,u,v,w,h; } SdSprite;',
         'static const SdSprite sd_sprites[] = {' + ','.join('{%d,%d,%d,%d,%d}' % (base[sprites[i][0]] + r[0], r[1], r[2], r[3], r[4]) for i, r in enumerate(rects)) + '};']
    for k in sd_icons.ICONS: L.append(f'#define SD_{k.upper()} {sid(("icon", k))}')
    L += [f'#define SD_LEADER {sid(("leader",))}']
    lock = ['0xFFFF'] * 100
    for it in sd_icons.LOCKS: lock[it] = str(sid(('lock', sd_icons.lock(*sd_icons.LOCKS[it]))))
    com = ['0xFFFF'] * 41
    for it, k in sd_icons.COMMON.items(): com[it] = str(sid(('icon', k)))
    L.append('static const unsigned short sd_lock_sprite[100] = {' + ','.join(lock) + '}; /* key item id -> lock marker */')
    L.append('static const unsigned short sd_common_sprite[41] = {' + ','.join(com) + '}; /* common item id -> marker */')
    L.append('typedef struct { unsigned short sprite; short x,y; unsigned char n; short pt[6]; } SdRoom; /* x,y name top-left; n leader points (start inside the room, last 1 px from the name); sprite 0xFFFF none */')
    for lang in ('en', 'ko'):
        out = []
        for t in rooms[lang]:
            if not t: out.append('{0xFFFF,0,0,0,{0}}'); continue
            sp, o = t
            pts = [v for p in o['leader'][:3] for v in p] if not o['forced'] else []
            out.append('{%d,%d,%d,%d,{%s}}' % (sp, o['x'], o['y'], len(pts) // 2, ','.join(map(str, pts + [0] * (6 - len(pts))))))
        L.append(f'static const SdRoom sd_rooms_{lang}[] = {{' + ',\n'.join(out) + '};')
    L.append('static const unsigned short sd_legend[2][9][2] = {' + ','.join('{' + ','.join('{%d,%d}' % (sid(('legend', l, r, 0)), sid(('legend', l, r, 1))) for r in LEGEND) + '}' for l in (0, 1)) + '};')
    L.append('static const unsigned short sd_scope[2][3] = {' + ','.join('{%s}' % ','.join(str(sid(('scope', l, s))) for s in range(3)) for l in (0, 1)) + '};')
    L.append('static const unsigned short sd_zoom[2][2] = {' + ','.join('{%d,%d}' % (sid(('zoom', l, 0)), sid(('zoom', l, 1))) for l in (0, 1)) + '};')
    for k in ('lang', 'title', 'hide', 'fold'): L.append(f'static const unsigned short sd_{k}[2] = {{{sid((k, 0))},{sid((k, 1))}}};')
    L.append('static const unsigned short sd_pixels[SD_PAGES][65536] = {')
    for pg in pages: L.append('{' + ','.join(hex(v) for v in pg.ravel().tolist()) + '},')
    L += ['};', '#endif', '']
    (ROOT / 'src/sd_assets.h').write_text('\n'.join(L))
    (ROOT / 'build').mkdir(exist_ok=True)
    for i, pg in enumerate(pages):
        rgb = np.stack([((pg >> s) & 31) << 3 for s in (0, 5, 10)], -1).astype(np.uint8)
        rgb[pg == 0] = (30, 34, 44)
        Image.fromarray(rgb).resize((PAGE * 2, PAGE * 2), Image.NEAREST).save(ROOT / f'build/sd-page{i}.png')
    print(f'{len(pages)} SD pages, {len(sprites)} sprites, rooms {[sum(t is not None for t in rooms[l]) for l in rooms]}')


if __name__ == '__main__':
    main()
