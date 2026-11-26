"""Every native address the runtime translates exists in each Steam layout table. Stdlib only; run from anywhere."""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / 'src'
code = (SRC / 're2_keymap.c').read_text()
used = set(re.findall(r'addr\((0x[0-9a-f]{6})\)', code))
used |= {k for pair in re.findall(r'addr\([^()?]+\?(0x[0-9a-f]{6}):(0x[0-9a-f]{6})\)', code) for k in pair}
used |= set(re.search(r'const unsigned sites\[\]=\{([^}]*)\}', code).group(1).split(','))
used |= {re.search(r'#define FLOOR_SITE (0x[0-9a-f]{6})', code).group(1)}
used = {int(k, 16) for k in used}

layouts = (SRC / 'layouts.h').read_text()
names = re.findall(r'static const LayoutAddr (\w+)_addrs', layouts)
assert names == [f'{who}{lang}' for lang in 'UJFGIS' for who in ('Leon', 'Claire')], names
for name in names:
    body = layouts.split(f'{name}_addrs[]={{')[1].split('};')[0]
    keys = [int(k, 16) for k in re.findall(r'\{0x(\w+),0x\w+\}', body)]
    assert keys == sorted(keys), f'{name}: addr() binary search needs sorted keys'
    missing = sorted(used - set(keys))
    assert not missing, f'{name}: missing {[hex(k) for k in missing]}'
print(f'PASS {len(used)} native keys in {len(names)} Steam layouts')
