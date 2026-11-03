#!/usr/bin/env python3
"""Decode RE2 map ADT files by emulating the game's own decompressor (EXE 0x43c390) in unicorn.
Usage: decode_maps.py            -> maps-decoded/<name>.bin (+ .png where a texture is recognised)
Game root = RE2_GAME."""
import struct, sys, os
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *

ROOT = os.environ["RE2_GAME"]
EXE = open(os.path.join(ROOT, "Resident Evil 2.exe"), "rb").read()

def _map(mu):
    pe = struct.unpack_from("<I", EXE, 0x3c)[0]
    nsec, = struct.unpack_from("<H", EXE, pe + 6)
    opt, = struct.unpack_from("<H", EXE, pe + 20)
    base, = struct.unpack_from("<I", EXE, pe + 52)
    size, = struct.unpack_from("<I", EXE, pe + 80)
    mu.mem_map(base, (size + 0xfff) & ~0xfff)
    mu.mem_write(base, EXE[:0x400])
    for i in range(nsec):
        o = pe + 24 + opt + i * 40
        vs, va, rs, ro = struct.unpack_from("<IIII", EXE, o + 8)
        mu.mem_write(base + va, EXE[ro:ro + min(rs, vs)])

IN, OUT, WORK, STK, FAKE = 0x20000000, 0x21000000, 0x23000000, 0x24000000, 0x25000000
IAT_READ = 0x517088

def decode(raw):
    """raw = whole ADT file; first 4 bytes are skipped like 0x43c590 does."""
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    _map(mu)
    for a, n in ((IN, 0x200000), (OUT, 0x200000), (WORK, 0x100000), (STK, 0x100000), (FAKE, 0x1000)):
        mu.mem_map(a, n)
    pos = [4]
    def w(addr, v): mu.mem_write(addr, struct.pack("<I", v))
    def rd(addr): return struct.unpack("<I", bytes(mu.mem_read(addr, 4)))[0]
    # state set exactly like 0x43c590 before calling 0x43c390
    for a in (0x671404, 0x671408, 0x67140c, 0x671410, 0x671414, 0x671418, 0x99dab4, 0x99dab8, 0x99dab0, 0x99dac8):
        w(a, 0)
    w(0x524e08, 8); w(0x524e0c, 0x4000)
    w(0x99daa8, OUT); w(0x99daa4, IN); w(0x99dabc, WORK); w(0x99daac, 0x1234)
    w(0x99dac0, 0)  # bytes in buffer -> forces first refill
    w(IAT_READ, FAKE)
    def hook(mu_, addr, size, _):
        if addr != FAKE: return
        esp = mu.reg_read(UC_X86_REG_ESP)
        ret, h, buf, n, pnread, _ov = struct.unpack("<6I", bytes(mu.mem_read(esp, 24)))
        chunk = raw[pos[0]:pos[0] + n]
        pos[0] += len(chunk)
        mu.mem_write(buf, chunk)
        if pnread: w(pnread, len(chunk))
        mu.reg_write(UC_X86_REG_EAX, 1 if chunk else 0)
        mu.reg_write(UC_X86_REG_ESP, esp + 24)  # stdcall: pop ret + 5 args
        mu.reg_write(UC_X86_REG_EIP, ret)
    mu.hook_add(UC_HOOK_CODE, hook, begin=FAKE, end=FAKE)
    sp = STK + 0x80000
    mu.mem_write(sp, struct.pack("<I", FAKE + 0x10))
    mu.reg_write(UC_X86_REG_ESP, sp)
    mu.hook_add(UC_HOOK_CODE, lambda *a: mu.emu_stop(), begin=FAKE + 0x10, end=FAKE + 0x10)
    mu.emu_start(0x43c390, 0, count=400_000_000)
    n = rd(0x99dab4)
    return bytes(mu.mem_read(OUT, n))

# ---- TIM pages / room tables -------------------------------------------------
import json, base64, hashlib
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE_IDS = (0x1d, 0x21, 0x20, 0x1e, 0x1f)   # load order at EXE 0x4fa2f4..0x4fa330
TABLES = {0: 0x53eaf8, 1: 0x53eb98}         # Leon / Claire floor tables, 8 bytes per floor
NFLOOR = 20

def tims(bin_):
    """Sequential TIM parse -> {page_id: (w_px, h, clut_rows[list of 16 ints], idx[h][w_px])}."""
    out, o = {}, 0
    for pid in PAGE_IDS:
        if o >= len(bin_): break  # plain MAP61 has only 4 TIMs (no 0x20 fill page)
        assert struct.unpack_from("<II", bin_, o) == (0x10, 8), (pid, o)
        p = o + 8
        sz, _, _, cw, ch = struct.unpack_from("<IHHHH", bin_, p)
        clut = struct.unpack_from("<%dH" % (cw * ch), bin_, p + 12)
        rows = [list(clut[r * cw:(r + 1) * cw]) for r in range(ch)]
        p += sz
        sz, _, _, w, h = struct.unpack_from("<IHHHH", bin_, p)
        raw = bin_[p + 12:p + 12 + w * 2 * h]
        idx = [[(raw[y * w * 2 + (x >> 1)] >> (4 * (x & 1))) & 15 for x in range(w * 4)] for y in range(h)]
        out[pid] = (w * 4, h, rows, idx)
        o = p + sz
    # ponytail: plain map60/map61 hold only 4 TIMs, ids would shift; their d/f variants are complete -> use those
    return out if o == len(bin_) and len(out) == 5 else {}

def rgb(c):
    return ((c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31)

def page_image(page, row=0):
    w, h, rows, idx = page
    pal = rows[min(row, len(rows) - 1)]
    im = Image.new("RGBA", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            c = pal[idx[y][x]]
            if c:  # PSX: 0x0000 = transparent, 0x8000 = opaque black
                px[x, y] = rgb(c) + (255,)
    return im

def exe_off(v):
    pe = struct.unpack_from("<I", EXE, 0x3c)[0]
    nsec, = struct.unpack_from("<H", EXE, pe + 6)
    opt, = struct.unpack_from("<H", EXE, pe + 20)
    base, = struct.unpack_from("<I", EXE, pe + 52)
    for i in range(nsec):
        vs, va, rs, ro = struct.unpack_from("<IIII", EXE, pe + 24 + opt + i * 40 + 8)
        if base + va <= v < base + va + vs and v - base - va < rs:
            return ro + v - base - va
    raise ValueError(hex(v))

def floor_rooms(pl, floor):
    """-> (map file stem e.g. 'map10', [raw 16-byte entries with va])"""
    ptr, cnt, _, word = struct.unpack_from("<IBBH", EXE, exe_off(TABLES[pl] + floor * 8))
    ents = [(ptr + i * 16, EXE[exe_off(ptr + i * 16):exe_off(ptr + i * 16) + 16]) for i in range(cnt)]
    return "map%d%d" % (word // 10, word % 10), ents

def load_bin(stem, variant=""):
    for f in os.listdir(os.path.join(HERE, "maps-decoded")):
        if f.lower() == (stem + variant).lower() + ".bin":
            return open(os.path.join(HERE, "maps-decoded", f), "rb").read()
    raise FileNotFoundError(stem + variant)

def cut(page, u, v, w, h):
    """opaque mask: palette index != 0 in ANY clut row (rows differ only in colour)."""
    pw, ph, rows, idx = page
    opaque = [i for i in range(16) if any(r[i] for r in rows)]
    return [[1 if idx[v + y][u + x] in opaque else 0 for x in range(w)] for y in range(h)]

def runs(mask):
    out = []
    for row in mask:
        r, x = [], 0
        while x < len(row):
            if row[x]:
                s = x
                while x < len(row) and row[x]: x += 1
                r.append([s, x - s])
            else: x += 1
        out.append(r)
    return out

def pack(mask):
    bits = "".join(str(b) for row in mask for b in row)
    bits += "0" * (-len(bits) % 8)
    return base64.b64encode(bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))).decode()

def main():
    src = os.path.join(ROOT, "Common", "file")
    dst = os.path.join(HERE, "maps-decoded")
    os.makedirs(dst, exist_ok=True)
    done = {}
    for f in sorted(os.listdir(src)):
        if f.lower().startswith("map") and f.lower().endswith(".adt"):
            stem = f[:-4].lower()
            out = decode(open(os.path.join(src, f), "rb").read())
            open(os.path.join(dst, stem + ".bin"), "wb").write(out)
            try:
                t = tims(out)
            except AssertionError as e:  # ponytail: map61 plain layout differs, shapes still use 0x20 only if parsed
                print(f, len(out), "TIM parse failed", e); continue
            if not t:
                print("  ", stem, "is not a 5-TIM file (", len(out), "bytes ); shapes taken from its d variant")
            for pid, pg in t.items():
                page_image(pg, 1 if pid == 0x20 else 0).save(os.path.join(dst, "%s_%02x.png" % (stem, pid)))
            done[stem] = t
            print(f, len(out), "ok")
    prov = json.load(open(os.path.join(HERE, "room_names-provenance.json")))
    names = {(r["pl"], r["floor"], r["native_va"]): r for r in prov["rows"]}
    floors = []
    for pl in (0, 1):
        for fl in range(NFLOOR):
            stem, ents = floor_rooms(pl, fl)
            if stem not in done:
                print("skip", pl, fl, stem); continue
            fill = (done[stem].get(0x20) or done[stem + "d"][0x20])  # MAP61 plain lacks fill page; d/f share it
            rooms = []
            for i, (va, raw) in enumerate(ents):
                u, v, w, h = raw[:4]
                x, y = struct.unpack_from("<hh", raw, 4)
                assert u + w <= 256 and v + h <= 256
                m = cut(fill, u, v, w, h)
                nm = names.get((pl, fl, va), {})
                rooms.append({"index": i, "va": va, "u": u, "v": v, "w": w, "h": h, "x": x, "y": y,
                              "seen": raw[12], "page_bit": raw[13], "raw": raw.hex(),
                              "rooms": nm.get("rooms", []), "ko": nm.get("ko"),
                              "opaque": sum(map(sum, m)), "runs": runs(m), "mask_b64": pack(m)})
            floors.append({"pl": pl, "floor": fl, "file": stem, "rooms": rooms})
    json.dump({"exe_sha256": hashlib.sha256(EXE).hexdigest(),
               "note": "mask = cut from page 0x20 (room fills) at u,v,w,h, to be placed at x,y; runs = per-row [start,len]",
               "floors": floors}, open(os.path.join(HERE, "room_shapes.json"), "w"), separators=(",", ":"))
    print("floors", len(floors), "rooms", sum(len(f["rooms"]) for f in floors))

if __name__ == "__main__":
    main()
