#!/usr/bin/env python3
"""Korean document names (the Files list) from the Korean HD patch, for item ids 106..126.

korean.asi applies korean_hd.bin ('KRP1') to the game in memory. Besides code patches, the file carries a Korean item-name
table: records `03 01 <u32 table offset> <u32 length> <bytes>`, offsets contiguous from 0x800, each string ends with 0xf7,
and the n-th record is the name of item id n (the entry at 0x800 is id 1). Characters are bytes: 0x00 space, 0x0c.. digits
and 0x1d.. letters (byte + 36 = ASCII), and glyph pairs `f1 xx` = cell xx and `f2 xx` = cell 252 + xx of the Korean page
Common/Data/fontk1.adt (page 39 in korean_rebirth.txt's G lines), `f3 xx` = cell xx of the shared rows of
Common/Data/font1..7.adt (page 9). A cell is 14 x 14 px, 18 per row, from the top of the page. Cell -> syllable readings are
in data/marker_names.json `ko_glyphs` (basis: the patch's own G table in korean_rebirth.txt, a user-confirmed name, or read
by eye from the cell: see local/marker-names-*/c7/documents-ko-review.png).
  RE2_GAME=<game dir> python extract_ko_doc_names.py           # check data/marker_names.json
  RE2_GAME=<game dir> python extract_ko_doc_names.py --dump"""
from pathlib import Path
import hashlib, json, os, struct, sys

HERE = Path(__file__).resolve().parent
IDS = range(106, 127)
SPECIAL = {0xf1: 0, 0xf2: 252}


def entries(blob):
    """{item id: (file offset of the record, table offset, bytes)}"""
    found = {}
    for p in range(len(blob) - 10):
        if blob[p] == 3 and blob[p + 1] == 1:
            off, ln = struct.unpack_from('<II', blob, p + 2)
            if 0 < ln < 80 and off < 0x4000 and p + 10 + ln <= len(blob) and blob[p + 9 + ln] == 0xf7 and off not in found:
                found[off] = (p, blob[p + 10:p + 10 + ln])
    offs = sorted(found)
    assert offs[0] == 0x800 and all(found[o][0] and o + len(found[o][1]) == n for o, n in zip(offs, offs[1:])), 'name table is not contiguous'
    return {i + 1: (found[o][0], o, found[o][1]) for i, o in enumerate(offs)}


def tokens(raw):
    out, i = [], 0
    while i < len(raw) - 1:
        if raw[i] in (0xf1, 0xf2, 0xf3):
            out.append(('p9' if raw[i] == 0xf3 else 'p39', raw[i + 1] + SPECIAL.get(raw[i], 0))); i += 2
        else:
            out.append(('c', raw[i])); i += 1
    return out


def decode(raw, glyphs):
    text = ''
    for kind, v in tokens(raw):
        if kind == 'c': text += ' ' if v == 0 else '.' if v == 1 else chr(v + 36).replace('_', '-')
        else: text += glyphs[f'{kind[1:]}:{v}']['syl']
    return text


def current_items(game, glyphs, ids):
    rows = entries((Path(game) / 'korean_hd.bin').read_bytes())
    return {i: dict(name=decode(rows[i][2], glyphs), record_offset=hex(rows[i][0]), sha256=hashlib.sha256(rows[i][2]).hexdigest()) for i in ids}


def current(game, glyphs):
    game = Path(game)
    blob = (game / 'korean_hd.bin').read_bytes()
    rows = entries(blob)
    return {i: dict(name=decode(rows[i][2], glyphs), record_offset=hex(rows[i][0]), table_offset=hex(rows[i][1]),
                    bytes=rows[i][2].hex(), sha256=hashlib.sha256(rows[i][2]).hexdigest()) for i in IDS}


if __name__ == '__main__':
    table = json.loads(next(p for p in (HERE / 'marker_names.json', HERE.parents[1] / 'data/marker_names.json') if p.is_file()).read_text())
    game = Path(os.environ['RE2_GAME'])
    glyphs = dict(table['ko_glyphs'])
    for line in (game / 'korean_rebirth.txt').read_text(encoding='utf-8').splitlines():  # the patch's own glyph table must agree
        f = line.split('\t')
        if f[0] == 'G':
            key = f'{f[2]}:{f[3]}'
            assert glyphs.setdefault(key, dict(syl=f[1]))['syl'] == f[1], line
    found = current(game, glyphs)
    if '--dump' in sys.argv:
        print(json.dumps(found, ensure_ascii=False, indent=1)); sys.exit(0)
    for i, d in table['documents'].items():
        src = d['ko_source']
        assert d['ko'] == found[int(i)]['name'] and src['sha256'] == found[int(i)]['sha256'] and src['record_offset'] == found[int(i)]['record_offset'], (i, d['ko'], found[int(i)])
    items = current_items(game, glyphs, map(int, table['item_names_ko']))
    for i, d in table['item_names_ko'].items():
        assert d['ko'] == items[int(i)]['name'] and d['source']['sha256'] == items[int(i)]['sha256'] and d['source']['record_offset'] == items[int(i)]['record_offset'], (i, d['ko'], items[int(i)])
    print(f'{len(table["documents"])} Korean document names and {len(items)} item names match korean_hd.bin')
