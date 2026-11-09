"""Generate Korean key-item labels for items.h (run extract_items.py first); requires Pillow."""
from pathlib import Path
import hashlib, re
from PIL import Image, ImageDraw, ImageFont
from extract_items import NAMES
import marker_names
import category_colors
from category_colors import KEY, LOCK, PUZZLE, DOCUMENT, COMMON

R = Path(__file__).resolve().parent
FONT = Path(__file__).resolve().parent / 'fonts/Pretendard-SemiBold.otf'  # open font only (release rule 2026-10-26)
OUTLINE = (8, 8, 8)
DOT = category_colors.NAME_RGB[KEY]  # the 4x4 opaque texel block at each page's corner; no name uses it
MARKER = 4  # texels (0,0)-(3,3) of every page are the opaque map dot
FONT_PX, STROKE = 24, 2
LANG = 'ko'  # regen.py sets 'en' for the English pass
# Korean 'A의 B' names drop the particle unless the stem is one syllable or listed here (RE0 HD map mod rule;
# no RE2 key-item name has one today).
KEEP_UI = ()
COMMON_ITEMS = {20, 21, 22, 24, 25, 26, 27, 29, 30, 35, 38, 39, 40}  # re2_keymap.c common_item
AREA_MAPS = range(200, 206)  # re2_keymap.c map_item


def display_lines(name, official=False):
    """RE0 HD map mod wrapping: a name of 8+ characters breaks at the space nearest its middle; words never split, and
    a leading [Z] tag counts as part of the first word.
    Each line is its own raster so the runtime can align it toward the marker."""
    if name not in KEEP_UI and not official:  # official = a document name as the game shows it in its Files list
        name = re.sub(r'(\S{2,})의 ', r'\1 ', name)
    tag = len('[Z] ') if name.startswith('[Z] ') else 0  # the zapping tag stays with the first word
    spaces = [i for i, c in enumerate(name) if c == ' ' and i >= tag]
    if len(name) < 8 or not spaces:
        return [name]
    cut = min(spaces, key=lambda i: abs(i - len(name) / 2))
    return [name[:cut], name[cut + 1:]]


def item_ids():
    body = (R / 'items.h').read_text().split('map_items[] = {', 1)[1]
    # MapItem rows: pl,floor,x,y,seen,item,bank,bit,guard_start,guard_count
    return sorted({int(row.split(',')[5]) for row in re.findall(r'^\{([^}]*)\},$', body, re.M)})


def marker_name_ids():
    """Documents and puzzles that overlay_data.h draws, and their names (data/marker_names.json): {id: (key, text)}."""
    body = (R / 'overlay_data.h').read_text()
    docs = {int(r.split(',')[4]) for r in re.findall(r'^\{([^}]*)\},$', body.split('map_documents[] = {', 1)[1].split('};', 1)[0], re.M)}
    inter = body.split('map_interactions[] = {', 1)[1].split('};', 1)[0]
    puzzles = {int(r.split(',')[8]) for r in re.findall(r'^\{([^}]*)\},$', inter, re.M) if int(r.split(',')[8])}
    col = 0 if LANG == 'en' else 1
    names = {i: ('Doc%d' % i, marker_names.DOCUMENTS[i][col]) for i in docs}
    names.update({i: ('Puzzle%d' % i, marker_names.PUZZLES[i][col]) for i in puzzles})
    return names


def door_keys():
    """Item ids that name a lock (doors-all.h, Door.key)."""
    body = (R / 'doors-all.h').read_text().split('doors[]=', 1)[1]
    return {int(r.split(',')[6]) for r in re.findall(r'^\{([^}]*)\},$', body, re.M)}


def label_entries(names):
    """[(item, category)] sorted so an item's own category comes first: pickups by kind, locks, puzzles, documents."""
    entries = {(i, DOCUMENT if i in AREA_MAPS else COMMON if i in COMMON_ITEMS else KEY) for i in item_ids()}
    entries |= {(i, LOCK) for i in door_keys() if i in names}
    entries |= {(i, DOCUMENT if key.startswith('Doc') else PUZZLE) for i, (key, _) in marker_name_ids().items()}
    return sorted(entries)


def new_page():
    page = Image.new('RGB', (256, 256))
    page.paste(DOT, (0, 0, MARKER, MARKER))
    return page


def raster_labels(entries, names):
    font = ImageFont.truetype(str(FONT), FONT_PX)
    pages, defs = [new_page()], []
    x, y, row_h = MARKER + 2, 1, MARKER
    for (item, cat), name in (((item, cat), line) for item, cat in entries
                              for line in display_lines(names[item][1], official=(cat == DOCUMENT and names[item][0].startswith('Doc')) or item in marker_names.ITEMS_KO)):
        box = font.getbbox(name, stroke_width=STROKE)
        w, h = box[2] - box[0] + 2, box[3] - box[1] + 2
        w += w % 2; h += h % 2
        assert 0 < w < 255 and 0 < h < 255
        if x + w + 1 > 256:
            x, y, row_h = 1, y + row_h + 2, 0
        if y + h + 1 > 256:
            pages.append(new_page())
            x, y, row_h = MARKER + 2, 1, MARKER
        tile = Image.new('RGB', (w, h))
        ImageDraw.Draw(tile).text((1 - box[0], 1 - box[1]), name, font=font,
                                 fill=category_colors.NAME_RGB[cat], stroke_width=STROKE, stroke_fill=OUTLINE)
        pages[-1].paste(tile, (x, y))
        defs.append(dict(item=item, cat=cat, page=len(pages) - 1, u=x, v=y, w=w, h=h, text=name))
        x += w + 2; row_h = max(row_h, h)
    return pages, defs


def check(pages, defs, entries):
    assert [(d['item'], d['cat']) for d in dict(((d['item'], d['cat']), d) for d in defs).values()] == entries
    keys = [(d['item'], d['cat']) for d in defs]  # a wrapped name is two consecutive rows of one (item, category)
    assert all(keys.count(k) <= 2 and (keys.count(k) == 1 or keys.index(k) + 1 == len(keys) - keys[::-1].index(k) - 1) for k in keys)
    for d in defs:
        assert d['u'] + d['w'] <= 256 and d['v'] + d['h'] <= 256, d
        assert d['u'] >= MARKER or d['v'] >= MARKER, ('label overlaps marker', d)
    for a in defs:
        for b in defs:
            if a is not b and a['page'] == b['page']:
                assert (a['u'] + a['w'] <= b['u'] or b['u'] + b['w'] <= a['u'] or
                        a['v'] + a['h'] <= b['v'] or b['v'] + b['h'] <= a['v']), (a, b)
    for page in pages:
        assert all(page.getpixel((u, v)) == DOT for u in range(MARKER) for v in range(MARKER))


def rgb555(page):
    return [(r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10) for r, g, b in page.getdata()]


def generate():
    names = {**NAMES, **marker_name_ids()}
    names.update({i: (names[i][0], ('[Z] ' if names[i][1].startswith('[Z] ') else '') + ko) for i, ko in marker_names.ITEMS_KO.items() if i in names} if LANG == 'ko' else {})
    entries = label_entries(names)
    missing = [i for i, _ in entries if i not in names]
    assert not missing, missing
    pages, defs = raster_labels(entries, names)
    check(pages, defs, entries)
    header = ['/* Generated by generate_item_labels.py from items.h + extract_items.NAMES.',
              f'   Font {FONT.name} sha256 {hashlib.sha256(FONT.read_bytes()).hexdigest()}.',
              '   RGB555: zero transparent; texels (0,0)-(3,3) of each page are the opaque marker dot; draw labels at quarter size. */',
              '#ifndef RE2_ITEM_LABELS_H', '#define RE2_ITEM_LABELS_H',
              'typedef struct { unsigned char item,page,u,v,w,h,cat; } ItemLabel; /* cat: 0 key 1 lock 2 puzzle 3 document/area map 4 common; a wrapped name: its second line is the next entry, same item and cat */',
              f'#define ITEM_LABEL_PAGE_COUNT {len(pages)}', f'#define ITEM_LABEL_COUNT {len(defs)}',
              'static const ItemLabel item_labels[ITEM_LABEL_COUNT]={']
    header += ['{%d,%d,%d,%d,%d,%d,%d}, /* %s %s */' % (d['item'], d['page'], d['u'], d['v'], d['w'], d['h'], d['cat'],
                                                     names[d['item']][0], d['text']) for d in defs]
    header += ['};', 'static const unsigned short item_label_pixels[ITEM_LABEL_PAGE_COUNT][65536]={']
    for page in pages:
        pixels = rgb555(page)
        assert all(pixels[v * 256 + u] for u in range(MARKER) for v in range(MARKER))
        header.append('{' + ','.join(hex(p) for p in pixels) + '},')
    (R / 'item_labels.h').write_text('\n'.join(header + ['};', '#endif', '']))
    cols = 4
    preview = Image.new('RGB', (cols * 160, ((len(defs) + cols - 1) // cols) * 32), (28, 32, 35))
    for i, d in enumerate(defs):
        px, py = i % cols * 160 + 4, i // cols * 32 + 4
        page = pages[d['page']]
        preview.paste(page.crop((0, 0, MARKER, MARKER)), (px, py + 10))
        preview.paste(page.crop((d['u'], d['v'], d['u'] + d['w'], d['v'] + d['h'])), (px + 8, py))
    preview.save(R / 'item_labels-preview.png')
    print(f'{len(defs)} item labels, {len(pages)} pages')


if __name__ == '__main__':
    generate()
