"""[~] legend toggle on the real EXE under unicorn: hiding swaps the legend and readout quads for one hint line and showing restores the same frame;
the readout follows the size/opacity keys and the Shift/Ctrl modifier (2026-11-07). Run from build/ with RE2_GAME_EXE set."""
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
assert len(gone)==25,len(gone)                      # header: title, hide, [H], [\] language; grid: 5 + 6 (ten state rows, zoom); readout: 4 hints, 2 Shift, 4 values
legend=[q for q in gone if struct.unpack_from('<h',q,18)[0]>=210];readout=[q for q in gone if struct.unpack_from('<h',q,22)[0]<=16]
assert len(legend)==15 and len(readout)==10,'only legend rows and the top-left readout disappear'
assert len(new)==1 and len(hidden)==len(shown)-24,(len(new),len(hidden)) # the hint, nothing else moves
x0,y0,x1,y1=struct.unpack_from('<4h',new[0],16)
assert x0==8 and y0==228 and y1<=238 and x1<=318,(x0,y0,x1,y1)
toggle(1);toggle(1);assert call('KeyMapTestLegend')==0 # other keys leave it alone
toggle(8192);assert call('KeyMapTestLegend')==1 and draw()==shown
# Readout values: '-'/'+' name size, '['/']' name opacity; with the modifier (bit 2048) icon size/opacity.
def values():return call('KeyMapTestSize'),call('KeyMapTestOpacity'),call('KeyMapTestIcons')&255,call('KeyMapTestIcons')>>8&255
before=values()
toggle(512);toggle(32768);assert values()==(before[0]+10,before[1]-10,before[2],before[3])
call('KeyMapTestToggle',0,2048);call('KeyMapTestToggle',0,2048|1024);call('KeyMapTestToggle',0,2048|65536);call('KeyMapTestToggle',0,0)
assert values()==(before[0]+10,before[1]-10,before[2]-10,min(before[3]+10,100))
assert draw()!=shown # the readout shows the new values
toggle(1024);toggle(65536);call('KeyMapTestSetIcons',before[2],before[3],call('KeyMapTestIcons')>>16&1);assert values()==before and draw()==shown
# Layout (user 2026-11-07): header = title then [~] hide; grid 2 rows x 6 columns ([0]..[4]+[H] / [5]..[9]+zoom), the
# column after [2]/[7] clear of the native floor arrow (x 152..165); readout = name column (opacity over size) and icon
# column (modifier + opacity over size).
import re
def labels(path):
 text=(R/path).read_text();start=int(re.search(r'ROOM_HELP_LABEL (\d+)',text)[1])
 return [tuple(int(v) for v in m) for m in re.findall(r'\{(\d+),(\d+),(\d+),(\d+),(\d+)\}',text.split('room_labels[]={',1)[1].split('};',1)[0])][start:]
def boxes(qs):return sorted((struct.unpack_from('<4h',q,16),(q[24],q[25])) for q in qs)
widths={}
for lang,path in (('en','room_labels.h'),('ko','korean-assets/room_labels.h')):
 if (call('KeyMapTestLanguage')==1)!=(lang=='en'):toggle(32)
 help=labels(path);uv=lambda i:help[i][1:3]
 q=draw();rows={y:[b for b in boxes(q) if b[0][1]==y] for y in (1,9,210,220,228)}
 head=rows[210];assert len(head)==4 and head[0][1]==uv(0) and head[1][1]==uv(25) and head[2][1] in (uv(26),uv(27),uv(54)) and head[3][1] in (uv(13),uv(14)),head # title, [~] hide, [H] item names, [\\] language
 assert head[0][0][2]<head[1][0][0]<head[1][0][2]<head[2][0][0]<head[2][0][2]<head[3][0][0] and head[3][0][2]<=318,'header order and width'
 assert head[2][0][1]==head[3][0][1] and head[2][0][3]==head[3][0][3] and head[2][0][3]-head[2][0][1]<=10,'[H] and [\\] share one row and size (one line each)'
 g=[rows[220],rows[228]];assert len(g[0])==5 and len(g[1])==6,g # the [H] state moved to the header: column 6 holds zoom only
 xs=[b[0][0] for b in g[1]];assert [b[0][0] for b in g[0]]==xs[:5],'columns aligned'
 assert g[1][5][1] in (uv(22),uv(23)),'column 6: zoom'
 assert g[0][3][0][0]>=166 and g[0][2][0][2]<152 and all(b[0][2]<=318 for b in g[0]+g[1]),'arrow lane and screen edge'
 widths[lang]=dict(columns=[max(r[c][0][2]-r[c][0][0]+1 for r in g if c<len(r)) for c in range(6)],x=xs,right=max(b[0][2] for b in g[0]+g[1]),header_right=head[3][0][2])
 # [H] cycles through three labels (all -> no common -> off), each fitting the header
 seen=set()
 for _ in range(3):
  toggle(16384);h=boxes([x for x in draw() if struct.unpack_from('<h',x,18)[0]==210])[2];seen.add(h[1]);assert h[0][2]<=318,h
 assert len(seen)==3 and seen=={uv(26),uv(27),uv(54)},seen
 r0,r1=rows[1],rows[9];assert len(r0)==len(r1)==5,(r0,r1)
 assert r0[0][0][0]==r1[0][0][0]==8 and r0[0][1]==uv(28) and r1[0][1]==uv(29),'name column: opacity over size'
 assert r0[2][0][0]==r1[2][0][0]>max(r0[1][0][2],r1[1][0][2]) and r0[2][1]==r1[2][1]==uv(30),'icon column: Shift + opacity over size'
 assert r0[3][1]==uv(32) and r1[3][1]==uv(33)
print('legend widths',widths)
if call('KeyMapTestLanguage')==0:toggle(32)
print('PASS legend toggle')

assert all(v['header_right']==317 for v in widths.values()), widths
