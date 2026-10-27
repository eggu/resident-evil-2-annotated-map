"""Pack C-style key sprites while retaining the existing lock-icon geometry."""
from pathlib import Path
import json
from PIL import Image
from pixel_icons import load_icon

R = Path(__file__).resolve().parent
layout = json.loads((R/'key-layout.json').read_text())
assert len(layout)==15 and len({row[0] for row in layout})==15
atlas = Image.new('RGB',(256,256))
for item,u,v,w,h in layout:
    assert 0<u<u+w<256 and 0<v<v+h<256
    atlas.paste(load_icon(f'key-{item}',(w,h)),(u,v))
atlas.save(R/'hd-atlas-preview.png')
pixels=[((r>>3)|((g>>3)<<5)|((b>>3)<<10)) for r,g,b in atlas.get_flattened_data()]
assert len(pixels)==65536 and any(pixels)
(R/'atlas.h').write_text('typedef struct {unsigned char item,u,v,w,h;} Icon;\nstatic const Icon icons[]={'+','.join('{%d,%d,%d,%d,%d}'%tuple(row) for row in layout)+'};\nstatic const unsigned short atlas_pixels[]={'+','.join(hex(p) for p in pixels)+'};\n')
(R/'atlas-provenance.json').write_text(json.dumps(dict(style='C',source='pixel-style-c/manifest.json',layout=layout),indent=2)+'\n')
print('Packed15 C-style key icons; original UVs and sizes retained.')
