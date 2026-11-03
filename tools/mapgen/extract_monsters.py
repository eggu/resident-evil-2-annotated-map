"""Extract RE2 monster spawns (SCE_EM_SET) for the map's key-7 monster markers.

op 68 (0x44) SCE_EM_SET  handler 0x4e77d0, 22 bytes; op 142 (0x8E) SCE_EM_SET2 handler 0x4e7cb0, 24 bytes (Extreme
Battle: same layout plus a first-visit chance byte +22). Layout (openre ScdSceEmSet): id +2, type +3, nFloor +6,
globalId +9, x +10, y +12, z +14. Dead check (both handlers): globalId != 0xff and bit globalId set in bank 7
(0x98eb94) when stage >= 3 or status bonus 0x02000000, else bank 6 (0x98eb74).
Script reachability, guards and Extreme Battle tagging (pl|2) reuse extract_items.py.
"""
import collections
import json
import struct

from extract_items import (G, R, NativeMap, parse_functions, room_paths, collapse_switch, mode_pl, stage_of)

EM_OPS = (68, 142)
# Monster category per EMD type (openre enemy.h); NPCs (>= 64) and EM_NONE are not drawn.
CATEGORY = {**{t: 0 for t in range(16, 32)}, 45: 0,      # zombies, zombie arms
            32: 1,                                        # zombie dog
            33: 2,                                        # crow
            34: 3,                                        # licker
            36: 4,                                        # evolved licker
            37: 5, 38: 5,                                 # giant spider, spider babies
            41: 6,                                        # large roach
            58: 7, 59: 7,                                 # giant moth, larvae
            46: 8, 47: 8,                                 # Ivy, vines
            57: 9,                                        # poison Ivy
            42: 10, 43: 10, 44: 10,                       # Tyrant
            35: 11, 39: 11, 40: 11,                       # alligator (no placements), G young/adult
            **{t: 11 for t in range(48, 56)}, 62: 11}     # Birkin G forms
CATEGORY_NAMES = ('zombie', 'dog', 'crow', 'licker', 'evolved_licker', 'spider', 'roach', 'moth',
                  'ivy', 'poison_ivy', 'tyrant', 'g')


def spawn_exclusion(raw):
    # Native zombie init 0x451d88/0x451dca: poses 5/7 become inert corpses with life -1; 2/4 can wake.
    if 16 <= raw[3] <= 31 and raw[4] & 0x3f in (5, 7):
        return 'initial corpse'
    # Spawn animation +18 forces routine 4 (0x4df1ff); behaviour bit7 is the script-frozen 0x8000 flag.
    if struct.unpack_from('<H', raw, 18)[0] or raw[5] & 0x80:
        return 'scripted animation or frozen actor'
    return None


def room_pixels():
    pixels = collections.defaultdict(set)
    for f in json.loads((R / 'room_shapes.json').read_text())['floors']:
        for room in f['rooms']:
            pixels[f['pl'], f['floor'], room['seen']].update(
                (room['x'] + x, room['y'] + y)
                for y, runs in enumerate(room['runs']) for start, width in runs for x in range(start, start + width))
    return pixels


def extract():
    sizes = json.loads((R / 'opcode-sizes.json').read_text())['sizes']
    assert (sizes[68], sizes[142]) == (22, 24)
    native = NativeMap((G / 'Resident Evil 2.exe').read_bytes())
    assert native.read(0x53ae10 + 68 * 4, 4) == struct.pack('<I', 0x4e77d0)
    assert native.read(0x53ae10 + 142 * 4, 4) == struct.pack('<I', 0x4e7cb0)
    rows, excluded, seen_ops = [], [], 0
    pixels = room_pixels()
    for pl in (0, 1):
        for path in sorted((G / f'Pl{pl}/Rdt').glob('*.RDT')):
            blob = path.read_bytes()
            for section in (16, 17):
                functions = parse_functions(blob, section, sizes)
                if not functions:
                    continue
                reach = collections.defaultdict(list)
                for offset, raw, guards, why in room_paths(functions, pl, path.name, section, wanted=EM_OPS):
                    reach[offset].append((guards, why))
                for ops in functions:
                    for offset, raw in ops.items():
                        if raw[0] not in EM_OPS:
                            continue
                        seen_ops += 1
                        etype, nfloor, gid = raw[3], raw[6], raw[9]
                        x, y, z = struct.unpack_from('<hhh', raw, 10)
                        d = dict(pl=mode_pl(pl, path.name), room=path.name, section=section, offset=offset,
                                 type=etype, gid=gid)
                        if etype not in CATEGORY:
                            continue  # NPC / none: not a monster marker
                        reason = spawn_exclusion(raw)
                        if reason:
                            excluded.append(dict(d, reason=reason))
                            continue
                        paths = [g for g, why in reach.get(offset, []) if not why]
                        if not paths:
                            reason = reach[offset][0][1] if offset in reach else 'not proven reachable from script root 0'
                            excluded.append(dict(d, reason=reason))
                            continue
                        # Projector reads nFloor at +4 and an x,z,w,h box at +6.
                        aot = bytes(4) + bytes([nfloor, 0]) + struct.pack('<hhhh', x, z, 0, 0)
                        try:
                            projections = native.projections(pl, path.name, aot)
                        except ValueError as error:
                            excluded.append(dict(d, reason=str(error)))
                            continue
                        dbank = 6 if stage_of(path.name) < 3 else 7
                        for p in projections:
                            if (p['x'] + 6, p['y'] + 6) not in pixels[pl, p['floor'], p['seen']]:
                                excluded.append(dict(d, floor=p['floor'], reason='spawn outside room shape'))
                                continue
                            for g in paths:
                                rows.append(dict(d, floor=p['floor'], seen=p['seen'], x=p['x'], y=p['y'],
                                                 cat=CATEGORY[etype], dbank=dbank, guards=list(g)))
    return rows, excluded, seen_ops


def coalesce(rows):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[tuple(r[k] for k in ('pl', 'floor', 'seen', 'x', 'y', 'cat', 'dbank', 'gid'))].append(r)
    out = []
    for key, rs in sorted(groups.items()):
        for guards in sorted(collapse_switch(tuple(map(tuple, r['guards'])) for r in rs)):
            out.append(dict(rs[0], guards=list(guards), rooms=sorted({r['room'] for r in rs})))
    return out


def write(rows, excluded):
    guards, lines = [], []
    for r in rows:
        lines.append('{%d,%d,%d,%d,%d,%d,%d,%d,%d,%d}, /* %s type %d */' % (
            r['pl'], r['floor'], r['x'], r['y'], r['seen'], r['cat'], r['dbank'], r['gid'], len(guards),
            len(r['guards']), r['rooms'][0][:-4], r['type']))
        guards += r['guards']
    out = ['/* Generated by extract_monsters.py: SCE_EM_SET / SCE_EM_SET2 spawns. */',
           '#ifndef RE2_MONSTERS_H', '#define RE2_MONSTERS_H',
           'typedef struct { unsigned char pl,floor; short x,y; unsigned char seen,cat,dbank,gid; '
           'unsigned short guard_start; unsigned char guard_count; } MapMonster;',
           'static const MapItemGuard monster_guards[] = {']
    out += ['{%d,%d,%d},' % tuple(g) for g in guards] or ['{0,0,0},']
    out += ['};', 'static const MapMonster map_monsters[] = {'] + lines + ['};', '#endif', '']
    (R / 'monsters.h').write_text('\n'.join(out))
    (R / 'monsters.json').write_text(json.dumps(dict(monsters=rows, excluded=excluded), indent=1))


if __name__ == '__main__':
    rows, excluded, seen_ops = extract()
    accounted = len({(r['pl'], r['room'], r['section'], r['offset']) for r in rows}) + len(excluded)
    rows = coalesce(rows)
    assert rows and {0, 1} <= {r['pl'] for r in rows} <= {0, 1, 2, 3}
    assert all(r['gid'] <= 255 and all(g[0] <= 34 or g[0] in (130, 131) for g in r['guards']) for r in rows)
    write(rows, excluded)
    print(json.dumps(dict(em_ops=seen_ops, monster_ops_accounted=accounted, rows=len(rows),
                          by_category={CATEGORY_NAMES[c]: n for c, n in
                                       sorted(collections.Counter(r['cat'] for r in rows).items())},
                          excluded=collections.Counter(e['reason'] for e in excluded))))
