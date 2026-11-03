"""Extract conservative RE2 pickup markers; never interpret arbitrary RDT bytes as opcodes.

Run with Python + Unicorn. Inputs are the installed EXE/RDT and the existing
opcode-size table. See items-report.md for native addresses and omissions.
"""
from pathlib import Path
import collections
import os
import hashlib
import json
import struct

R = Path(__file__).resolve().parent
G = Path(os.environ['RE2_GAME'])
NAMES = {
    20: ('HandgunBullets', '권총 탄약'), 21: ('ShotgunShells', '샷건 탄약'),
    22: ('MagnumBullets', '매그넘 탄약'), 24: ('GrenadeRounds', '유탄'),
    25: ('FlameRounds', '화염탄'), 26: ('AcidRounds', '산성탄'),
    27: ('SMGBullets', '기관단총 탄약'), 29: ('BowGunBolts', '보우건 볼트'),
    30: ('InkRibbon', '잉크 리본'), 35: ('FirstAidSpray', '응급 스프레이'),
    38: ('GreenHerb', '허브 (초록)'), 39: ('RedHerb', '허브 (빨강)'),
    40: ('BlueHerb', '허브 (파랑)'),
    31: ('SmallKey', '작은 열쇠'), 47: ('Lighter', '라이터'),
    48: ('Lockpick', '키픽'), 50: ('ValveHandle', '밸브 핸들'),
    51: ('RedJewel', '붉은 보석'), 52: ('RedCard', '빨간 카드'),
    53: ('BlueCard', '파란 카드'), 54: ('SerpentStone', '뱀 석판'),
    55: ('JaguarStone', '재규어 석판'), 56: ('JaguarStoneL', '석판 왼쪽'),
    57: ('JaguarStoneR', '석판 오른쪽'), 58: ('EagleStone', '독수리 석판'),
    59: ('BishopPlug', '비숍 플러그'), 60: ('RookPlug', '룩 플러그'),
    61: ('KnightPlug', '나이트 플러그'), 62: ('KingPlug', '킹 플러그'),
    63: ('WeaponBoxKey', '무기고 열쇠'), 64: ('Detonator', '신관'),
    65: ('C4Explosive', '폭약'), 66: ('C4Detonator', '기폭 장치'),
    67: ('Crank', '크랭크'), 71: ('UnicornMedal', '유니콘 메달'),
    72: ('EagleMedal', '독수리 메달'), 73: ('WolfMedal', '늑대 메달'),
    74: ('Cog', '톱니바퀴'), 75: ('ManholeOpener', '맨홀 손잡이'),
    76: ('MainFuse', '메인 퓨즈'), 77: ('FuseCase', '퓨즈 케이스'),
    78: ('Vaccine', '백신'), 79: ('VaccineCart', '백신 카트리지'),
    81: ('VaccineBase', '백신 베이스'), 82: ('GVirus', 'G 바이러스'),
    83: ('SpecialKey', '특수 열쇠'), 84: ('JointPlugBlue', '파란 조인트'),
    85: ('JointPlugRed', '빨간 조인트'), 86: ('Cord', '전선'),
    88: ('CabinKey', '관리실 열쇠'), 89: ('SpadeKey', '스페이드 열쇠'),
    90: ('DiamondKey', '다이아 열쇠'), 91: ('HeartKey', '하트 열쇠'),
    92: ('ClubKey', '클로버 열쇠'), 93: ('DownKey', '하강 열쇠'),
    94: ('UpKey', '상승 열쇠'), 95: ('PowerRoomKey', '동력실 열쇠'),
    96: ('MODisk', 'MO 디스크'), 97: ('UmbrellaKeyCard', '엄브렐러 카드'),
    98: ('MasterKey', '마스터 열쇠'), 99: ('PlatformKey', '플랫폼 열쇠'),
    # Weapons, weapon parts and darkroom films (user 2026-10-19: Leon B factory Shotgun Parts missing); [3] key items.
    17: ('RocketLauncher', '로켓 런처'), 36: ('AntiVirusBomb', '항바이러스 폭탄'),  # Extreme Battle
    1: ('Knife', '나이프'), 5: ('Magnum', '매그넘'), 7: ('Shotgun', '샷건'), 9: ('GrenadeLauncher', '유탄 발사기'), 12: ('Bowgun', '보우건'), 13: ('ColtSAA', '콜트 S.A.A.'), 16: ('Flamethrower', '화염 방사기'), 32: ('HandgunParts', '권총 부품'), 33: ('MagnumParts', '매그넘 부품'), 34: ('ShotgunParts', '샷건 부품'), 68: ('FilmA', '필름 A'), 69: ('FilmB', '필름 B'), 70: ('FilmC', '필름 C'), 80: ('FilmD', '필름 D'),
    # Overlay-only IDs: map objects are event rewards, not inventory items.
    200: ('PoliceStationMap', '경찰서 지도'), 201: ('PoliceB1Map', '경찰서 지하 지도'),
    202: ('SewageDisposalMap', '하수 처리장 지도'), 203: ('SewerMap', '하수도 지도'),
    204: ('FactoryMap', '공장 지도'), 205: ('LaboratoryMap', '연구소 지도'),
    # Zapping (A -> B carry-over) markers; see extract_zapping.
    15: ('SubMachineGun', '[Z] 기관단총'), 206: ('SidePack', '[Z] 사이드팩'), 207: ('CordSpot', '[Z] 전선'),
    208: ('GasControl', '[Z] B.O.W. 가스'), 209: ('PoisonIvy', '[Z] 독성 아이비'),
}


def stage_of(room_name):
    # Extreme Battle loads ROOMA..G for engine stages 0..6 (0x98e798 = 9 offsets the file letter only).
    c = room_name[4]
    return int(c) - 1 if c.isdigit() else ord(c) - ord('A')


def mode_pl(pl, room_name):
    # Runtime row key: Extreme Battle rows are pl|2 (re2_keymap.c marker_pl).
    return pl | (0 if room_name[4].isdigit() else 2)


# SCD work words 0x98eae4 + 2*var (switch 0x4e4970): 0x1e = Extreme Battle character (word_98EB20), 0x1f = level
# (ex_battle_mode 0x98eb22). Guard bank SWITCH_BANK+var tests var == bit (re2_keymap.c bank_bit).
SWITCH_VARS, SWITCH_BANK = (0x1e, 0x1f), 100
# Item AOT opcodes. 141 (0x8D, handler 0x4e53b0) = Extreme Battle ITEM_AOT_SET: 0x4E layout (item +14, pickup bit +18
# in bank 8/34, nFloor +4) plus a first-visit chance byte +22 (0 in every RDT). audit() re-derives this set from the EXE.
ITEM_OPS = (78, 105, 141)
DOOR_OPS = {59, 104}  # DOOR_AOT_SET / _4P: same AOT table and banks, handled by the lock pipeline (project_all.py)
ZAPPING_BANK = 29  # FG_ZAPPING; survives from scenario A into B (openre FlagGroup::Zapping, re-scd)
# (room, item, AOT x,z,w,h, hide bank, hide bit, guards). Sources: re-scd extract/re2/pl{0,1}/<room>.bio.
ZAPPING = (
    ('214', 15, (-15780, -6600, 2850, 1230), ZAPPING_BANK, 0, ()),   # Armory locker: SMG taken sets Z0
    ('214', 206, (-14280, -6600, 2850, 1230), ZAPPING_BANK, 1, ()),  # same locker: Side Pack sets Z1
    ('204', 207, (-19091, -16772, 1800, 2100), ZAPPING_BANK, 9, ((ZAPPING_BANK, 10, 0),)),  # cord used here or
    ('20F', 207, (-16593, -7658, 1400, 3000), ZAPPING_BANK, 10, ((ZAPPING_BANK, 9, 0),)),   # here (one only)
    ('612', 208, (-28790, -10800, 6190, 4900), ZAPPING_BANK, 14, ((1, 1, 0),)),  # A: gas release sets Z14
    # B: Z14 from A spawns ENEMY_IVY_PURPLE in the Plant Cultivation Room; bank 255 = never hidden.
    ('60E', 209, (-23383, -21505, 1000, 1000), 255, 0, ((1, 1, 1), (ZAPPING_BANK, 14, 1))),
)
MAP_IDS = dict(zip(('police_station', 'police_b1', 'sewage_disposal', 'sewer', 'factory', 'laboratory'), range(200, 206)))

# These items are scenario-specific in the original game, even when their RDT
# setup is shared between the A and B room files.
SCENARIO_GATES = {
    (94, None): 1,  # Control Panel Key (U): B scenarios only
    (99, None): 1,  # Platform Key: B scenarios only
    (98, None): 1, # Master Key: Leon B and Claire B only
}

# The Spade Key's 1x1 pickup AOT is far from its linked statue model.
ITEM_MAP_POINT_OVERRIDES = {
    (0, 'ROOM2000.RDT', 89): (149, 125),
    (1, 'ROOM2001.RDT', 89): (149, 125),
}


def parse_functions(blob, section, sizes):
    offsets = struct.unpack_from('<23I', blob, 8)
    start = offsets[section]
    if not start:
        return []
    end = min([x for x in offsets if x > start] or [len(blob)])
    assert 0 < start < end <= len(blob)
    first = struct.unpack_from('<H', blob, start)[0]
    assert first and first % 2 == 0 and first < end - start
    relative = struct.unpack_from('<' + 'H' * (first // 2), blob, start)
    assert relative[0] == first and list(relative) == sorted(relative)
    assert all(first <= x < end - start for x in relative)
    functions = []
    for a, z in zip([start + x for x in relative], [start + x for x in relative[1:]] + [end]):
        ops, prev, last_end = {}, None, None
        while a < z:
            op = blob[a]
            size = sizes[op] if op < len(sizes) else 0
            if (not size or a + size > z) and last_end is not None:
                # ponytail: bytes after evt_end are padding/trailing data; jumps into them still fail closed in walk().
                ops = {k: v for k, v in ops.items() if k < last_end}
                break
            if not size or a + size > z:
                # Trailing padding is not a licence to resynchronize a failed function.
                raise ValueError(('invalid instruction', a, op, z))
            ops[a] = blob[a:a + size]
            prev = op
            if op == 1:
                last_end = a + size
            a += size
        functions.append(ops)
    return functions


def normalized(guards):
    values = {}
    for bank, bit, value in guards:
        if (bank, bit) in values and values[bank, bit] != value:
            return None
        values[bank, bit] = value
    return tuple(sorted((bank, bit, value) for (bank, bit), value in values.items()))


def minimize(guard_sets):
    """Merge OR-ed guard sets that differ only in one flag's value (x&a | x&!a = x)."""
    sets = {frozenset(g) for g in guard_sets}
    changed = True
    while changed:
        changed = False
        for a in list(sets):
            for b in list(sets):
                diff = a ^ b
                if len(diff) == 2 and len({(x[0], x[1]) for x in diff}) == 1 and a in sets and b in sets:
                    sets -= {a, b}
                    sets.add(a & b)
                    changed = True
    # Drop sets implied by a weaker (subset) set.
    return [tuple(sorted(s)) for s in sets if not any(o < s for o in sets)]


def collapse_switch(guard_sets):
    """(b==v1) | (b==v2) | ... | (b not in {v1,v2,...}) == true for switch banks; repeat to a fixpoint."""
    sets = {frozenset(g) for g in guard_sets}
    changed = True
    while changed:
        changed = False
        for bank in {g[0] for s in sets for g in s if g[0] >= SWITCH_BANK}:
            groups = collections.defaultdict(set)
            for s in sets:
                groups[frozenset(g for g in s if g[0] != bank)].add(frozenset(g for g in s if g[0] == bank))
            for rest, parts in groups.items():
                cases = {next(iter(p))[1] for p in parts if len(p) == 1 and next(iter(p))[2] == 1}
                default = frozenset((bank, v, 0) for v in cases)
                if cases and default in parts:
                    sets = {s for s in sets if frozenset(g for g in s if g[0] != bank) != rest} | {rest}
                    changed = True
                    break
            if changed:
                break
    return minimize(tuple(sorted(s)) for s in sets)


def walk(functions, fn, guards=(), ancestry=(), wanted=(78, 105, 141)):
    """Structured IF/ELSE and synchronous GOSUB only; unknown paths fail closed.

    Yield (offset, instruction, predicates, limitation). Returned paths preserve
    early-return guards, so bonus-only root exits cannot expose normal spawns.
    """
    if fn in ancestry or fn >= len(functions):
        return [], False
    ops = functions[fn]
    if not ops:
        return [], True
    end = max(ops) + len(ops[max(ops)])
    found = []
    switches = []

    def region(start, stop, paths, limitation='', in_switch=False):
        pos = start
        while pos < stop and paths:
            if pos not in ops:
                return []
            q = ops[pos]
            op = q[0]
            nxt = pos + len(q)
            if op in (1, 25):  # evt_end / return
                return []
            if op == 6:
                target = pos + 4 + struct.unpack_from('<H', q, 2)[0]
                if target not in ops and target != end:
                    return []
                other = target - 4
                has_else = other in ops and ops[other][0] == 7
                merge = other + struct.unpack_from('<H', ops[other], 2)[0] if has_else else target
                if not pos < target <= merge <= stop:
                    return []
                conds = []
                height = False
                body = nxt
                while body in ops and (ops[body][0] == 33 or ops[body][:3] == b'\x3e\x00\x11' or (
                        ops[body][0] == 35 and ops[body][2] in SWITCH_VARS and ops[body][3] in (0, 5))):
                    c = ops[body]
                    if c[0] == 33:
                        conds.append((c[1], c[2], c[3]))
                    elif c[0] == 35:  # CMP var ==/!= value on Extreme Battle globals -> switch guard bank
                        v = struct.unpack_from('<h', c, 4)[0]
                        conds.append((SWITCH_BANK + c[2], v, 1 if c[3] == 0 else 0) if 0 <= v < 256 else (255, 0, 9))
                    else:
                        # Player storey compare (two-deck rooms, e.g. Extreme Battle sewer D010): both branches
                        # spawn; each AOT is projected on its own nFloor byte, so no guard is needed.
                        height = True
                    body += len(c)
                # Only persistent flags and stable player/scenario/difficulty flags
                # have a meaning when viewing a DIFFERENT room on the map.
                supported = (bool(conds) or height) and all(c[0] in (0, 1, 3, 4, 8, 34) + tuple(SWITCH_BANK + v for v in SWITCH_VARS)
                                                            and c[2] in (0, 1) for c in conds)
                unknown = limitation or ('' if supported else 'unsupported condition/local room state')
                yes_paths, no_paths = [], []
                for path in paths:
                    yes = normalized(path + tuple(conds)) if supported else path
                    if yes is not None:
                        yes_paths += region(body, other if has_else else target, [yes], unknown, in_switch)
                    # AND's complement is OR, represented as separate marker rows.
                    if supported and not conds:
                        no_paths += region(target, merge, [path], unknown, in_switch) if has_else else [path]
                    for k in range(len(conds) if supported else 1 if not height else 0):
                        no = normalized(path + tuple(conds[:k]) + ((conds[k][0], conds[k][1], 1 - conds[k][2]),)) if supported else path
                        if no is not None:
                            no_paths += region(target, merge, [no], unknown, in_switch) if has_else else [no]
                # Both sides reaching merge can drop branch predicates. Unknown
                # conditions are scoped to their branches, never guessed true.
                paths = list(dict.fromkeys(yes_paths + no_paths))
                if yes_paths and no_paths:
                    paths = paths if supported else paths[:1]
                pos = merge
                continue
            if op == 19 and q[1] in SWITCH_VARS:
                # switch(var) { case v: ... break; } on Extreme Battle globals; guard (SWITCH_BANK+var, v, 1|0).
                bank, cases, default, p2 = SWITCH_BANK + q[1], [], None, nxt
                while p2 in ops and ops[p2][0] != 22:
                    o2 = ops[p2][0]
                    if o2 in (19, 1, 25):
                        return []  # nested switch / exit inside a case: fail closed
                    if o2 == 20:
                        cases.append((p2, struct.unpack_from('<h', ops[p2], 4)[0]))
                    elif o2 == 21:
                        default = p2
                    p2 += len(ops[p2])
                if p2 not in ops or not all(0 <= v < 256 for _, v in cases):
                    return []
                others = tuple((bank, v, 0) for _, v in cases)
                entries = [(c, ((bank, v, 1),)) for c, v in cases] + [(default, others)]
                out = []
                switches.append((nxt, p2, out))  # forward gotos into this switch append their exits to `out`
                for path in paths:
                    for at, conds in entries:
                        g = normalized(path + conds)
                        if g is None:
                            continue
                        out += [g] if at is None else region(at + len(ops[at]), p2, [g], limitation, True)
                switches.pop()
                paths = list(dict.fromkeys(out))
                pos = p2 + len(ops[p2])
                continue
            if op == 23 and switches:
                # goto forward inside the enclosing switch (Extreme Battle D080: case 0 jumps into case 3's body
                # once bank4 bit 29 is set); other gotos stay excluded below.
                target = pos + struct.unpack_from('<h', q, 4)[0]
                start, stop_sw, exits = switches[-1]
                if pos < target < stop_sw and target in ops:
                    for path in paths:
                        exits += region(target, stop_sw, [path], limitation, True)
                    return []
            if in_switch and op in (20, 21):  # falling into the next case label continues
                pos = nxt
                continue
            if in_switch and op == 26:  # break: leave the switch
                return paths
            if op == 24:
                for path in paths:
                    sub, _ = walk(functions, q[1], path, ancestry + (fn,), wanted)
                    found.extend((p, v, g, limitation or why) for p, v, g, why in sub)
            elif op in wanted:
                found.extend((pos, q, path, limitation) for path in paths)
            elif op in (13, 15, 17, 19, 23, 27):
                # shortcut: unstructured flow and loops are excluded, add a CFG
                # interpreter only if an omitted core pickup needs that path.
                return []
            pos = nxt
        return paths

    continuing = region(min(ops), end, [guards])
    return found, bool(continuing)


def cond_guards(ops, body):
    """Conditions after IF: (next op offset, guards tuple or None if unsupported, has storey compare)."""
    conds, height = [], False
    while body in ops and ops[body][0] in (33, 35, 62):
        c = ops[body]
        if c[0] == 33 and c[1] in (0, 1, 3, 4, 8, 34) and c[3] in (0, 1):
            conds.append((c[1], c[2], c[3]))
        elif c[0] == 35 and c[2] in SWITCH_VARS and c[3] in (0, 5) and 0 <= struct.unpack_from('<h', c, 4)[0] < 256:
            conds.append((SWITCH_BANK + c[2], struct.unpack_from('<h', c, 4)[0], 1 if c[3] == 0 else 0))
        elif c[:3] == b'\x3e\x00\x11':
            height = True
        else:
            conds = None
            while body in ops and ops[body][0] in (33, 35, 62):
                body += len(ops[body])
            return body, None, height
        body += len(c)
    return body, tuple(conds), height


def walk_cfg(functions, fn, guards=(), ancestry=(), wanted=(78, 105, 141), budget=None):
    """Jump-target interpreter over one SCD function: IF/ELSE, switch/case/break and FORWARD goto.
    Backward jumps (loops) and unknown loop ops end a path; unsupported conditions mark both branches
    'unsupported condition/local room state' until the IF's merge point. Yields like walk()."""
    if fn in ancestry or fn >= len(functions) or not functions[fn]:
        return []
    ops = functions[fn]
    budget = budget if budget is not None else [20000]
    # switch extents for break: switch pos -> eswitch pos
    extents = []
    for pos in sorted(ops):
        if ops[pos][0] == 19:
            p2, depth = pos + len(ops[pos]), 0
            while p2 in ops and not (ops[p2][0] == 22 and depth == 0):
                depth += {19: 1, 22: -1}.get(ops[p2][0], 0)
                p2 += len(ops[p2])
            if p2 in ops:
                extents.append((pos, p2))
    found, seen = [], set()
    stack = [(min(ops), guards, 0)]  # (pos, guards, limited_until)
    while stack and budget[0] > 0:
        pos, path, limited = stack.pop()
        while pos in ops:
            budget[0] -= 1
            if (pos, path, limited) in seen:
                break
            seen.add((pos, path, limited))
            if limited and pos >= limited:
                limited = 0
            q = ops[pos]; op = q[0]; nxt = pos + len(q)
            why = 'unsupported condition/local room state' if limited else ''
            if op in (1, 25):
                break
            if op == 6:
                target = pos + 4 + struct.unpack_from('<H', q, 2)[0]
                body, conds, height = cond_guards(ops, nxt)
                other = target - 4
                merge = other + struct.unpack_from('<H', ops[other], 2)[0] if other in ops and ops[other][0] == 7 else target
                if conds is None:  # unknown condition: both sides, limited until the merge point
                    lim = max(limited, merge)
                    stack.append((target, path, lim))
                    pos, limited = body, lim
                    continue
                yes = normalized(path + conds)
                for k in range(len(conds)):  # AND complement = OR of single negations
                    no = normalized(path + conds[:k] + ((conds[k][0], conds[k][1], 1 - conds[k][2]),))
                    if no is not None:
                        stack.append((target, no, limited))
                if height and not conds:
                    stack.append((target, path, limited))
                if yes is None:
                    break
                pos, path = body, yes
                continue
            if op == 7:
                pos = pos + struct.unpack_from('<H', q, 2)[0]
                continue
            if op == 19:
                ext = next((e for e in extents if e[0] == pos), None)
                if q[1] not in SWITCH_VARS or ext is None:
                    break
                bank, cases, default, p = SWITCH_BANK + q[1], [], None, nxt
                while p < ext[1]:
                    if ops[p][0] == 20:
                        cases.append((p, struct.unpack_from('<h', ops[p], 4)[0]))
                    elif ops[p][0] == 21:
                        default = p
                    p += len(ops[p])
                if not all(0 <= v < 256 for _, v in cases):
                    break
                others = tuple((bank, v, 0) for _, v in cases)
                for at, conds in [(c + 6, ((bank, v, 1),)) for c, v in cases] + [
                        ((default + 2) if default else ext[1] + 2, others)]:
                    g = normalized(path + conds)
                    if g is not None:
                        stack.append((at, g, limited))
                break
            if op == 26:
                inner = [e for e in extents if e[0] < pos < e[1]]
                if not inner:
                    break
                pos = max(inner)[1] + 2
                continue
            if op == 23:
                target = pos + struct.unpack_from('<h', q, 4)[0]
                if target <= pos or target not in ops:
                    break  # loop or bad target: fail closed
                pos = target
                continue
            if op == 24:
                found += [(p, v, g, why or w) for p, v, g, w in walk_cfg(functions, q[1], path, ancestry + (fn,), wanted, budget)]
            elif op in wanted:
                found.append((pos, q, path, why))
            elif op in (13, 15, 17, 27):
                break
            pos = nxt
    return found


def room_paths(functions, pl, room, section, wanted=(78, 105, 141)):
    paths = walk(functions, 0, wanted=wanted)[0]
    # Fallback: offsets the structured walker could not prove cleanly get the jump-target interpreter's paths.
    clean = {p[0] for p in paths if not p[3]}
    extra = [p for p in walk_cfg(functions, 0, wanted=wanted) if p[0] not in clean]
    paths = [p for p in paths if p[0] in clean or p[0] not in {e[0] for e in extra if not e[3]}] + extra
    # These root setup branches select a storey by player height. Project each
    # pickup with its own AOT floor; retain predicates inside the setup routine.
    setups = {
        (0, 'ROOM4030.RDT', 17): (0x22ee, '3e0011000400', (25, 27), 6),
        (1, 'ROOM4031.RDT', 17): (0x22f0, '3e0011000400', (23, 24), 6),
        (1, 'ROOM4001.RDT', 17): (0x1724, '3e0011020400', (19,), 2),
    }
    setup = setups.get((pl, room, section))
    if setup:
        offset, expected, routines, count = setup
        assert functions[0][offset].hex() == expected, (room, 'height branch changed')
        extra = [p for fn in routines for p in walk(functions, fn, wanted=(78, 105, 141))[0]]
        offsets = {p[0] for p in extra}
        assert len(offsets) == count, (room, 'pickup setup changed')
        paths = [p for p in paths if p[0] not in offsets] + [p for p in extra if p[1][0] in wanted]
    return paths


class NativeMap:
    """Same native floor/index/coordinate routines used by project_all.py."""
    def __init__(self, blob):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
        self.blob = blob
        pe = struct.unpack_from('<I', blob, 60)[0]
        self.sections = []
        self.u = Uc(UC_ARCH_X86, UC_MODE_32)
        self.u.mem_map(0x400000, 0x1000000)
        for i in range(struct.unpack_from('<H', blob, pe + 6)[0]):
            o = pe + 24 + struct.unpack_from('<H', blob, pe + 20)[0] + 40 * i
            _, rv, size, raw = struct.unpack_from('<IIII', blob, o + 8)
            self.sections.append((0x400000 + rv, size, raw))
            self.u.mem_write(0x400000 + rv, blob[raw:raw + size])
        self.u.mem_map(0x20000000, 0x10000)
        assert self.read(0x53ae10 + 78 * 4, 4) == struct.pack('<I', 0x4e52e0)
        assert self.read(0x53b238, 4) == struct.pack('<I', 0x98ebb4)
        assert self.read(0x53b2a0, 4) == struct.pack('<I', 0x98ebd4)

    def read(self, va, size):
        for base, count, raw in self.sections:
            if base <= va and va + size <= base + count:
                return self.blob[raw + va - base:raw + va - base + size]
        raise ValueError(hex(va))

    def call(self, fn, a, b):
        from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX
        self.u.reg_write(UC_X86_REG_ESP, 0x20008000)
        self.u.mem_write(0x20008000, struct.pack('<III', 0x20000100, a, b))
        self.u.emu_start(fn, 0x20000100, count=500)
        return self.u.reg_read(UC_X86_REG_EAX)

    # 0x4faf80 (room -> map floor) reads: player height 0x989ff6, scenario bit 0x40000000 of 0x989ed0, bank4
    # (FG_COMMON) bits 98/99/137/190 (factory lift, lab, final stage), previous room 0x98eb1a == 0x602 and lab byte
    # 0x692fac. The same room is then drawn on a different sub-floor map (e.g. Vacant Factory 1F upper/lower deck:
    # room 503 moves from floor 10 to 11 once the Up Key raised the lift in scenario B).
    FLOOR_STATES = [(s, f, prev, lab) for s in (0, 0x40000000) for f in (0, 98, 99, 137, 190)
                    for prev, lab in ((0, 0), (0x602, 1))]

    def floors(self, pl, stage, room, level):
        """Every map floor 0x4faf80 can pick for this room at AOT height `level`; the default state first."""
        out = []
        for scenario, flag, prev, lab in self.FLOOR_STATES:
            bank = bytearray(32)
            if flag:
                struct.pack_into('<I', bank, flag // 32 * 4, 0x80000000 >> (flag % 32))
            self.u.mem_write(0x989ff6, bytes([level]))
            self.u.mem_write(0x989ed0, struct.pack('<I', scenario | pl << 31))
            self.u.mem_write(0x98eb4c, bytes(bank))
            self.u.mem_write(0x98eb1a, struct.pack('<H', prev))
            self.u.mem_write(0x692fac, bytes([lab]))
            floor = self.call(0x4faf80, stage, room)
            if floor not in out:
                out.append(floor)
        for va, size in ((0x989ed0, 4), (0x98eb4c, 32), (0x98eb1a, 2), (0x692fac, 1)):
            self.u.mem_write(va, bytes(size))
        return out

    def projections(self, pl, room_name, raw):
        """project() on every sub-floor the room can be drawn on; floors whose room rect rejects it are skipped."""
        stage, room = stage_of(room_name), int(room_name[5:7], 16)
        out, first = [], None
        for floor in self.floors(pl, stage, room, raw[4]):
            try:
                out.append(self.project(pl, room_name, raw, floor))
            except ValueError as error:
                first = first or error
        if not out:
            raise first
        return out

    def project(self, pl, room_name, raw, floor=None):
        from unicorn.x86_const import UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_ESI
        stage, room = stage_of(room_name), int(room_name[5:7], 16)
        # Two-storey rooms (e.g. sewer 401/403) sit on two map floors; 0x4faf80 picks by the player's
        # height level byte 0x989ff6, so use the AOT's own nFloor (byte 4 of AOT/ITEM_AOT_SET).
        if floor is None:
            self.u.mem_write(0x989ff6, bytes([raw[4]]))
            floor = self.call(0x4faf80, stage, room)
        index = self.call(0x4fb1c0, floor, room)
        if not 0 <= floor < 20:
            raise ValueError('no native floor')
        table = 0x53eb98 if pl else 0x53eaf8
        ptr, count = struct.unpack('<IB', self.read(table + floor * 8, 5))
        if index >= count:
            raise ValueError('no native room projection')
        record = self.read(ptr + index * 16, 16)
        x, z, w, h = struct.unpack_from('<hhhh', raw, 6)
        self.u.mem_write(0x989f28, struct.pack('<i', x + w // 2))
        self.u.mem_write(0x989f30, struct.pack('<i', z + h // 2))
        self.u.mem_write(0x691fb8, b'\0' * 4)
        for reg, value in ((UC_X86_REG_EBX, ptr + index * 16), (UC_X86_REG_EBP, 0), (UC_X86_REG_ESI, 0x20001000)):
            self.u.reg_write(reg, value)
        self.u.emu_start(0x4faa19, 0x4faae3, count=200)
        px, py = struct.unpack('<hh', self.u.mem_read(0x20001008, 4))
        # Rooms may extend past x=255 (the map pans), so test the native room rect.
        w, h, rx, ry = record[2], record[3], *struct.unpack_from('<hh', record, 4)
        if not (rx - 8 <= px <= rx + w + 8 and ry - 8 <= py <= ry + h + 8):
            raise ValueError('projection outside native room rectangle')
        return dict(floor=floor, x=px, y=py, seen=record[12], room_index=index,
                    bank=8 if stage < 4 else 34)


def extract_area_maps(native):
    data = json.loads((R / 'area-maps.json').read_text())
    assert data['exe_sha256'] == hashlib.sha256(native.blob).hexdigest(), 'Re-run map analysis for this EXE'
    for name, digest in data['inputs'].items():
        assert hashlib.sha256((G / name).read_bytes()).hexdigest() == digest, f'Re-run map analysis for {name}'
    floors = json.loads((R / 'room_shapes.json').read_text())['floors']
    result = []
    for row in data['maps']:
        p = row['position']
        floor = next(f for f in floors if (f['pl'], f['floor']) == (row['pl'], p['floor']))
        shape = next(r for r in floor['rooms'] if r['seen'] == p['seen'])
        # Native projection returns the arrow's top-left; the renderer adds 6px.
        center = (p['x'] + 6, p['y'] + 6)
        point = min(((x + shape['x'], y + shape['y']) for y, runs in enumerate(shape['runs'])
                     for a, width in runs for x in range(a, a + width)),
                    key=lambda q: (q[0] - center[0]) ** 2 + (q[1] - center[1]) ** 2)
        item = MAP_IDS[row['kind']]
        # Fixed wall maps use their physical pickup flag even while Ada/Sherry is active.
        result.append(dict(pl=row['pl'], room=row['room'], section=17, function=row['procedure'],
                           offset=row['aot_offset'], raw=row['aot_raw'], item=item,
                           name=NAMES[item][0], name_ko=NAMES[item][1], floor=p['floor'], seen=p['seen'],
                           x=point[0] - 6, y=point[1] - 6, bank=row['physical_taken']['bank'],
                           bit=row['physical_taken']['bit'], guards=[]))
    assert len(result) == 14 and {d['item'] for d in result} == set(MAP_IDS.values())
    return result


def reward_giver(functions, aot_id):
    """Event AOT that hands out a sentinel-position item AOT: a press-to-use SCE_EVENT whose gosub target runs op 0x47
    with that AOT id. 60D func 5: if bank4 bit119 (Fuse Case inserted) and bank34 bit24 clear -> 47 01 = Main Fuse
    (user 2026-10-23). Returns the event's raw aot_set, or None."""
    for ops in functions:
        for raw in ops.values():
            if raw[0] == 44 and raw[2] == 5 and raw[3] & 0x10 and raw[16] == 0x18 and raw[17] < len(functions) and \
               any(r[0] == 0x47 and r[1] == aot_id for r in functions[raw[17]].values()):
                return raw
    return None


def four_point_rect(raw):
    """item_aot_set_4p (105): x,z,w,h bounding box of the four corners in the op-78 layout NativeMap projects."""
    c = struct.unpack_from('<8h', raw, 6)
    x0, z0 = min(c[0::2]), min(c[1::2])
    return raw[:6] + struct.pack('<hhHH', x0, z0, max(c[0::2]) - x0, max(c[1::2]) - z0)


def extract():
    sizes = json.loads((R / 'opcode-sizes.json').read_text())['sizes']
    assert sizes[78] == 22 and sizes[105] == 30
    native = NativeMap((G / 'Resident Evil 2.exe').read_bytes())
    result, excluded, sources, failures = [], [], [], []
    for pl in (0, 1):
        for path in sorted((G / f'Pl{pl}/Rdt').glob('*.RDT')):
            blob = path.read_bytes()
            sources.append(dict(path=str(path.relative_to(G)), sha256=hashlib.sha256(blob).hexdigest()))
            for section in (16, 17):
                try:
                    functions = parse_functions(blob, section, sizes)
                except (AssertionError, ValueError, struct.error) as error:
                    failures.append(dict(pl=pl, room=path.name, section=section, error=str(error)))
                    continue
                if not functions:
                    continue
                reachable = room_paths(functions, pl, path.name, section)
                by_offset = collections.defaultdict(list)
                for offset, raw, guards, limitation in reachable:
                    by_offset[offset].append((guards, limitation))
                for offset, paths in by_offset.items():
                    clean = minimize(g for g, why in paths if not why)
                    by_offset[offset] = [(g, '') for g in clean] + [p for p in paths if p[1]][:1]
                for fn, ops in enumerate(functions):
                    for offset, raw in ops.items():
                        if raw[0] not in ITEM_OPS:
                            continue
                        item = struct.unpack_from('<H', raw, 22 if raw[0] == 105 else 14)[0]
                        if item not in NAMES or (item == 17 and path.name[4].isdigit()):
                            continue  # Rocket Launcher: Extreme Battle pickup; the scenario-B finale one is thrown in
                        d = dict(pl=mode_pl(pl, path.name), room=path.name, section=section, function=fn,
                                 offset=offset, item=item, name=NAMES[item][0], name_ko=NAMES[item][1], raw=raw.hex())
                        reason = ''
                        bit = struct.unpack_from('<H', raw, 26 if raw[0] == 105 else 18)[0]
                        at = four_point_rect(raw) if raw[0] == 105 else raw  # where the map point comes from
                        if raw[0] == 105 and raw[2] != 2:
                            reason = 'not a regular interactive floor pickup'
                        elif raw[0] == 105:
                            pass  # 60D Fuse Case (user 2026-10-23): bounding-box centre
                        elif raw[2] != 2 or raw[3] & ~0x40 not in (0x31, 0):
                            # PL|MANUAL|FRONT; +UNDER 0x40 (Leon B factory Shotgun Parts). SAT 0 = Extreme Battle table
                            # stacks (Library A120); original-mode SAT-0 items all sit at sentinel positions (next check).
                            reason = 'not a regular interactive floor pickup'
                        elif struct.unpack_from('<hh', raw, 6) == (0, 0) or max(map(abs, struct.unpack_from('<hh', raw, 6))) >= 30000:
                            # 1x1 AOTs at real coordinates are puzzle rewards (Spade Key statue); keep them.
                            # Rewards handed out by an event (machine, statue) are drawn at that event's spot.
                            at = reward_giver(functions, raw[1])
                            if at is None:
                                reason = 'synthetic/sentinel-position reward or hidden event item'
                        elif offset not in by_offset:
                            reason = 'not proven reachable from script root 0'
                        if reason:
                            excluded.append(dict(d, reason=reason))
                            continue
                        for guards, limitation in by_offset[offset]:
                            if limitation:
                                excluded.append(dict(d, reason=limitation))
                                continue
                            # Room-local mutable state is never read for another room.
                            try:
                                projections = native.projections(pl, path.name, at)
                            except ValueError as error:
                                excluded.append(dict(d, reason=str(error)))
                                continue
                            for k, projection in enumerate(projections):
                                if k == 0 and (pl, path.name, item) in ITEM_MAP_POINT_OVERRIDES:
                                    projection['x'], projection['y'] = ITEM_MAP_POINT_OVERRIDES[pl, path.name, item]
                                result.append(dict(d, **projection, bit=bit, reward=raw[0] != 105 and at is not raw,
                                                   guards=[dict(bank=b, bit=i, value=v) for b, i, v in guards]))
    # The third Small Key is behind an unsupported local-state branch in Leon's
    # sewer room. Its in-game availability is Leon B only; preserve its native
    # pickup location but use that verified scenario gate instead of guessing
    # the local room condition for map rendering.
    sewer_overrides = {
        (73, 3866): [],       # Leon A/B Wolf Medal, held by the soldier
        (31, 3896): [(1, 1, 1)],  # Leon B Small Key #3
    }
    for (item, offset), guards in sewer_overrides.items():
        matches = [d for d in excluded if (d['pl'], d['room'], d['section'], d['function'], d['offset'], d['item']) ==
                   (0, 'ROOM4050.RDT', 17, 0, offset, item)]
        assert len(matches) == 1 and matches[0]['reason'] == 'unsupported condition/local room state'
        d = matches[0]
        excluded.remove(d)
        raw = bytes.fromhex(d['raw'])
        result.append(dict(d, **native.project(0, d['room'], raw), bit=struct.unpack_from('<H', raw, 18)[0],
                           guards=[dict(bank=b, bit=i, value=v) for b, i, v in guards]))
    # Leon A/B Rook Plug uses duplicated AOT setup records guarded by local room state.
    rook = [d for d in excluded if (d['pl'], d['room'], d['section'], d['function'], d['item']) ==
            (0, 'ROOM20E0.RDT', 17, 0, 60)]
    assert len(rook) == 2 and all(d['reason'] == 'unsupported condition/local room state' for d in rook)
    for d in rook:
        excluded.remove(d)
        raw = bytes.fromhex(d['raw'])
        projection = native.project(0, d['room'], raw)
        assert (projection['floor'], projection['x'], projection['y'], projection['seen']) == (2, 176, 90, 44)
        result.append(dict(d, **projection, bit=struct.unpack_from('<H', raw, 18)[0], guards=[]))
    # Claire A/B's Eagle Stone uses the same Interrogation Room shelf and local
    # branch shape; the character-specific item replaces the Leon-only Rook Plug.
    eagle = [d for d in excluded if (d['pl'], d['room'], d['section'], d['function'], d['item']) ==
             (1, 'ROOM20E1.RDT', 17, 0, 58)]
    assert len(eagle) == 2 and all(d['reason'] == 'unsupported condition/local room state' for d in eagle)
    for d in eagle:
        excluded.remove(d)
        raw = bytes.fromhex(d['raw'])
        projection = native.project(1, d['room'], raw)
        assert (projection['floor'], projection['x'], projection['y'], projection['seen']) == (2, 176, 90, 44)
        result.append(dict(d, **projection, bit=struct.unpack_from('<H', raw, 18)[0], guards=[]))
    result.extend(extract_area_maps(native))
    zapping = extract_zapping(native)
    # 214 Armory SMG reward is already the zapping marker; keep one.
    result = [d for d in result if not (d.get('reward') and any((z['pl'], z['item']) == (d['pl'], d['item']) for z in zapping))]
    result.extend(zapping)
    # Coalesce repeated AOT initializers while preserving alternative predicates.
    groups = collections.defaultdict(list)
    for d in result:
        groups[tuple(d[k] for k in ('pl', 'room', 'item', 'bank', 'bit', 'x', 'y'))].append(d)
    result = []
    for rows in groups.values():
        guard_sets = collapse_switch(tuple((g['bank'], g['bit'], g['value']) for g in d['guards']) for d in rows)
        scenario_gate = SCENARIO_GATES.get((rows[0]['item'], rows[0]['pl']))
        if scenario_gate is None:
            scenario_gate = SCENARIO_GATES.get((rows[0]['item'], None))
        if scenario_gate is not None:
            guard_sets = [g for guard in guard_sets
                          if (g := normalized(guard + ((1, 1, scenario_gate),))) is not None]
        for guards in sorted(guard_sets):
            result.append(dict(rows[0], merged=sorted({d['offset'] for d in rows}),
                               guards=[dict(bank=b, bit=i, value=v) for b, i, v in guards]))
    provenance = dict(exe_sha256=hashlib.sha256(native.blob).hexdigest(),
                      sources=sources, parse_failures=failures,
                      counts=dict(included=len(result), excluded=len(excluded)),
                      pickup_flag='Regular items: bank8 for stage<4, bank34 otherwise, GlobalId ushort+18; wall maps use verified physical bank4/8/34 flags; MSB-first DWORD',
                      area_maps='area-maps.json; EXE and RDT hashes verified')
    return result, excluded, provenance


def extract_zapping(native):
    result = []
    for room, item, (x, z, w, h), bank, bit, guards in ZAPPING:
        for pl in (0, 1):
            name = f'ROOM{room}{pl}.RDT'
            raw = bytes(6) + struct.pack('<hhhh', x, z, w, h)  # projector reads nFloor raw[4] and x,z,w,h at +6
            p = native.project(pl, name, raw)
            result.append(dict(pl=pl, room=name, section=17, function=-1, offset=-1, raw=raw.hex(), item=item,
                               name=NAMES[item][0], name_ko=NAMES[item][1], floor=p['floor'], seen=p['seen'],
                               x=p['x'], y=p['y'], bank=bank, bit=bit,
                               guards=[dict(bank=b, bit=i, value=v) for b, i, v in guards]))
    return result


def write_outputs(result, excluded, provenance):
    for name, value in (('item-locations.json', result), ('item-locations-excluded.json', excluded),
                        ('item-locations-provenance.json', provenance)):
        (R / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    guards, rows = [], []
    for d in result:
        start = len(guards)
        guards.extend(d['guards'])
        rows.append('{%s},' % ','.join(str(d[k]) for k in ('pl', 'floor', 'x', 'y', 'seen', 'item', 'bank', 'bit')) .__add__(f',{start},{len(d["guards"])}'))
    lines = ['/* Generated by extract_items.py; see items-report.md. */', '#ifndef RE2_MAP_ITEMS_H', '#define RE2_MAP_ITEMS_H',
             'typedef struct { unsigned char bank,bit,value; } MapItemGuard;',
             'typedef struct { unsigned char pl,floor; short x,y; unsigned char seen,item,bank; unsigned short bit,guard_start; unsigned char guard_count; } MapItem;',
             'static const MapItemGuard map_item_guards[] = {']
    lines += ['{%d,%d,%d},' % (g['bank'], g['bit'], g['value']) for g in guards] or ['{0,0,0},']
    lines += ['};', 'static const MapItem map_items[] = {'] + rows + ['};', '#endif', '']
    (R / 'items.h').write_text('\n'.join(lines))


FLOOR_INPUTS = ((0x989ff6, 1), (0x989ed0, 4), (0x98eb4c, 32), (0x98eb1a, 2), (0x692fac, 1), (0x4fb198, 28))


def check_floor_inputs(native):
    """Regression guard: 0x4faf80 must read only the state NativeMap.FLOOR_STATES varies (plus its jump table).
    A different EXE or a new floor rule (another flag, variable or room) fails here instead of silently
    dropping markers from a sub-floor map (user 2026-10-19: Vacant Factory 1F lift deck, Up Key panel)."""
    from unicorn import UC_HOOK_MEM_READ
    reads = set()
    hook = native.u.hook_add(UC_HOOK_MEM_READ, lambda uc, access, address, size, value, data: reads.add((address, size)))
    try:
        for stage in range(7):
            for room in range(0x30):
                native.floors(0, stage, room, 0)
                native.floors(1, stage, room, 4)
    finally:
        native.u.hook_del(hook)
    stray = {(a, s) for a, s in reads if not 0x20000000 <= a < 0x20010000
             and not any(base <= a and a + s <= base + n for base, n in FLOOR_INPUTS)}
    assert not stray, ('0x4faf80 reads state outside FLOOR_INPUTS', sorted(hex(a) for a, s in stray))
    bits = {a for a, s in reads if 0x98eb4c <= a < 0x98eb4c + 32}
    assert bits <= {0x98eb4c + n // 32 * 4 for n in (98, 99, 137, 190)}, sorted(hex(a) for a in bits)


def item_opcodes(native):
    """SCD opcodes whose handler both registers an AOT (0x988850) and reads the item pickup bank pointers."""
    ops = set()
    for op in range(0x8f):
        va = struct.unpack('<I', native.read(0x53ae10 + op * 4, 4))[0]
        try:
            code = native.read(va, 0x100)
        except ValueError:
            continue
        refs = lambda a: struct.pack('<I', a) in code
        if refs(0x988850) and (refs(0x53b238) or refs(0x53b2a0)):
            ops.add(op)
    return ops


def audit(result, excluded, provenance):
    """Fail the build instead of silently dropping pickups (recurring misses: 0x8D, switch, storey compare)."""
    native = NativeMap((G / 'Resident Evil 2.exe').read_bytes())
    assert item_opcodes(native) == set(ITEM_OPS) | DOOR_OPS, ('AOT opcodes reading item banks changed', sorted(item_opcodes(native)))
    assert not provenance['parse_failures'], provenance['parse_failures'][:5]
    sizes = json.loads((R / 'opcode-sizes.json').read_text())['sizes']
    seen = {(d['pl'] & 1, d['room'], d['section'], o) for d in result + excluded if 'offset' in d
            for o in d.get('merged', [d['offset']])}
    missing = []
    for pl in (0, 1):
        for path in sorted((G / f'Pl{pl}/Rdt').glob('*.RDT')):
            blob = path.read_bytes()
            for section in (16, 17):
                for ops in parse_functions(blob, section, sizes):
                    for offset, raw in ops.items():
                        if raw[0] in ITEM_OPS and struct.unpack_from('<H', raw, 22 if raw[0] == 105 else 14)[0] in NAMES \
                                and not (raw[0] != 105 and raw[14] == 17 and path.name[4].isdigit()) \
                                and (pl, path.name, section, offset) not in seen:
                            missing.append((pl, path.name, section, offset))
    assert not missing, ('item AOTs neither extracted nor excluded', missing[:10])
    # Script constructs the walker cannot model are reviewed once; any NEW one fails here with its location.
    silent = ('unsupported condition/local room state', 'not proven reachable from script root 0',
              'not a regular interactive floor pickup',
              'projection outside native room rectangle', 'no native room projection')
    now = sorted({(d['pl'], d['room'], d['offset'], d['item'], d['reason']) for d in excluded if d['reason'] in silent})
    approved_path = R / 'excluded-approved.json'
    approved = {tuple(x) for x in json.loads(approved_path.read_text())} if approved_path.exists() else None
    new = [x for x in now if approved is not None and x not in approved]
    assert not new, ('new unexplained pickup exclusions; fix the walker or approve in excluded-approved.json', new)
    return now


def self_check():
    sw = [((131, 1, 0), (131, 2, 0), (131, 3, 0)), ((131, 1, 1),), ((131, 2, 1),), ((131, 3, 1),)]
    assert collapse_switch(sw) == [()] and collapse_switch(sw[1:]) != [()]
    assert collapse_switch([g + ((130, 3, 1),) for g in sw]) == [((130, 3, 1),)]
    assert minimize([((4, 18, 1),), ((4, 18, 0),)]) == [()]
    assert minimize([((1, 1, 0), (4, 18, 1)), ((1, 1, 0), (4, 18, 0)), ((1, 1, 1), (3, 2, 1))]) in (
        [((1, 1, 0),), ((1, 1, 1), (3, 2, 1))], [((1, 1, 1), (3, 2, 1)), ((1, 1, 0),)])


if __name__ == '__main__':
    self_check()
    check_floor_inputs(NativeMap((G / 'Resident Evil 2.exe').read_bytes()))
    result, excluded, provenance = extract()
    assert result and {0, 1} <= {d['pl'] for d in result} <= {0, 1, 2, 3}
    assert all(d['bank'] in (4, 8, 34, ZAPPING_BANK, 255) and d['bit'] < 256 for d in result)
    from snap_inside import snap
    print('items snapped into room shape:', len(snap(result)))
    write_outputs(result, excluded, provenance)
    audit(result, excluded, provenance)
    print(json.dumps(dict(included=len(result), excluded=len(excluded), parse_failures=len(provenance['parse_failures']),
                          items=sorted({d['item'] for d in result})), indent=2))
