"""Pack C-style key sprites while retaining the existing lock-icon geometry."""
from pathlib import Path
import json
from PIL import Image
from pixel_icons import load_icon

R = Path(__file__).resolve().parent
layout = json.loads((R/'key-layout.json').read_text())
assert len(layout)==18 and len({row[0] for row in layout})==18  # 52 Red Card (key-97 card without the logo), 75 Manhole Opener, 62 Chess Plug; 5 rows of 44 px
atlas = Image.new('RGB',(256,256))
for item,u,v,w,h in layout:
    assert 0<u<u+w<256 and 0<v<v+h<256
    atlas.paste(load_icon(f'key-{item}',(w,h)),(u,v))
atlas.save(R/'hd-atlas-preview.png')
pixels=[((r>>3)|((g>>3)<<5)|((b>>3)<<10)) for r,g,b in atlas.get_flattened_data()]
assert len(pixels)==65536 and any(pixels)
# Lock icons are drawn by visible size (re2_keymap.c icon_box), so each rect is cropped to its non-transparent texels;
# otherwise art that fills its cell (Lockpick, cards, Chess Plug) drew ~35% larger than the suit keys (user 2026-10-27).
def visible(item,u,v,w,h):
    pts=[(x,y) for y in range(v,v+h) for x in range(u,u+w) if pixels[y*256+x]]
    x0,y0=min(p[0] for p in pts),min(p[1] for p in pts)
    return [item,x0,y0,max(p[0] for p in pts)-x0+1,max(p[1] for p in pts)-y0+1]
cropped=[visible(*row) for row in layout]
(R/'atlas.h').write_text('typedef struct {unsigned char item,u,v,w,h;} Icon;\nstatic const Icon icons[]={'+','.join('{%d,%d,%d,%d,%d}'%tuple(row) for row in cropped)+'};\nstatic const unsigned short atlas_pixels[]={'+','.join(hex(p) for p in pixels)+'};\n')
(R/'atlas-provenance.json').write_text(json.dumps(dict(style='C',source='artwork-provenance.json',layout=layout),indent=2)+'\n')
print('Packed', len(layout), 'C-style key icons; icon rects cropped to visible texels.')
