#!/usr/bin/env python3
"""Document (file) titles: bitmap hashes of page 2 of Common/file/fileNN.bin (installed Korean HD patch) and fileNNu.bin (English).

Each fileNN.bin is an offset table (32 dwords) followed by compressed TIM pages at 0x80 + offset; the game's own
decompressor (EXE 0x43c390, decode_maps.decode) unpacks them. Page 2 is a 4bpp 256x256 TIM whose only content is the title.
File NN = item id - 104 (EXE 0x4fa864 adds 0x68 to the file slot for the item/name). Titles are read from the bitmaps by eye;
this tool only proves that data/marker_names.json still describes the bitmaps of the game install.
  RE2_GAME=<game dir> python extract_file_titles.py           # check data/marker_names.json
  RE2_GAME=<game dir> python extract_file_titles.py --dump    # print the current table rows"""
from pathlib import Path
import hashlib, json, os, struct, sys

HERE = Path(__file__).resolve().parent
G = Path(os.environ['RE2_GAME'])
TITLE_PAGE = 2


def bitmap(path):
    """(w, h, palette-index bytes) of the title's bounding box on page 2."""
    import decode_maps
    raw = path.read_bytes()
    offsets = struct.unpack_from('<32I', raw, 0)
    page = decode_maps.decode(raw[0x80 + offsets[TITLE_PAGE]:])
    clut = struct.unpack_from('<I', page, 8)[0]
    p = 8 + clut
    _, _, _, iw, ih = struct.unpack_from('<IHHHH', page, p)
    assert (iw, ih) == (64, 256), (path.name, iw, ih)
    pixels = []
    for b in page[p + 12:p + 12 + iw * 2 * ih]:
        pixels += [b & 15, b >> 4]
    width = iw * 4
    rows = [pixels[y * width:(y + 1) * width] for y in range(ih)]
    ys = [y for y, r in enumerate(rows) if any(r)]
    xs = [x for x in range(width) if any(r[x] for r in rows)]
    x0, x1, y0, y1 = xs[0], xs[-1] + 1, ys[0], ys[-1] + 1
    return x1 - x0, y1 - y0, bytes(v for r in rows[y0:y1] for v in r[x0:x1])


def digest(path):
    w, h, data = bitmap(path)
    return dict(w=w, h=h, sha256=hashlib.sha256(bytes([w, h]) + data).hexdigest())


def current(ids):
    out = {}
    for item in ids:
        stem = f'file{item - 104:02x}'
        folder = G / 'Common/file'
        out[item] = dict(file=stem, ko=digest(folder / f'{stem}.bin'), en=digest(folder / f'{stem}u.bin'))
    return out


if __name__ == '__main__':
    sys.path.insert(0, str(HERE))
    table = json.loads(next(p for p in (HERE / 'marker_names.json', HERE.parents[1] / 'data/marker_names.json') if p.is_file()).read_text())
    docs = table['documents']
    found = current(int(i) for i in docs)
    if '--dump' in sys.argv:
        print(json.dumps(found, indent=1))
        sys.exit(0)
    bad = [i for i, d in docs.items()
           if d['file'] != found[int(i)]['file'] or d['bitmap']['ko'] != found[int(i)]['ko'] or d['bitmap']['en'] != found[int(i)]['en']]
    assert not bad, f'title bitmaps differ from data/marker_names.json: {bad}'
    print(f'{len(docs)} document title bitmaps match the game files')
