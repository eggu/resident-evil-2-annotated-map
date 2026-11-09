"""v6.2 data: every floor pickup per room (room tint) + typewriter/item-box AOTs (map icons).

Reuses extract_items.py's verified opcode parser, structured walker and native
projection; extract_items.py/items.h (core labels) stay unchanged.
Native facts (EXE 21b2a647):
  op 78  ITEM_AOT_SET    handler 0x4E52E0: item ushort+14, pickup flag ushort+18
  op 105 ITEM_AOT_SET_4P handler 0x4E5520: item ushort+22, pickup flag ushort+26
  both: bank8 (0x98EBB4) if stage<4 else bank34 (0x98EBD4) via 0x53B218, checker 0x503170
  op 44  AOT_SET (20 bytes) / op 103 AOT_SET_4P (28 bytes): byte+2 = SCE type;
         SCE 9 = typewriter (save), SCE 10 = item box.
"""
from pathlib import Path
import collections
import json
import struct

import marker_names
from extract_items import G, R, NativeMap, minimize, normalized, parse_functions, walk, room_paths, stage_of, mode_pl

SCE_SAVE, SCE_ITEMBOX = 9, 10
SCE_FLAG_CHG, SCE_WATER = 6, 7
SCE_EVENT = 5


def number_lock_bit(functions, raw):
    """AOT_RESET numeric lock: four FG_ROOM digit checks followed by one permanent completion bit."""
    if raw[2] != SCE_EVENT or not raw[3] & 0x10 or raw[6] != 0x18 or raw[7] >= len(functions):
        return None
    ops = functions[raw[7]].values()
    cleared = {r[2] for r in ops if r[0] == 0x22 and r[1] == 5 and r[3] == 0}
    if not {5, 6, 7, 8} <= cleared:
        return None
    bits = {r[2] for r in ops if r[0] == 0x22 and r[1] == 4 and r[3] == 1}
    return next(iter(bits)) if len(bits) == 1 else None


def puzzle_spot(op, raw):
    """Map puzzle/device marker: SCE_FLAG_CHG of the item-use type (first data byte 10) asking for a key item.

    Verified against re-scd (pl0/pl1 *.lst): e.g. 408 Valve Handle `2C03062101007F20E5063408D0070A0032000100`.
    SCE_WATER (7) is a wading zone and other FLAG_CHG types (5/9/0x23) are floor triggers, not puzzles.
    """
    if raw[2] != SCE_FLAG_CHG:
        return False
    d = 14 if op == 44 else 22  # aot_set: x,z,w,h; aot_set_4p: four corners
    # Item-locked doors are locks (doors-all.h, project_all.py), not puzzles: 52 Armory Red Card reader,
    # 75 Kennel manhole, 59-62 Plug Passage chess-plug panel.
    return raw[d] == 10 and 47 <= raw[d + 2] <= 99 and raw[d + 2] not in (52, 59, 60, 61, 62, 75)
def evidence(op, raw):
    """Marker-name evidence of an item-use puzzle AOT: the key item it asks for ('i<id>'); None for other AOTs."""
    return f'i{raw[(14 if op == 44 else 22) + 2]}' if puzzle_spot(op, raw) else None


EVENT_KIND = 20  # MapInteraction.kind of an event marker (spoiler story scene)
OP_MOVIE = 111   # Movie_on: plays an FMV, the argument is the movie id
EVENT_REPORT = []  # cutscene functions that could not be given a marker, with the reason


def callee(r):
    """Function a Gosub (0x18) or Evt_exec (0x04 ... 0x18 fn) instruction calls, else None."""
    return r[1] if r[0] == 0x18 else r[3] if r[0] == 4 and len(r) > 3 and r[2] == 0x18 else None


def movie_functions(functions):
    """Indexes of the functions that play an FMV, directly or through calls."""
    found = {i for i, ops in enumerate(functions) if any(r[0] == OP_MOVIE for r in ops.values())}
    grew = True
    while grew:
        grew = False
        for i, ops in enumerate(functions):
            if i not in found and any(callee(r) in found for r in ops.values()):
                found.add(i); grew = True
    return found


OP_SAVE, TIMER_VAR = 0x24, 0x23  # Save(var, value): variable 0x23 is the countdown (300 s in 701 Train Platform and 617, 120 s in 703)


def timer_functions(functions):
    """Indexes of the functions that start the self-destruct countdown (Save(0x23, n > 0)), directly or through calls."""
    found = {i for i, ops in enumerate(functions)
             if any(r[0] == OP_SAVE and r[1] == TIMER_VAR and struct.unpack_from('<H', r, 2)[0] for r in ops.values())}
    grew = True
    while grew:
        grew = False
        for i, ops in enumerate(functions):
            if i not in found and any(callee(r) in found for r in ops.values()):
                found.add(i); grew = True
    return found


PERSISTENT_BANKS = (3, 4)  # FG_SCENARIO / FG_COMMON: kept across rooms (bank 5 is per room, 1/2 are transient)
BOSS_TYPES = {35, 39, 40, 42, 43, 44, 48, 49, 50, 51, 52, 53, 54, 55, 57, 58, 62}  # extract_monsters: alligator, G, Tyrant, plant 42, giant moth


def event_flag(functions, fn):
    """(bank, bit) a cutscene function sets as its 'scene played' flag: first persistent Set(.., 1) in it or its callees."""
    seen, stack = set(), [fn]
    while stack:
        f = stack.pop(0)
        if f in seen or f >= len(functions):
            continue
        seen.add(f)
        for r in functions[f].values():
            if r[0] == 0x22 and r[1] in PERSISTENT_BANKS and r[3] == 1:
                return r[1], r[2]
            if callee(r) is not None:
                stack.append(callee(r))
    return None


def caller_flag(functions, fn):
    """(bank, bit) a caller sets just before it starts the scene (Ck(b,x,0); Set(b,x,1); Evt_exec fn): the done flag when the
    scene function itself sets none. Looks at the 3 instructions before each call site."""
    for ops in functions:
        items = list(ops.values())
        for k, r in enumerate(items):
            if callee(r) == fn:
                for q in reversed(items[max(0, k - 3):k]):
                    if q[0] == 0x22 and q[1] in PERSISTENT_BANKS and q[3] == 1:
                        return q[1], q[2]
    return None


def event_bit(functions, fn):
    """The FG_COMMON bit a cutscene function sets (its 'scene played' flag): first bank-4 Set(.., 1) in it or its callees."""
    seen, stack = set(), [fn]
    while stack:
        f = stack.pop(0)
        if f in seen or f >= len(functions):
            continue
        seen.add(f)
        for r in functions[f].values():
            if r[0] == 0x22 and r[1] == 4 and r[3] == 1:
                return r[2]
            if callee(r) is not None:
                stack.append(callee(r))
    return None


def apply_resets(paths, resets):
    """Hide an AOT once the script disables it: `Aot_reset(id, type != item-use)` under condition C (e.g. Ck(4,36,1) in the
    room init, set by the scene that solved the puzzle) leaves the AOT visible only while C is false. `paths` and `resets` are
    lists of guard conjunctions; the result is the list of conjunctions under which the AOT is still live."""
    for conj in minimize(resets):
        if not conj:
            return []  # always reset: never live
        live = []
        for g in paths:
            for bank, bit, value in conj:
                n = normalized(tuple(g) + ((bank, bit, 1 - value),))
                if n is not None and n not in live:
                    live.append(n)
        paths = minimize(live)
    return paths


def puzzle_completion(functions):
    """A device disabled by the same routine that sets one permanent progress bit is complete at that bit."""
    found = collections.defaultdict(set)
    for ops in functions:
        bits = {r[2] for r in ops.values() if r[0] == 0x22 and r[1] == 4 and r[3] == 1}
        if len(bits) == 1:
            for r in ops.values():
                if r[0] == 70 and r[2] == 0:
                    found[r[1]].update(bits)
    return {aot: next(iter(bits)) for aot, bits in found.items() if len(bits) == 1}


def switch_bit(functions, raw, follow_calls=False):
    """[5] device marker without an item (e.g. 605 power switch, user 2026-10-23): a press-to-use (SAT MANUAL) event
    AOT whose gosub target both tests and sets the same FG_COMMON (bank 4) bit, i.e. a one-shot progress switch.
    605 func 5: ck(4,145,0) -> message; else set(4,145,1). Returns the last such bit (hide once set), or None."""
    if raw[2] != SCE_EVENT or not raw[3] & 0x10 or raw[16] != 0x18 or raw[17] >= len(functions):
        return None
    ops = [r for _, r in sorted(functions[raw[17]].items())]
    tested = {r[2] for r in ops if r[0] == 0x21 and r[1] == 4}
    bits = [r[2] for r in ops if r[0] == 0x22 and r[1] == 4 and r[3] == 1 and r[2] in tested]
    if bits:
        return bits[-1]
    if not follow_calls:
        return None
    # Some panels test in the interaction handler but set the bit in a called animation (700 gate: 3 -> 4).
    pending, visited, called = [raw[17]], set(), []
    while pending:
        fn = pending.pop()
        if fn in visited or fn >= len(functions):
            continue
        visited.add(fn)
        for r in functions[fn].values():
            called.append(r)
            if r[0] == 0x18:
                pending.append(r[1])
            elif r[0] == 4 and r[2] == 0x18:
                pending.append(r[3])
    candidates = {r[2] for r in called if r[0] == 0x22 and r[1] == 4 and r[3] == 1 and r[2] in tested}
    return next(iter(candidates)) if len(candidates) == 1 else None



# (pl, bank4 bit) already drawn as a lock: event locks (all-locks.json, e.g. 208 darkroom 175, 615 159) and
# project_all.ITEM_DOORS (211 Red Card 14, 21A manhole 59, 303 chess plugs 58 Leon only). No second marker there.
LOCK_BITS = {(d['pl'], d['key_id']) for d in json.loads((R / 'all-locks.json').read_text()) if d['kind'] == 'event'} | \
            {(0, 14), (1, 14), (0, 59), (1, 59), (0, 58)}
DOCUMENT_ITEM_IDS = {106, 107, 108, 109, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 125, 126}


def map_stage(room_name):
    # 0x4faf80 switches on stage 0..6 only; Extreme Battle's ROOMA..G are those stages (stage_of).
    if room_name[4] not in '1234567ABCDEFG':
        raise ValueError('stage outside native map switch')
    return stage_of(room_name)


class RoomMap(NativeMap):
    def project(self, pl, room_name, raw, floor=None):
        map_stage(room_name)
        return super().project(pl, room_name, raw, floor)

    def projections(self, pl, room_name, raw):
        map_stage(room_name)
        return super().projections(pl, room_name, raw)

    def rooms(self, pl, room_name, level=0):
        """Native floor/room-table lookup on every sub-floor (NativeMap.floors); level = AOT nFloor."""
        stage, room = map_stage(room_name), int(room_name[5:7], 16)
        out = []
        for floor in self.floors(pl, stage, room, level):
            index = self.call(0x4fb1c0, floor, room)
            if not 0 <= floor < 20:
                continue
            ptr, count = struct.unpack('<IB', self.read((0x53eb98 if pl else 0x53eaf8) + floor * 8, 5))
            if index < count:
                out.append(dict(floor=floor, seen=self.read(ptr + index * 16 + 12, 1)[0], bank=8 if stage < 4 else 34))
        if not out:
            raise ValueError('no native room entry')
        return out


def scan():
    sizes = json.loads((R / 'opcode-sizes.json').read_text())['sizes']
    assert (sizes[44], sizes[103], sizes[78], sizes[105]) == (20, 28, 22, 30)
    native = RoomMap((G / 'Resident Evil 2.exe').read_bytes())
    assert native.read(0x53ae10 + 105 * 4, 4) == struct.pack('<I', 0x4e5520)
    pickups, markers, documents, interactions, excluded = [], [], [], [], []
    for pl in (0, 1):
        for path in sorted((G / f'Pl{pl}/Rdt').glob('*.RDT')):
            blob = path.read_bytes()
            completion = {}
            file_resets = collections.defaultdict(list)  # AOT id -> guard conjunctions under which the script disables it
            for section in (16, 17):
                try:
                    fns = parse_functions(blob, section, sizes)
                except (AssertionError, ValueError, struct.error):
                    continue
                if fns:
                    completion.update(puzzle_completion(fns))
                    for offset, raw, guards, why in room_paths(fns, pl, path.name, section, wanted=(70,)):
                        if raw[0] == 70 and raw[2] != SCE_FLAG_CHG and not why:
                            file_resets[raw[1]].append(tuple(guards))
            for section in (16, 17):
                try:
                    functions = parse_functions(blob, section, sizes)
                except (AssertionError, ValueError, struct.error):
                    continue  # same parse failures as items-report.md
                if not functions:
                    continue
                reach = collections.defaultdict(list)
                movies = movie_functions(functions) | timer_functions(functions)  # scenes, and the countdown start (701, 2026-11-09)
                triggered = set()
                for offset, raw, guards, why in room_paths(functions, pl, path.name, section, wanted=(44, 70, 78, 103, 105, 141)):
                    reach[offset].append((guards, why))
                for ops in functions:
                    for offset, raw in ops.items():
                        op = raw[0]
                        d = dict(pl=mode_pl(pl, path.name), room=path.name, section=section, offset=offset, op=op)
                        if op in (78, 105, 141) and raw[2] == 2:  # 141 = Extreme Battle ITEM_AOT_SET, 0x4E layout
                            item = struct.unpack_from('<H', raw, 22 if op == 105 else 14)[0]
                            bit = struct.unpack_from('<H', raw, 26 if op == 105 else 18)[0]
                            pos = struct.unpack_from('<hh', raw, 6)
                            reason = ('empty item id' if not item else
                                      'synthetic/sentinel-position event item' if op != 105 and (pos == (0, 0) or max(map(abs, pos)) >= 30000) else
                                      'not proven reachable from script root 0' if offset not in reach else '')
                            paths = [g for g, why in reach.get(offset, []) if not why]
                            if not reason and not paths:
                                reason = reach[offset][0][1]
                            if reason:
                                excluded.append(dict(d, item=item, reason=reason))
                                continue
                            try:
                                rooms = native.rooms(pl, path.name, raw[4])
                            except ValueError as error:
                                excluded.append(dict(d, item=item, reason=str(error)))
                                continue
                            room = rooms[0]
                            pickups += [dict(d, **r, item=item, bit=bit, guards=g) for r in rooms for g in paths]
                            # shortcut: only positioned standard pickups; include scripted/4P documents when their map coordinates are verified.
                            if item in DOCUMENT_ITEM_IDS and op == 78 and raw[3] == 0x31:
                                try:
                                    ps = native.projections(pl, path.name, raw)
                                except ValueError as error:
                                    excluded.append(dict(d, item=item, reason=str(error)))
                                else:
                                    documents += [dict(d, floor=p['floor'], seen=p['seen'], x=p['x'], y=p['y'],
                                                       bank=room['bank'], item=item, bit=bit, guards=g) for p in ps for g in paths]
                        elif op == 70:
                            bit = number_lock_bit(functions, raw)
                            if bit is None:
                                continue
                            # A reset changes only the action; its original AOT supplies the safe's coordinates.
                            bases = {r for fn in functions for r in fn.values() if r[0] in (44, 103) and r[1] == raw[1]}
                            if len(bases) != 1:
                                continue
                            base = next(iter(bases))
                            if base[0] != 44:
                                continue  # shortcut: no four-corner numeric lock in the supported room scripts.
                            paths = [v for g, why in reach.get(offset, []) if not why
                                     if (v := normalized(tuple(g) + ((4, bit, 0),))) is not None]
                            if not paths:
                                continue
                            try:
                                ps = native.projections(pl, path.name, base)
                            except ValueError as error:
                                excluded.append(dict(d, reason=str(error)))
                                continue
                            interactions += [dict(d, kind=SCE_FLAG_CHG, number_lock=bit, ev=f'nl{bit}', floor=p['floor'],
                                                  x=p['x'], y=p['y'], seen=p['seen'], guards=g) for p in ps for g in paths]
                        elif op == 44 and raw[2] in (SCE_SAVE, SCE_ITEMBOX):
                            # Icons are not guarded: typewriters/boxes are fixed room furniture.
                            if offset not in reach:
                                excluded.append(dict(d, sce=raw[2], reason='not proven reachable from script root 0'))
                                continue
                            try:
                                ps = native.projections(pl, path.name, raw)
                            except ValueError as error:
                                excluded.append(dict(d, sce=raw[2], reason=str(error)))
                                if str(error) == 'projection outside native room rectangle':
                                    markers.append(dict(d, kind=raw[2], fallback=True))  # anchored to a sibling icon below
                                continue
                            for p in ps:
                                markers.append(dict(d, kind=raw[2], floor=p['floor'], x=p['x'], y=p['y'], seen=p['seen']))
                                interactions.append(dict(d, kind=raw[2], floor=p['floor'], x=p['x'], y=p['y'], seen=p['seen'], guards=()))
                        elif op == 44:
                            # All other reachable AOTs are user-visible interaction targets.
                            if not offset in reach:
                                continue
                            if raw[2] == SCE_EVENT and raw[16] == 0x18 and raw[17] in movies and not switch_bit(functions, raw, follow_calls=path.name[4] == '7'):
                                # (an AOT that is also a one-shot switch stays a puzzle: the 703 Train Car lever plays a scene but is a device)
                                # Story scene (FMV): a purple event marker at its trigger, hidden once its progress flag is set.
                                triggered.add(raw[17])
                                bit = event_bit(functions, raw[17])
                                if bit is None:
                                    EVENT_REPORT.append(dict(pl=pl, room=path.name, fn=raw[17], reason='cutscene sets no FG_COMMON progress flag'))
                                    continue
                                try:
                                    ps = native.projections(pl, path.name, raw)
                                except ValueError as error:
                                    EVENT_REPORT.append(dict(pl=pl, room=path.name, fn=raw[17], reason=str(error)))
                                    continue
                                interactions += [dict(d, kind=EVENT_KIND, floor=p['floor'], x=p['x'], y=p['y'], seen=p['seen'],
                                                      guards=tuple(g) + ((4, bit, 0),), event_bit=bit) for p in ps for g, why in reach[offset]]
                                continue
                            bit = switch_bit(functions, raw, follow_calls=path.name[4] == '7') if path.name[4] in '1234567' else None  # not Extreme Battle / 4th Survivor
                            if raw[2] in (SCE_FLAG_CHG, SCE_WATER) and not puzzle_spot(op, raw):
                                continue
                            try:
                                ps = native.projections(pl, path.name, raw)
                            except ValueError as error:
                                excluded.append(dict(d, sce=raw[2], reason=str(error)))
                                continue
                            paths = apply_resets([g for g, why in reach[offset]], file_resets.get(raw[1], ()))
                            if puzzle_spot(op, raw) and raw[1] in completion:
                                paths = [v for g in paths if (v := normalized(tuple(g) + ((4, completion[raw[1]], 0),))) is not None]
                            if path.name[4:7] == '108' and puzzle_spot(op, raw):
                                # Rooftop function 7 sets FG_COMMON 0 when the water scene completes; init reset is conditional on the B encounter.
                                paths = [v for g in paths if (v := normalized(tuple(g) + ((4, 0, 0),))) is not None]
                            if path.name[4:7] == '702' and puzzle_spot(op, raw):
                                # 702 init/function 4 disables all four plug AOTs when FG_COMMON 136 is set.
                                paths = [v for g in paths if (v := normalized(tuple(g) + ((4, 136, 0),))) is not None]
                            interactions += [dict(d, kind=raw[2], floor=p['floor'], x=p['x'], y=p['y'], seen=p['seen'], guards=g,
                                                  ev=evidence(op, raw)) for p in ps for g in paths]
                            if bit is not None and (pl, bit) not in LOCK_BITS:  # drawn like an item-use puzzle spot until the switch flag is set
                                switch_guards = ((4, bit, 0),)
                                if path.name[4:7] == '700' and bit == 140:
                                    switch_guards += ((1, 1, 1),)  # Train gate panel is a scenario-B escape objective.
                                interactions += [dict(d, kind=SCE_FLAG_CHG, switch=bit, ev=f'sw{bit}', floor=p['floor'], x=p['x'], y=p['y'], seen=p['seen'],
                                                      guards=tuple(g) + switch_guards) for p in ps for g in paths]
                        elif op == 103:
                            # Four-corner triggers: project their bounding-box centre onto the native map.
                            if offset not in reach or (raw[2] in (SCE_FLAG_CHG, SCE_WATER) and not puzzle_spot(op, raw)):
                                continue
                            coords = struct.unpack_from('<8h', raw, 6)
                            x0, x1 = min(coords[0::2]), max(coords[0::2])
                            y0, y1 = min(coords[1::2]), max(coords[1::2])
                            rect = bytearray(raw[:14])
                            struct.pack_into('<hhhh', rect, 6, x0, y0, x1 - x0, y1 - y0)
                            try:
                                ps = native.projections(pl, path.name, rect)
                            except ValueError as error:
                                excluded.append(dict(d, sce=raw[2], reason='4-point ' + str(error)))
                                continue
                            if raw[2] == SCE_EVENT and raw[24] == 0x18 and raw[25] in movies:
                                # Four-corner story trigger (701 Train Platform: the self-destruct countdown starts here), same rule as the point AOT.
                                triggered.add(raw[25])
                                bit = event_bit(functions, raw[25])
                                if bit is None:
                                    EVENT_REPORT.append(dict(pl=pl, room=path.name, fn=raw[25], reason='cutscene sets no FG_COMMON progress flag'))
                                    continue
                                interactions += [dict(d, kind=EVENT_KIND, floor=p['floor'], x=p['x'], y=p['y'], seen=p['seen'],
                                                      guards=tuple(g) + ((4, bit, 0),), event_bit=bit) for p in ps for g, why in reach[offset]]
                                continue
                            paths = apply_resets([g for g, why in reach[offset]], file_resets.get(raw[1], ()))
                            if puzzle_spot(op, raw) and raw[1] in completion:
                                paths = [v for g in paths if (v := normalized(tuple(g) + ((4, completion[raw[1]], 0),))) is not None]
                            interactions += [dict(d, kind=raw[2], floor=p['floor'], x=p['x'], y=p['y'], seen=p['seen'], guards=g,
                                                  ev=evidence(op, raw)) for p in ps for g in paths]
                        elif op == 103 and raw[2] in (SCE_SAVE, SCE_ITEMBOX):
                            excluded.append(dict(d, sce=raw[2], reason='4-point AOT not projected'))
    room_scene_events(native, interactions)
    return pickups, markers, documents, interactions, excluded


def room_centres(native, pl, room_name):
    """[(floor, seen, x, y)]: the native room rectangle's centre on every map floor the room can be drawn on, as the marker
    origin (the map adds PROJ_CENTRE 6 when it draws, like for projected AOTs)."""
    stage, room = stage_of(room_name), int(room_name[5:7], 16)
    out = []
    for floor in native.floors(pl, stage, room, 0):
        index = native.call(0x4fb1c0, floor, room)
        if not 0 <= floor < 20:
            continue
        ptr, count = struct.unpack('<IB', native.read((0x53eb98 if pl else 0x53eaf8) + floor * 8, 5))
        if index >= count:
            continue
        record = native.read(ptr + index * 16, 16)
        w, h, rx, ry = record[2], record[3], *struct.unpack_from('<hh', record, 4)
        out.append((floor, record[12], rx + w // 2 - 6, ry + h // 2 - 6))
    return out


def room_scene_events(native, interactions):
    """Cutscenes the room's own script starts (no event AOT of its own): an event marker at the room's centre while their
    persistent done flag is unset. Rooms where a boss spawns (the boss keeps its enemy marker) and scenes without such a flag
    are listed in EVENT_REPORT instead."""
    sizes = json.loads((R / 'opcode-sizes.json').read_text())['sizes']
    for pl in (0, 1):
        for path in sorted((G / f'Pl{pl}/Rdt').glob('*.RDT')):
            blob = path.read_bytes()
            sections = {}
            for section in (16, 17):
                try:
                    sections[section] = parse_functions(blob, section, sizes)
                except (AssertionError, ValueError, struct.error):
                    continue
            functions = sections.get(17)
            if not functions:
                continue
            aots = {r[17] for ops in functions for r in ops.values() if r[0] == 44 and len(r) > 17 and r[2] == SCE_EVENT and r[16] == 0x18}
            movie_fns = {i for i, ops in enumerate(functions) if any(r[0] == OP_MOVIE for r in ops.values())}
            boss = any(r[0] in (68, 142) and r[3] in BOSS_TYPES for fns in sections.values() for ops in fns for r in ops.values())
            for fn in sorted(movie_fns):
                if any(fn in movie_functions_from(functions, a) for a in aots):
                    continue  # started by an event AOT: handled as an AOT event (or a puzzle)
                note = dict(pl=pl, room=path.name, fn=fn, movie=sorted({r[1] for r in functions[fn].values() if r[0] == OP_MOVIE}))
                flag = event_flag(functions, fn) or caller_flag(functions, fn)
                if boss:
                    EVENT_REPORT.append(dict(note, reason='a boss spawns in this room: entering starts the fight, the boss keeps its enemy marker'))
                elif flag is None:
                    EVENT_REPORT.append(dict(note, reason='no persistent (FG_SCENARIO/FG_COMMON) done flag'))
                else:
                    try:
                        centres = room_centres(native, pl, path.name)
                    except ValueError as error:
                        EVENT_REPORT.append(dict(note, reason=str(error)))
                        continue
                    for floor, seen, x, y in centres:
                        interactions.append(dict(pl=mode_pl(pl, path.name), room=path.name, section=17, offset=0, op=111, kind=EVENT_KIND,
                                                 floor=floor, x=x, y=y, seen=seen, guards=((flag[0], flag[1], 0),), event_bit=flag[1],
                                                 event_bank=flag[0], room_anchor=True))


def untriggered_movies():
    """Cutscene functions with no event AOT of their own (started by the room script or another scene): listed, never invented."""
    sizes = json.loads((R / 'opcode-sizes.json').read_text())['sizes']
    rows = []
    for pl in (0, 1):
        for path in sorted((G / f'Pl{pl}/Rdt').glob('*.RDT')):
            try:
                functions = parse_functions(path.read_bytes(), 17, sizes)
            except (AssertionError, ValueError, struct.error):
                continue
            movies = movie_functions(functions)
            direct = {i for i, ops in enumerate(functions) if any(r[0] == OP_MOVIE for r in ops.values())}
            aots = {r[17] for ops in functions for r in ops.values() if r[0] == 44 and len(r) > 17 and r[2] == SCE_EVENT and r[16] == 0x18}
            for fn in sorted(direct):
                ids = sorted({r[1] for r in functions[fn].values() if r[0] == OP_MOVIE})
                if not any(fn in movie_functions_from(functions, a) for a in aots):
                    rows.append(dict(pl=pl, room=path.name, fn=fn, movie=ids, reason='not started by an event AOT of its own (room script or another scene)'))
    return rows


def movie_functions_from(functions, start):
    seen, stack = set(), [start]
    while stack:
        f = stack.pop()
        if f in seen or f >= len(functions):
            continue
        seen.add(f)
        stack += [c for r in functions[f].values() if (c := callee(r)) is not None]
    return seen


def coalesce(pickups, markers, documents, interactions):
    groups = collections.defaultdict(list)
    for d in pickups:
        groups[d['pl'], d['floor'], d['seen'], d['bank'], d['bit']].append(d)
    rows = []
    for key, ds in sorted(groups.items()):
        for guards in sorted(minimize(tuple(g) for g in (d['guards'] for d in ds))):
            rows.append(dict(pl=key[0], floor=key[1], seen=key[2], bank=key[3], bit=key[4], guards=list(guards),
                             items=sorted({d['item'] for d in ds}), rooms=sorted({d['room'] for d in ds})))
    by_room = {(m['pl'], m['room'][:7]): m for m in markers if not m.get('fallback')}
    resolved = []
    for m in markers:
        if m.get('fallback'):
            sibling = by_room.get((m['pl'], m['room'][:7]))
            if not sibling:
                continue  # stays in excluded only
            m = dict(m, floor=sibling['floor'], seen=sibling['seen'], x=sibling['x'], y=sibling['y'], anchored_to=sibling['kind'])
        resolved.append(m)
    markers = resolved
    icons = {}
    for m in markers:  # one icon per (room, kind); first AOT in file order is the anchor
        icons.setdefault((m['pl'], m['floor'], m['seen'], m['kind']), m)
    doc_groups = collections.defaultdict(list)
    for d in documents:
        doc_groups[tuple(d[k] for k in ('pl', 'floor', 'seen', 'x', 'y', 'bank', 'item', 'bit'))].append(tuple(d['guards']))
    docs = []
    for key, paths in sorted(doc_groups.items()):
        for guards in sorted(minimize(paths)):
            docs.append(dict(zip(('pl', 'floor', 'seen', 'x', 'y', 'bank', 'item', 'bit'), key), guards=list(guards)))
    int_groups, int_ev = collections.defaultdict(list), collections.defaultdict(set)
    for d in interactions:
        key = tuple(d[k] for k in ('pl','floor','seen','kind','x','y'))
        int_groups[key].append(tuple(d['guards']))
        if d['kind'] == SCE_FLAG_CHG:
            int_ev[key].add((d['room'][4:7], d['ev']))
    int_rows = []
    for key, paths in sorted(int_groups.items()):
        unknown = [e for e in int_ev.get(key, ()) if e not in marker_names.RULES and e not in marker_names.UNRESOLVED]
        assert not unknown, ('puzzle evidence missing from data/marker_names.json (name it or list it as unresolved)', unknown)
        name = marker_names.puzzle_name_id(int_ev.get(key, ()))
        for guards in sorted(minimize(paths)):
            int_rows.append(dict(zip(('pl','floor','seen','kind','x','y'), key), guards=list(guards), name=name))
    return rows, [icons[k] for k in sorted(icons)], docs, int_rows


def write(rows, icons, documents, interactions, excluded):
    from snap_inside import snap
    moved = snap(icons) + snap(documents) + snap(interactions)
    far = [m for m in moved if max(abs(m[1][0] - m[2][0]), abs(m[1][1] - m[2][1])) > 3 and
           any(i['kind'] == SCE_FLAG_CHG and (i['pl'], i['floor'], i['seen']) == m[0] for i in interactions)]
    print('snapped into room shape:', len(moved), 'drawn puzzle markers moved >3px:', far)
    guards, lines = [], []
    for r in rows:
        lines.append('{%d,%d,%d,%d,%d,%d,%d}, /* %s items %s */' % (
            r['pl'], r['floor'], r['seen'], r['bank'], r['bit'], len(guards), len(r['guards']),
            ','.join(x[:-4] for x in r['rooms']), ','.join(map(str, r['items']))))
        guards += r['guards']
    doc_guards, doc_lines = [], []
    for d in documents:
        doc_lines.append('{%d,%d,%d,%d,%d,%d,%d,%d,%d,%d},' % (
            d['pl'], d['floor'], d['seen'], d['bank'], d['item'], d['x'], d['y'], d['bit'], len(doc_guards), len(d['guards'])))
        doc_guards += d['guards']
    interaction_guards, interaction_lines = [], []
    for d in interactions:
        interaction_lines.append('{%d,%d,%d,%d,%d,%d,%d,%d,%d},' % (
            d['pl'],d['floor'],d['seen'],d['kind'],d['x'],d['y'],len(interaction_guards),len(d['guards']),d.get('name', 0)))
        interaction_guards += d['guards']
    out = ['/* Generated by extract_overlay.py: room pickups, furniture icons, documents, and interaction markers. */',
           '#ifndef RE2_OVERLAY_DATA_H', '#define RE2_OVERLAY_DATA_H',
           'typedef struct { unsigned char pl,floor,seen,bank; unsigned short bit,guard_start; unsigned char guard_count; } RoomPickup;',
           'typedef struct { unsigned char pl,floor,seen,kind; short x,y; } MapMarker; /* kind 9 typewriter, 10 item box */',
           'typedef struct { unsigned char pl,floor,seen,bank,item; short x,y; unsigned short bit,guard_start; unsigned char guard_count; } MapDocument;',
           'typedef struct { unsigned char pl,floor,seen,kind; short x,y; unsigned short guard_start; unsigned char guard_count,name; } MapInteraction; /* name: item_labels id of a named puzzle, else 0 */',
           'static const MapItemGuard interaction_guards[] = {']
    out += ['{%d,%d,%d},' % g for g in interaction_guards] or ['{0,0,0},']
    out += ['};', 'static const MapInteraction map_interactions[] = {'] + interaction_lines + ['};',
           'static const MapItemGuard document_guards[] = {']
    out += ['{%d,%d,%d},' % g for g in doc_guards] or ['{0,0,0},']
    out += ['};', 'static const MapDocument map_documents[] = {'] + doc_lines + ['};',
            'static const MapItemGuard room_pickup_guards[] = {']
    out += ['{%d,%d,%d},' % g for g in guards] or ['{0,0,0},']
    out += ['};', 'static const RoomPickup room_pickups[] = {'] + lines + ['};', 'static const MapMarker map_markers[] = {']
    out += ['{%d,%d,%d,%d,%d,%d}, /* %s */' % (m['pl'], m['floor'], m['seen'], m['kind'], m['x'], m['y'], m['room'][:-4])
            for m in icons]
    out += ['};', '#endif', '']
    (R / 'overlay_data.h').write_text('\n'.join(out))
    (R / 'overlay-data.json').write_text(json.dumps(dict(room_pickups=rows, markers=icons, documents=documents, interactions=interactions, excluded=excluded),
                                                    indent=1, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    pickups, markers, documents, interactions, excluded = scan()
    assert not any(d['room'][4:7] == '116' and d['kind'] in (6, 7) for d in interactions)
    assert any(d['room'] in ('ROOM2000.RDT', 'ROOM2001.RDT') and d['kind'] == 6 and
               (d['floor'], d['x'], d['y']) == (2, 149, 126) for d in interactions)
    switches = {(d['room'][4:7], d['switch']) for d in interactions if 'switch' in d}
    assert ('605', 145) in switches and len({r for r, _ in switches}) <= 16, switches  # B3 power switch; no event-flood
    raw_events = [d for d in interactions if d['kind'] == EVENT_KIND]
    rows, icons, documents, interactions = coalesce(pickups, markers, documents, interactions)
    assert rows and icons and {0, 1} <= {r['pl'] for r in rows} <= {0, 1, 2, 3}
    assert all(r['bank'] in (8, 34) and r['bit'] < 256 and all(g[0] <= 34 or g[0] in (130, 131) for g in r['guards']) for r in rows)
    assert interactions and {0, 1} <= {d['pl'] for d in interactions} <= {0, 1, 2, 3}
    write(rows, icons, documents, interactions, excluded)
    rk, re_ = (json.loads((R / f'room_names-{l}.json').read_text()) for l in ('ko', 'en'))
    drawn = [dict(pl=d['pl'], room=d['room'][4:7], room_ko=rk.get(d['room'][4:7]), room_en=re_.get(d['room'][4:7]), floor=d['floor'], x=d['x'], y=d['y'],
                  hidden_by_bit=f"bank {d.get('event_bank', 4)} bit {d['event_bit']}", anchored_at_room_centre=bool(d.get('room_anchor'))) for d in raw_events]
    listed = [dict(r, room=r['room'][4:7], room_ko=rk.get(r['room'][4:7]), room_en=re_.get(r['room'][4:7])) for r in EVENT_REPORT]
    (R / 'events-report.json').write_text(json.dumps(dict(
        method='FMV scenes (script op 111, Movie_on) started by an event AOT (SCE 5, gosub) get a purple event marker at the AOT, hidden once the first FG_COMMON bit the scene sets is set. Scenes with no AOT of their own, or without such a bit, are listed, not drawn.',
        drawn=drawn, not_drawn=listed), ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(dict(pickup_aots=len(pickups), room_pickup_rows=len(rows), icons=len(icons),
                          save=sum(m['kind'] == SCE_SAVE for m in icons), itembox=sum(m['kind'] == SCE_ITEMBOX for m in icons), documents=len(documents), interactions=len(interactions),
                          excluded=collections.Counter(e['reason'] for e in excluded))))
