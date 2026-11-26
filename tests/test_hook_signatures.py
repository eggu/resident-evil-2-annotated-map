"""Exercise the actual DLL entry point against the native map hook sites.

RE2_STEAM_DUMPS (optional): a folder with the unpacked Steam memory dumps LeonU.bin ... ClaireS.bin
(tools/steam_layouts.py). Each image must select its own layout and no other.
"""
import os
import re
from pathlib import Path

source = Path(__file__).with_name("test_native-v6.4.py")
exec(source.read_text().split("# ---- harness end", 1)[0])

entry = 0x10000000 + struct.unpack_from("<I", di, o + 16)[0]
sites = {0x4fa552: 5, 0x4fb60b: 5, 0x4fb7e7: 5, 0x4faf3f: 5, 0x4fb4e6: 6}
original = {site: bytes(u.mem_read(site, length)) for site, length in sites.items()}
gog_image = bytes(u.mem_read(0x400000, 0x160000))
protections = {}
fail_protect = None
unreadable = None


def query(address, output, size):
    page = address & ~0xfff
    if page == unreadable:
        return 0
    u.mem_write(output, struct.pack("<7I", page, 0x400000, 0x20, 0x1000, 0x1000,
                                   protections.get(page, 0x20), 0x1000000))
    return size


def protect(address, size, mode, output):
    if address == fail_protect:
        return 0
    page = address & ~0xfff
    u.mem_write(output, struct.pack("<I", protections.get(page, 0x20)))
    protections[page] = mode
    return 1


def filename(module, output, size):
    u.mem_write(output, b"C:\\RE2.AnnotatedMap.asi\0")
    return 22


apis = {
    "GetModuleHandleW": (1, lambda *_: 0x400000),
    "DisableThreadLibraryCalls": (1, lambda *_: 1),
    "GetModuleFileNameA": (3, filename),
    "CreateFileA": (7, lambda *_: 0xffffffff),
    "VirtualQuery": (3, query),
    "VirtualProtect": (4, protect),
    "FlushInstructionCache": (3, lambda *_: 1),
    "GetCurrentProcess": (0, lambda: 0xffffffff),
    "GetPrivateProfileIntA": (4, lambda s, k, default, f: default),
    "GetPrivateProfileStringA": (6, lambda *_: 0),
    "GetFileAttributesA": (1, lambda *_: 0xffffffff),
    "CreateThread": (6, lambda *_: 1),  # the deferred installer is driven below through KeyMapTestInstall
}
handlers = {}
p = imp
while struct.unpack_from("<I", di, p + 12)[0]:
    lookup, _, _, _, iat = struct.unpack_from("<5I", di, p)
    i = 0
    while (hint := struct.unpack_from("<I", di, lookup + 4 * i)[0]):
        name = di[hint + 2:di.index(0, hint + 2)].decode()
        stub = 0x25000010 + 4 * len(handlers)
        handlers[stub] = name
        u.mem_write(iat + 0x10000000 + 4 * i, struct.pack("<I", stub))
        u.mem_write(stub, b"\x90\xc3")
        i += 1
    p += 20


def syscall(uc, address, size, _):
    if address not in handlers:
        return
    name = handlers[address]
    esp = uc.reg_read(UC_X86_REG_ESP)
    if name == "lstrcpyA":
        dest, src = struct.unpack("<2I", uc.mem_read(esp + 4, 8))
        content = bytearray()
        while (char := uc.mem_read(src + len(content), 1)) != b"\0":
            content.extend(char)
        uc.mem_write(dest, bytes(content) + b"\0")
        count, result = 2, dest
    elif name == "lstrcmpiA":
        count, result = 2, 1
    else:
        count, handler = apis[name]
        result = handler(*struct.unpack("<" + "I" * count, uc.mem_read(esp + 4, 4 * count)))
    ret = uc.mem_read(esp, 4)
    uc.mem_write(esp + 4 * count, bytes(ret))
    uc.reg_write(UC_X86_REG_ESP, esp + 4 * count)
    uc.reg_write(UC_X86_REG_EAX, result)


u.hook_add(UC_HOOK_CODE, syscall, begin=min(handlers), end=max(handlers))


def attach():
    u.mem_write(0x20008000, struct.pack("<4I", 0x20000100, 0x10000000, 1, 0))
    u.reg_write(UC_X86_REG_ESP, 0x20008000)
    u.emu_start(entry, 0x20000100, count=1000000)
    assert u.reg_read(UC_X86_REG_ESP) == 0x20008010
    assert all(mode == 0x20 for mode in protections.values())


def assert_untouched():
    assert all(u.mem_read(site, len(code)) == code for site, code in original.items())


# Corruption in a target or either branch must leave every patch site alone.
for address in (0x4fa990, 0x440280, 0x503170, 0x4fa465):
    old = bytes(u.mem_read(address, 1))
    u.mem_write(address, bytes([old[0] ^ 1]))
    attach()
    assert_untouched()
    u.mem_write(address, old)

unreadable = 0x4fa000
attach()
assert_untouched()
unreadable = None

fail_protect = 0x4fb4e6
attach()
assert_untouched()
fail_protect = None

attach()
for site, code in original.items():
    patch = u.mem_read(site, len(code))
    assert patch != code, f"map hook missing at {site:#x}"
    target = site + 5 + struct.unpack_from("<i", patch, 1)[0]
    if site == 0x4fb4e6:
        assert patch[0] == 0xe9 and target == 0x4fb5aa and patch[5] == 0x90
    else:
        assert patch[0] == 0xe8 and 0x10000000 <= target < 0x11000000


def table(name):
    body = Path(__file__).with_name("layouts.h").read_text().split(f"{name}_addrs[]={{")[1].split("};")[0]
    return {int(k, 16): int(v, 16) for k, v in re.findall(r"\{0x(\w+),0x(\w+)\}", body)}


LAYOUTS = ["GOG"] + [f"{who}{lang}" for lang in "UJFGIS" for who in ("Leon", "Claire")]
dumps = os.environ.get("RE2_STEAM_DUMPS")
if dumps:
    for index, name in enumerate(LAYOUTS):
        image = gog_image if name == "GOG" else (Path(dumps) / f"{name}.bin").read_bytes()[:0x160000]
        u.mem_write(0x400000, image)
        protections.clear()
        assert [call("KeyMapTestLayoutMatches", n) for n in range(len(LAYOUTS))] == [int(n == index) for n in range(len(LAYOUTS))], name
        assert call("KeyMapTestInstall") == index, name
        assert all(mode == 0x20 for mode in protections.values())
        va = (lambda key: key) if name == "GOG" else table(name).__getitem__
        for key in (0x4fa552, 0x4fb60b, 0x4fb7e7, 0x4faf3f, 0x4fb4e6):
            patch = u.mem_read(va(key), 6)
            target = va(key) + 5 + struct.unpack_from("<i", patch, 1)[0]
            if key == 0x4fb4e6:
                assert patch[0] == 0xe9 and target == va(0x4fb5aa) and patch[5] == 0x90, name
            else:
                assert patch[0] == 0xe8 and 0x10000000 <= target < 0x11000000, (name, hex(key))
        print("PASS layout", name)
    u.mem_write(0x400000, gog_image)
