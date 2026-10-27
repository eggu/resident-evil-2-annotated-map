"""Load approved C-style pixel sprites without smoothing or changing draw geometry."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent / 'icons'


def load_icon(name, size):
    sprite = Image.open(ROOT / (name+'.png')).convert('RGBA')
    assert sprite.getbbox() and max(sprite.size) <= 32
    assert set(sprite.getchannel('A').get_flattened_data()) <= {0,255}
    scale = min((size[0]-2)/sprite.width, (size[1]-2)/sprite.height)
    sprite = sprite.resize(tuple(max(1,round(d*scale)) for d in sprite.size), Image.Resampling.NEAREST)
    out = Image.new('RGB', size)
    out.paste(sprite, ((size[0]-sprite.width)//2,(size[1]-sprite.height)//2), sprite)
    assert out.getbbox()
    return out
