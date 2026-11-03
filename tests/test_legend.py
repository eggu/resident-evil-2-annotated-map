"""[~] legend toggle on the real EXE under unicorn: hiding swaps the legend quads for one hint line and showing restores the same frame. Run from build/ with RE2_GAME_EXE set."""
import struct
from pathlib import Path
R=Path(__file__).resolve().parent
exec((R/'test_native-v6.4.py').read_text().split('# ---- harness end')[0])
src=(R/'re2_keymap.c').read_text()
assert 'VK_OEM_3' in src and '"Legend"' in src
u.mem_write(0x4021c0,bytes.fromhex('c20800'))
call('KeyMapTestInit',0x400000);call('KeyMapTestTexture',5000)
def draw(floor=2):
 u.mem_write(0x989ed0,bytes(32));u.mem_write(0x98eb2c,bytes(0xc0));u.mem_write(0x98ed2c,bytes(32));u.mem_write(0x98ec04,b'\xff'*32)
 u.mem_write(0x691f7a,bytes([floor]));u.mem_write(0x691f62,b'\0');u.mem_write(0x691fb8,bytes(4))
 u.mem_write(0x21000000,b'\xa5'*0x30000);u.mem_write(0x524e1c,struct.pack('<II',0x21000000,0x21020000));call('KeyMapTestDraw')
 end=struct.unpack('<I',u.mem_read(0x524e1c,4))[0]
 return [bytes(u.mem_read(p,32)) for p in range(0x21000000,end,32)]
def toggle(bit):call('KeyMapTestToggle',0,bit);call('KeyMapTestToggle',0,0)
shown=draw();assert call('KeyMapTestLegend')==1
toggle(8192);assert call('KeyMapTestLegend')==0
hidden=draw()
gone=[q for q in shown if q not in hidden];new=[q for q in hidden if q not in shown]
assert len(gone)==14,len(gone)                      # title, opacity, size, zoom and ten state rows
assert all(struct.unpack_from('<h',q,18)[0]>=210 for q in gone),'only legend rows disappear'
assert len(new)==1 and len(hidden)==len(shown)-13,(len(new),len(hidden)) # the hint, nothing else moves
x0,y0,x1,y1=struct.unpack_from('<4h',new[0],16)
assert x0==8 and y0==228 and y1<=238 and x1<=318,(x0,y0,x1,y1)
toggle(1);toggle(1);assert call('KeyMapTestLegend')==0 # other keys leave it alone
toggle(8192);assert call('KeyMapTestLegend')==1 and draw()==shown
print('PASS legend toggle')
