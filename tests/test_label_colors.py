"""Every marker name is drawn in its own category colour, the one of its legend row (tools/mapgen/category_colors.py),
checked over all item_labels rows of both languages and both legend languages. Stdlib only; run from the repository root."""
import json, re, sys, unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools/mapgen'))
import category_colors as cc

OUTLINE = 0x421
COMMON_ITEMS = {20, 21, 22, 24, 25, 26, 27, 29, 30, 35, 38, 39, 40}  # re2_keymap.c common_item
LEGEND_ROW = {'[2]': cc.LOCK, '[3]': cc.KEY, '[4]': cc.DOCUMENT, '[5]': cc.PUZZLE, '[6]': cc.EVENT, '[7]': cc.COMMON}  # renumbered 2026-11-08


def rgb555(rgb):
    return (rgb[0] >> 3) | ((rgb[1] >> 3) << 5) | ((rgb[2] >> 3) << 10)


def pixels(text, name):
    body = text.split(name, 1)[1].split('={', 1)[1].split('};', 1)[0]
    return [int(v, 0) for v in re.findall(r'0x[0-9a-fA-F]+|\d+', body)]


def fill(px, page, u, v, w, h):
    """The label's fill: its most common bright texel (anti-aliased outline edges are dark, the fill is the brightest solid colour)."""
    return Counter(c for j in range(h) for i in range(w)
                   if (c := px[page * 65536 + (v + j) * 256 + u + i]) not in (0, OUTLINE) and max(c & 31, c >> 5 & 31, c >> 10) >= 8
                   ).most_common(1)[0][0]


def item_rows(lang):
    text = (ROOT / f'src/item_labels-{lang}.h').read_text()
    rows = [tuple(int(x) for x in m) for m in re.findall(r'^\{(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\},', text, re.M)]
    return rows, pixels(text, f'item_label_pixels_{lang.upper()}')


class LabelColors(unittest.TestCase):
    def test_categories_have_distinct_colours(self):
        values = [rgb555(c) for c in cc.NAME_RGB.values()]
        self.assertEqual(len(set(values)), 6)
        self.assertEqual(cc.NAME_RGB[cc.COMMON], (184, 188, 196))  # cool grey #B8BCC4 (user 2026-11-08)
        self.assertEqual(cc.NAME_RGB[cc.EVENT], (176, 112, 255))
        self.assertEqual(cc.OFF, (106, 106, 106))  # disabled legend rows, #6A6A6A
        self.assertEqual(rgb555(cc.NAME_RGB[cc.COMMON]), 23 | 23 << 5 | 24 << 10)

    def test_every_item_name_has_its_category_colour(self):
        for lang in ('ko', 'en'):
            rows, px = item_rows(lang)
            self.assertGreater(len(rows), 100)
            seen = Counter()
            for item, page, u, v, w, h, cat in rows:
                self.assertEqual(fill(px, page, u, v, w, h), rgb555(cc.NAME_RGB[cat]), (lang, item, cat))
                seen[cat] += 1
            self.assertEqual(set(seen), set(range(5)), lang)  # events carry no names

    def test_category_matches_the_marker_it_names(self):
        doors = (ROOT / 'src/doors-all.h').read_text().split('doors[]=', 1)[1]
        lock_keys = {int(r.split(',')[6]) for r in re.findall(r'^\{([^}]*)\},$', doors, re.M)}
        puzzles = set(map(int, json.loads((ROOT / 'data/marker_names.json').read_text())['puzzle_names']))
        for lang in ('ko', 'en'):
            for item, *_, cat in item_rows(lang)[0]:
                if cat == cc.COMMON: self.assertIn(item, COMMON_ITEMS)
                if cat == cc.LOCK: self.assertIn(item, lock_keys)
                if cat == cc.PUZZLE: self.assertIn(item, puzzles)
                if cat == cc.DOCUMENT: self.assertTrue(106 <= item <= 126 or 200 <= item <= 205, item)
                if cat == cc.KEY: self.assertFalse(item in COMMON_ITEMS or 200 <= item <= 205 or item in puzzles, item)

    def test_legend_rows_use_the_same_colours(self):
        for fixtures, provenance in (('tests/fixtures', 'tests/fixtures/room_names-provenance.json'),
                                     ('tests/fixtures/korean-assets', 'tests/fixtures/korean-assets/room_names-provenance.json')):
            text = (ROOT / fixtures / 'room_labels.h').read_text()
            first = int(re.search(r'ROOM_HELP_LABEL (\d+)', text)[1])
            rows = [tuple(int(x) for x in m) for m in re.findall(r'\{(\d+),(\d+),(\d+),(\d+),(\d+)\}', text.split('room_labels[]=', 1)[1].split('};', 1)[0])]
            px = pixels(text, 'room_label_pixels')
            labels = json.loads((ROOT / provenance).read_text())['labels']
            checked = set()
            for n, label in enumerate(labels[first:], first):
                key = label['text'][:3]
                if key in LEGEND_ROW and not re.search(r'OFF|꺼짐', label['text']):
                    self.assertEqual(fill(px, *rows[n]), rgb555(cc.NAME_RGB[LEGEND_ROW[key]]), label['text'])
                    checked.add(key)
            self.assertEqual(checked, set(LEGEND_ROW), provenance)
            off = [(n, l) for n, l in enumerate(labels[first:], first) if l['text'][:3] in LEGEND_ROW and re.search(r'OFF|꺼짐', l['text'])]
            self.assertEqual(len(off), 6)
            for n, l in off:
                self.assertEqual(fill(px, *rows[n]), rgb555(cc.OFF), l['text'])


if __name__ == '__main__':
    unittest.main()
