"""Move map points that project outside their own room shape onto the nearest pixel of that room."""
from pathlib import Path
import json

R = Path(__file__).resolve().parent
CENTRE = 6  # stored points are the native arrow's top-left; the renderer draws at +6


def snap(rows):
    floors = json.loads((R / 'room_shapes.json').read_text())['floors']
    cache, moved = {}, []
    for r in rows:
        key = (r['pl'], r['floor'], r['seen'])
        if key not in cache:
            f = next((f for f in floors if (f['pl'], f['floor']) == (key[0] & 1, key[1])), None)  # pl|2 = Extreme Battle
            cache[key] = {(s['x'] + x, s['y'] + y) for s in (f['rooms'] if f else []) if s['seen'] == key[2]
                          for y, runs in enumerate(s['runs']) for a, w in runs for x in range(a, a + w)}
        pts, p = cache[key], (r['x'] + CENTRE, r['y'] + CENTRE)
        if not pts or p in pts:
            continue
        q = min(pts, key=lambda q: ((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2, q))
        moved.append((key, p, q))
        r['x'], r['y'] = q[0] - CENTRE, q[1] - CENTRE
    return moved

