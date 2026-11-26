"""Generate src/layouts.h: native addresses of the Steam 1998 builds, keyed by the GOG addresses the runtime uses.

Steam ships packed executables, so this reads memory dumps taken after unpacking (0x400000.., flat, one file per
build). LeonU was mapped from GOG by hand (instruction alignment of the map, status, renderer and floor functions,
cross-checked by content: floor/door/bank tables, texture descriptor vtable). The other builds are derived from
LeonU by unique masked-instruction matches, so a key that is missing or ambiguous in a build stops the generator.

  python tools/steam_layouts.py DUMPS_DIR   # LeonU.bin ClaireU.bin ... LeonS.bin ClaireS.bin (U J F G I S)
"""
from pathlib import Path
import re, struct, sys
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
from capstone.x86 import X86_GRP_CALL, X86_GRP_JUMP, X86_OP_IMM, X86_OP_MEM

ROOT = Path(__file__).resolve().parents[1]
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# GOG key -> LeonU address. Functions and hook sites first, then data.
LEONU = {
    0x4021c0: 0x402f60, 0x405ec0: 0x4070c0, 0x416be0: 0x4199d0, 0x440280: 0x4fc860, 0x441170: 0x4fd740,
    0x4ed950: 0x4f12a0, 0x4fa7d0: 0x500a90, 0x4fa990: 0x500c30, 0x4faf80: 0x501220, 0x503170: 0x5097c0,
    0x4fa552: 0x5007e3, 0x4fb60b: 0x5018c8, 0x4fb7e7: 0x501ab7, 0x4faf38: 0x5011e7, 0x4faf3f: 0x5011ee,
    0x4fb4e6: 0x5017b6, 0x4fb5aa: 0x50187a, 0x4fa465: 0x5006f6,
    0x5173fc: 0x51f928, 0x524e1c: 0x5479e0, 0x524e20: 0x5479e4, 0x53b218: 0x5451f0, 0x53da70: 0x547ac0,
    0x53dae0: 0x547b30, 0x53dae4: 0x547b34, 0x53eaf8: 0x548ac8, 0x53eb98: 0x548ac8, 0x67c7d8: 0x68ff00,
    0x680588: 0x694244, 0x6805b8: 0x6942ac, 0x8c28f8: 0x8ccef8,
    **{k: k + 0xa600 for k in (0x691f61, 0x691f62, 0x691f7a, 0x691f88, 0x691fb8, 0x691fba, 0x9885fc, 0x988608,
                               0x989ed0, 0x989ef8, 0x98e9ba, 0x98e9bc, 0x98eae4, 0x98eb14, 0x98eb16, 0x98ec00,
                               0x98ec04, 0x98ec1c, 0x98ed2c)},
}
CODE = {k for k in LEONU if k < 0x510000}
SITES = {0x4fa552: 5, 0x4fb60b: 5, 0x4fb7e7: 5, 0x4faf38: 12, 0x4fb4e6: 6, 0x4fa465: 6}
FUNCS = {0x4021c0, 0x405ec0, 0x416be0, 0x440280, 0x441170, 0x4ed950, 0x4fa7d0, 0x4fa990, 0x4faf80, 0x503170}
# Each build is one character: GOG keeps both in one EXE and reads the player from the flag word's bit 31.
PLAYER = {f'{who}{lang}': pl for lang in 'UJFGIS' for who, pl in (('Leon', 0), ('Claire', 1))}
DEVICE = 0x5f1c  # Marni texture device, GOG 0x8c8338; read again from each build's create function below


def insns(img, va, n):
    out = []
    for i in md.disasm(img[va - 0x400000:va - 0x400000 + 16 * n], va):
        out.append(i)
        if len(out) == n:
            break
    return out


def absolute(i):
    return [op.imm if op.type == X86_OP_IMM else op.mem.disp for op in i.operands
            if (op.type == X86_OP_IMM and op.imm >= 0x400000) or (op.type == X86_OP_MEM and op.mem.disp >= 0x400000)]


def pattern(img, va, n):
    """n instructions at va as a regex, absolute and relative operands wildcarded."""
    out = b''
    for i in insns(img, va, n):
        mask = [False] * i.size
        e = i.encoding
        if (i.group(X86_GRP_JUMP) or i.group(X86_GRP_CALL)) and i.operands[0].type == X86_OP_IMM:
            mask[e.imm_offset:] = [True] * (i.size - e.imm_offset)
        for op in i.operands:
            if op.type == X86_OP_IMM and op.imm >= 0x400000 and e.imm_offset:
                mask[e.imm_offset:e.imm_offset + e.imm_size] = [True] * e.imm_size
            if op.type == X86_OP_MEM and op.mem.disp >= 0x400000 and e.disp_offset:
                mask[e.disp_offset:e.disp_offset + e.disp_size] = [True] * e.disp_size
        out += b''.join(b'.' if m else re.escape(bytes([c])) for c, m in zip(i.bytes, mask))
    return out


def unique(pivot, img, va):
    """Unique match of the code at va, anchored up to 48 bytes earlier when the code at va alone repeats."""
    for back in range(0, 48):
        if back and not any(i.address == va for i in insns(pivot, va - back, 16)):
            continue
        for n in (40, 24, 16, 12):
            hits = [m.start() + 0x400000 for m in re.finditer(pattern(pivot, va - back, n), img[:0x200000], re.S)]
            if len(hits) == 1:
                return hits[0] + back
    return None


def derive_data(pivot, img, target):
    """Read target from LeonU instructions that use it (or a field up to 0x80 bytes before or after it),
    at their unique match in img. Votes are the resulting address of target."""
    votes = {}
    for window in (0, 0x80):
        for ref in sorted(range(target - window, target + window + 1), key=lambda r: abs(r - target)):
            for m in re.finditer(re.escape(struct.pack('<I', ref)), pivot[0x1000:0x200000]):
                off = m.start() + 0x1000
                for back in range(1, 8):
                    ins = insns(pivot, 0x400000 + off - back, 1)
                    if ins and ref in absolute(ins[0]) and ins[0].address + ins[0].size >= 0x400000 + off + 4:
                        hit = unique(pivot, img, ins[0].address)
                        if hit:
                            value = absolute(insns(img, hit, 1)[0])[absolute(ins[0]).index(ref)] + target - ref
                            votes[value] = votes.get(value, 0) + 1
                        break
                if sum(votes.values()) >= 4:
                    return votes
        if votes:
            return votes
    return votes


def derive(pivot, img, name):
    table = {}
    for key, lu in sorted(LEONU.items()):
        if key in CODE:
            va = unique(pivot, img, lu)
        else:
            votes = derive_data(pivot, img, lu)
            va = max(votes, key=votes.get) if votes else None
            if len(votes) > 1:
                sys.exit(f'{name}: split votes for {key:#x}: {votes}')
        if va is None:
            sys.exit(f'{name}: no unique match for {key:#x}')
        table[key] = va
    return table


def device_offset(img, create):
    # create: push ebx; push ebp; push esi; push edi; mov edi,ecx; mov eax,[edi+device]
    i = insns(img, create, 6)[5]
    assert i.mnemonic == 'mov' and i.operands[1].type == X86_OP_MEM, i
    return i.operands[1].mem.disp


def checks(img, table):
    """Raw bytes the runtime compares before patching: hook sites and function entries."""
    out = [(table[k], img[table[k] - 0x400000:table[k] - 0x400000 + n]) for k, n in SITES.items()]
    out += [(table[k], img[table[k] - 0x400000:table[k] - 0x400000 + 16]) for k in sorted(FUNCS)]
    return out


def c_bytes(b):
    return '"' + ''.join(f'\\x{c:02x}' for c in b) + '"'


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    images = {n: (Path(sys.argv[1]) / f'{n}.bin').read_bytes() for n in PLAYER}
    pivot = images['LeonU']
    lines = ['// Generated by tools/steam_layouts.py from unpacked Steam memory dumps. Do not edit.']
    names = []
    for name in PLAYER:
        img = images[name]
        table = dict(LEONU) if name == 'LeonU' else derive(pivot, img, name)
        lines.append(f'static const LayoutAddr {name}_addrs[]={{')
        lines += [f' {{0x{k:06x},0x{v:06x}}},' for k, v in sorted(table.items())]
        lines.append('};')
        lines.append(f'static const LayoutCheck {name}_checks[]={{')
        lines += [f' {{0x{va:06x},{len(b)},{c_bytes(b)}}},' for va, b in checks(img, table)]
        lines.append('};')
        names.append(f' {{"Steam {name}",{PLAYER[name]},0x{device_offset(img, table[0x405ec0]):x},{name}_addrs,'
                     f'sizeof({name}_addrs)/sizeof({name}_addrs[0]),{name}_checks,'
                     f'sizeof({name}_checks)/sizeof({name}_checks[0])}},')
    lines.append('#define STEAM_LAYOUTS \\')
    lines += [n + ' \\' for n in names]
    lines.append('')
    (ROOT / 'src/layouts.h').write_text('\n'.join(lines))
    print('wrote src/layouts.h')


if __name__ == '__main__':
    main()
