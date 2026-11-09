"""Completion subtraction must handle unrelated scenario branches without truncation."""
import ast
import collections
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ns = {'collections': collections}
for file, names in [('extract_items.py', ('normalized', 'minimize')), ('extract_overlay.py', ('apply_resets', 'puzzle_completion'))]:
    tree = ast.parse((ROOT / 'tools/mapgen' / file).read_text())
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[]), file, 'exec'), ns)

class Completion(unittest.TestCase):
    def test_all_scenario_branches_collapse_to_done_flag(self):
        for bit in (0, 36, 84, 136):
            resets = [((4, bit, 1), (0, 25, bonus), (1, 1, scenario))
                      for bonus in (0, 1) for scenario in (0, 1)]
            self.assertEqual(ns['apply_resets']([()], resets), [((4, bit, 0),)])

    def test_more_than_sixteen_intermediate_paths_are_not_dropped(self):
        resets = [tuple((4, b, 1) for b in range(20)), ((3, 1, 1),)]
        paths = ns['apply_resets']([()], resets)
        self.assertTrue(paths)
        self.assertTrue(all((3, 1, 0) in p for p in paths))

    def test_completion_requires_one_unique_permanent_bit(self):
        reset = bytes((70, 2, 0))
        done = bytes((0x22, 4, 36, 1))
        self.assertEqual(ns['puzzle_completion']([{0: reset, 3: done}]), {2: 36})
        self.assertEqual(ns['puzzle_completion']([{0: reset, 3: done, 7: bytes((0x22, 4, 37, 1))}]), {})
        self.assertEqual(ns['puzzle_completion']([{0: reset, 3: bytes((0x22, 5, 36, 1))}]), {})

    def test_reported_devices_require_unsolved_flags(self):
        import json, re
        text = (ROOT / 'src/overlay_data.h').read_text()
        def rows(name):
            body = text.split(name + '[] = {', 1)[1].split('};', 1)[0]
            return [tuple(int(v, 0) for v in row.split(',')) for row in re.findall(r'\{([-0-9x, ]+)\}', body)]
        guards = rows('interaction_guards')
        markers = rows('map_interactions')
        rules = json.loads((ROOT / 'data/marker_names.json').read_text())['puzzle_rules']
        for evidence, bit in [('108:i50', 0), ('206:i47', 36), ('20D:i47', 84)]:
            found = [r for r in markers if r[3] == 6 and r[8] == rules[evidence]]
            self.assertTrue(found, evidence)
            self.assertTrue(all((4, bit, 0) in guards[r[6]:r[6]+r[7]] for r in found), (evidence, found))

if __name__ == '__main__': unittest.main()
