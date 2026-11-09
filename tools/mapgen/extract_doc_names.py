#!/usr/bin/env python3
"""English document names (the Files list) from the game's own item-name table, for item ids 104..128.

Resident Evil 2.exe keeps item names as strings in the game's font encoding: byte + 36 is the ASCII code (0x00 = space,
0x0c.. = digits), capitals are plain bytes (0x1d = A) and '^' is the apostrophe glyph and '_' the dash glyph.
The English strings start at file offset 0x12eb98 (VA 0x52eb98), each ends with 0xf7, and the n-th string is the name of item
id n (1 Knife, 100 'no item', 104 CHRIS's diary ... 128 Rookie files). The Japanese-code table the game uses for the
Korean HD patch's glyph pages is at VA 0x52e580 with word offsets at VA 0x52ea80 (getter 0x4c9909 adds the base, an alternate
name offset table at VA 0x52eb82 is used when the item record's flag, byte 0x53de29 + id*8, is set).
  RE2_GAME=<game dir> python extract_doc_names.py           # check data/marker_names.json
  RE2_GAME=<game dir> python extract_doc_names.py --dump"""
from pathlib import Path
import hashlib, json, os, sys

HERE = Path(__file__).resolve().parent
EXE_SHA = '21b2a647cbeddac1ec389be847f22a434a0264a18020589de91cb2824dcb1bf5'
TABLE_START = 0x12eb98  # file offset; VA 0x52eb98 (section .data VA 0x51a000 = file 0x11a000)
TERMINATOR = 0xf7
IDS = range(104, 129)


def decode(raw):
    """Game font bytes -> text: byte + 36 is ASCII, 0 is a space; '^' is drawn as an apostrophe, '_' as a dash."""
    return ''.join(' ' if b == 0 else chr(b + 36) for b in raw).replace('^', "'").replace('_', '-')


def entries(blob):
    """[(file offset, bytes)] of the 0xf7-terminated strings; the list index is the item id."""
    out, pos = [], TABLE_START
    while len(out) <= 128:
        end = blob.index(TERMINATOR, pos)
        out.append((pos, blob[pos:end])); pos = end + 1
    return out


def current(game):
    blob = (Path(game) / 'Resident Evil 2.exe').read_bytes()
    assert hashlib.sha256(blob).hexdigest() == EXE_SHA, 'different executable'
    rows = entries(blob)
    assert decode(rows[1][1]) == 'Knife' and decode(rows[100][1]) == 'no item', 'item-name table moved'
    return {i: dict(name=decode(rows[i][1]), offset=hex(rows[i][0]), va=hex(rows[i][0] + 0x51a000 - 0x11a000),
                    sha256=hashlib.sha256(rows[i][1]).hexdigest()) for i in IDS}


if __name__ == '__main__':
    found = current(os.environ['RE2_GAME'])
    if '--dump' in sys.argv:
        print(json.dumps(found, indent=1)); sys.exit(0)
    table = json.loads(next(p for p in (HERE / 'marker_names.json', HERE.parents[1] / 'data/marker_names.json') if p.is_file()).read_text())
    for i, d in table['documents'].items():
        src = d['en_source']
        assert d['en'] == found[int(i)]['name'] and src['offset'] == found[int(i)]['offset'] and src['sha256'] == found[int(i)]['sha256'], (i, src, found[int(i)])
    print(f'{len(table["documents"])} document names match the game EXE item-name table')
