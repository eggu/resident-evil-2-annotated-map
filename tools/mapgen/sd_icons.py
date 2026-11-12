"""SD map markers (user decisions 2026-11-12, common/SD-MAP-PORTING.md): 9x9 pixel sprites, enemies 5x5, locks from the
approved RE2 table (common/sd-lock-assignments.py K2). Letters are colours of the sprite's own palette."""
import numpy as np

ICON_PAL = dict(k=(8, 8, 8), a=(238, 184, 48), p=(176, 112, 255), c=(136, 232, 255), g=(90, 205, 90), r=(220, 50, 50), b=(80, 120, 255),
                o=(130, 140, 60), s=(195, 195, 205), Y=(230, 190, 70), w=(248, 248, 248), m=(150, 150, 150), n=(140, 90, 40),
                T=(215, 190, 130), X=(62, 62, 70))
# lock palette: common/sd-lock-assignments.py C (user-approved)
LOCK_PAL = dict(X=(62, 62, 70), A=(215, 160, 55), I=(230, 220, 175), L=(150, 150, 160), J=(110, 110, 118), c=(170, 225, 240), k=(8, 8, 8),
                Y=(240, 200, 60), H=(190, 190, 200), R=(220, 50, 50), t=(40, 170, 170), N=(60, 170, 70), b=(70, 110, 240), Q=(110, 60, 25),
                W=(250, 250, 250), m=(235, 215, 170), o=(140, 150, 60), Z=(110, 110, 120))


def herb(f): return '|'.join(['.........', '.kkkkkkk.', '.k' + f * 5 + 'k.', '..k' + f * 3 + 'k..', '..k' + f * 3 + 'k..', '...k' + f + 'k...', '...k' + f + 'k...', '....k....', '.........'])
def ammo(f): return '|'.join(['.........', '.........', '.Y.Y.Y.Y.', 'kkkkkkkkk', 'k' + f * 7 + 'k', 'k' + f * 7 + 'k', 'kkkkkkkkk', '.........', '.........'])
def grenade(f): return '...kkk...|..k' + f * 3 + 'k..|.k' + f * 5 + 'k.|.k' + f * 5 + 'k.|.knnnnnk.|.knnnnnk.|.knnnnnk.|..kkkkk..|.........'
def diamond(f, glyph):
    rows = []
    for r in range(9):
        h = 4 - abs(4 - r)
        rows.append(''.join('w' if (r, c) in glyph and abs(c - 4) < h else 'k' if abs(c - 4) == h else f if abs(c - 4) < h else '.' for c in range(9)))
    return '|'.join(rows)


# bolts (user 2026-11-12): a quiver lying on its side, the fletching sticking out of its left end, so it reads as arrows
BOLTS = '|'.join(['.........', '.........', 'rr.kkkkkk', '.wwknnnnk', 'rrrwnnnnk', '.wwknnnnk', 'rr.kkkkkk', '.........', '.........'])
ICONS = {
    'puzzle': diamond('a', {(2, 4), (3, 4), (4, 4), (6, 4)}),
    'event': diamond('p', {(2, 3), (2, 4), (2, 5), (3, 5), (4, 4), (6, 4)}),
    'key': '.........|...kkk...|..kccck..|.kccccck.|.kccccck.|.kccccck.|..kccck..|...kkk...|.........',
    'herb_g': herb('g'), 'herb_r': herb('r'), 'herb_b': herb('b'),
    'ammo_handgun': ammo('r'), 'ammo_shotgun': ammo('o'), 'ammo_magnum': ammo('s'), 'ammo_smg': ammo('X'), 'ammo_bolts': BOLTS,
    'grenade': grenade('m'), 'grenade_acid': grenade('Y'), 'grenade_flame': grenade('r'),
    'spray': '...kkk...|...kmk...|..kkkkk..|..kwwwk..|..kwrwk..|..krrrk..|..kwrwk..|..kwwwk..|..kkkkk..',
    'ribbon': '..kkkkk..|.kmmmmmk.|kmwwwwwmk|kmwkkkwmk|kmwkmkwmk|kmwkkkwmk|kmwwwwwmk|.kmmmmmk.|..kkkkk..',
    'file': '.kkkkkk..|.kwwwwkk.|.kwkkwwk.|.kwwwwwk.|.kwkkkwk.|.kwwwwwk.|.kwkkkwk.|.kwwwwwk.|.kkkkkkk.',
    'map': '.........|kkkkkkkkk|kTrnTYnTk|kTTnTTnTk|kTTnTgnTk|kTTnTTnTk|kkkkkkkkk|.........|.........',
    'typewriter': '.........|..kkkkk..|..kwwwk..|kkkkkkkkk|kmmmmmmmk|kmXXXXXmk|kmmmmmmmk|kkkkkkkkk|.........',
    'itembox': '.........|kkkkkkkkk|knnnnnnnk|kkkkkkkkk|knnnYnnnk|knnnnnnnk|knnnnnnnk|kkkkkkkkk|.........',
    'enemy': 'kk.kk|krkrk|.krk.|krkrk|kk.kk',
}
S3 = {'x': 'x.x|.x.|x.x', '-': '...|xxx|...', 'o': 'xxx|xxx|xxx', '□': 'xxx|x.x|xxx', '|': '.x.|.x.|.x.'}
S7 = {'spade': '...x...|..xxx..|.xxxxx.|...x...|..xxx..', 'heart': '..x.x..|.xxxxx.|.xxxxx.|..xxx..|...x...',
      'diamond': '...x...|..xxx..|.xxxxx.|..xxx..|...x...', 'club': '...x...|..xxx..|.x.x.x.|.xxxxx.|...x...',
      'card': '.......|xxxxxxx|.......|.......|.......', 'D': '.......|..xx...|..x.x..|..xx...|.......', 'U': '.......|..x.x..|..x.x..|..xxx..|.......',
      'check': 'x.x.x.x|.x.x.x.|x.x.x.x|.x.x.x.|x.x.x.x', 'slash': '......x|....xx.|...x...|.xx....|x......', 'hi-': '.......|.xxxxx.|.......|.......|.......',
      'king': '...x...|..xxx..|...x...|..xxx..|.xxxxx.', 'bishop': '...x...|..xxx..|..xxx..|...x...|.xxxxx.',
      'rook': '.x.x.x.|.xxxxx.|..xxx..|..xxx..|.xxxxx.', 'knight': '..xxx..|.xxxx..|...xx..|..xxx..|.xxxxx.'}


def lock(body, sym, fg):
    """9x9 padlock: 2-row shackle, 9x7 body; body = the key's colour, pattern in another colour."""
    g = S7[sym].split('|') if sym in S7 else ['.' * 7] + ['.' * ((7 - len(r)) // 2) + r + '.' * (7 - len(r) - (7 - len(r)) // 2) for r in S3[sym].split('|')] + ['.' * 7]
    inner = [''.join(fg if c == 'x' else body for c in r) for r in g]
    return '|'.join(['..kkkkk..', '.kk...kk.', 'kkkkkkkkk'] + ['k' + r + 'k' for r in inner] + ['kkkkkkkkk'])


# key item id -> (body, pattern, pattern colour), common/sd-lock-assignments.py K2 (31 and 48 share one marker)
LOCKS = {31: ('H', '|', 'Q'), 48: ('H', '|', 'Q'), 52: ('R', 'card', 'W'), 62: ('X', 'king', 'I'), 59: ('I', 'bishop', 'X'), 60: ('X', 'rook', 'I'),
         61: ('I', 'knight', 'X'), 63: ('Q', '|', 'Y'), 75: ('L', 'slash', 'k'), 83: ('Y', 'o', 'N'), 88: ('H', '□', 'W'), 89: ('t', 'spade', 'W'),
         90: ('R', 'diamond', 'Y'), 91: ('R', 'heart', 'W'), 92: ('N', 'club', 'W'), 93: ('R', 'D', 'W'), 94: ('Y', 'U', 'N'), 95: ('Z', 'o', 'k'),
         97: ('R', 'x', 'W'), 98: ('Z', 'check', 'H'), 99: ('H', 'hi-', 'k')}
# common item id -> icon
COMMON = {20: 'ammo_handgun', 21: 'ammo_shotgun', 22: 'ammo_magnum', 24: 'grenade', 25: 'grenade_flame', 26: 'grenade_acid', 27: 'ammo_smg',
          29: 'ammo_bolts', 30: 'ribbon', 35: 'spray', 38: 'herb_g', 39: 'herb_r', 40: 'herb_b'}


def image(pattern, pal):
    """RGBA array of a sprite string ('.' transparent)."""
    rows = pattern.split('|')
    a = np.zeros((len(rows), len(rows[0]), 4), np.uint8)
    for y, r in enumerate(rows):
        assert len(r) == len(rows[0]), pattern
        for x, c in enumerate(r):
            if c != '.':
                a[y, x] = pal[c] + (255,)
    return a


def lock_image(item): return image(lock(*LOCKS[item]), LOCK_PAL)
def icon_image(name): return image(ICONS[name], ICON_PAL)
