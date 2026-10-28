"""Regression checks for monster eligibility and numeric-lock markers; no game files required."""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def rows(file, name):
    text = (ROOT / 'src' / file).read_text().split(name + '[] = {', 1)[1].split('};', 1)[0]
    return [tuple(int(v.strip(), 0) for v in row.split(',')) for row in re.findall(r'\{([^{}]+)\}', text)]


class MapMarkers(unittest.TestCase):
    def test_monsters_stay_inside_their_room(self):
        masks = {}
        for floor in json.loads((ROOT / 'data/room_shapes.json').read_text())['floors']:
            for room in floor['rooms']:
                masks.setdefault((floor['pl'], floor['floor'], room['seen']), set()).update(
                    (room['x'] + x, room['y'] + y)
                    for y, runs in enumerate(room['runs']) for start, width in runs for x in range(start, start + width))
        monsters = rows('monsters.h', 'map_monsters')
        self.assertTrue(monsters)
        for pl, floor, x, y, seen, *_ in monsters:
            self.assertIn((x + 6, y + 6), masks.get((pl & 1, floor, seen), set()))

    def test_inert_and_cinematic_spawns_are_absent(self):
        spawns = {(r[0], r[1], r[4], r[2], r[3], r[7]) for r in rows('monsters.h', 'map_monsters')}
        # West Office corpse, West Corridor frozen actor, Rooftop Entrance off-room crow.
        for spawn in ((0, 2, 32, 88, 132, 255), (0, 3, 19, 67, 142, 255), (0, 3, 9, 242, 139, 1)):
            self.assertNotIn(spawn, spawns)
        self.assertTrue(any(r[5] == 0 for r in rows('monsters.h', 'map_monsters')))

    def test_enemy_setting_uses_only_the_new_key(self):
        import configparser
        config = configparser.ConfigParser()
        config.read(ROOT / 'packaging/RE2.AnnotatedMap.ini')
        self.assertEqual(config['MapOverlay']['Enemies'], '0')
        self.assertNotIn('Monsters', config['MapOverlay'])
        for name in ('README.md', 'README.en.md'):
            text = (ROOT / name).read_text()
            self.assertIn('`Enemies`', text)
            self.assertNotIn('`Monsters`', text)

    def test_enemy_legend_uses_the_display_name(self):
        for lang, folder, expected in [('ko', 'korean-assets', ['[7] 적 켜짐', '[7] 적 꺼짐']),
                                      ('en', '', ['[7] ENEMIES: ON', '[7] ENEMIES: OFF'])]:
            data = json.loads((ROOT / 'tests/fixtures' / folder / 'room_names-provenance.json').read_text())
            self.assertEqual([r['text'] for r in data['labels'] if r['text'].startswith('[7] ')], expected)

    def test_zapping_tags_are_separate_from_item_names(self):
        for lang in ('ko', 'en'):
            text = (ROOT / f'src/item_labels-{lang}.h').read_text()
            labels = {int(i): name for i, name in re.findall(
                r'\{(\d+),[^}]+\}, /\* \S+ (.*?) \*/', text)}
            self.assertEqual({i for i, name in labels.items() if name.startswith('[Z] ')},
                             {15, 206, 207, 208, 209})
            self.assertFalse(any(name.startswith('Z ') for name in labels.values()))

    def test_safe_hides_after_unlock_for_both_characters(self):
        guards = rows('overlay_data.h', 'interaction_guards')
        safes = [r for r in rows('overlay_data.h', 'map_interactions')
                 if r[1:6] == (2, 41, 6, 220, 134)]
        self.assertEqual({r[0] for r in safes}, {0, 1})
        self.assertEqual(len(safes), 2)
        for row in safes:
            conditions = guards[row[6]:row[6] + row[7]]
            self.assertEqual(set(conditions), {(1, 6, 0), (4, 37, 0)})
            for opened in (0, 1):
                for bonus in (0, 1):
                    state = {(4, 37): opened, (1, 6): bonus}
                    visible = all(state[(bank, bit)] == value for bank, bit, value in conditions)
                    self.assertEqual(visible, not opened and not bonus)


if __name__ == '__main__':
    unittest.main()
