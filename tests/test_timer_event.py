"""The 701 Train Platform event that starts the self-destruct countdown is an event marker hidden by its own done flag."""
import ast
import re
import struct
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / 'tools/mapgen/extract_overlay.py').read_text())
ns = {'struct': struct}
wanted = ('callee', 'timer_functions')
body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in wanted) or
        (isinstance(n, ast.Assign) and any(getattr(t, 'id', '') in ('OP_SAVE', 'TIMER_VAR') for t in ast.walk(n.targets[0])))]
exec(compile(ast.Module(body=body, type_ignores=[]), 'extract_overlay.py', 'exec'), ns)


class TimerEvent(unittest.TestCase):
    def test_timer_start_is_found_directly_and_through_calls(self):
        start = bytes((0x24, 0x23, 0x2c, 0x01))                    # Save(0x23, 300)
        reset = bytes((0x24, 0x23, 0, 0))                           # a reset to 0 does not start it
        self.assertEqual(ns['timer_functions']([{0: start}, {0: reset}, {0: bytes((0x18, 0))}, {0: bytes((0x18, 2))}]), {0, 2, 3})

    def test_train_platform_event_row(self):
        text = (ROOT / 'src/overlay_data.h').read_text()
        def rows(name):
            part = text.split(name + '[] = {', 1)[1].split('};', 1)[0]
            return [tuple(int(v, 0) for v in row.split(',')) for row in re.findall(r'\{([-0-9x, ]+)\}', part)]
        guards, markers = rows('interaction_guards'), rows('map_interactions')
        found = [m for m in markers if m[1] == 18 and m[3] == 20]        # pl, floor, seen, kind, x, y, guard_start, guard_count, name
        self.assertEqual({m[0] for m in found}, {0, 1})
        for m in found:
            self.assertEqual(guards[m[6]:m[6] + m[7]], [(4, 183, 0)])    # shown until the countdown event sets FG_COMMON 183


if __name__ == '__main__':
    unittest.main()
