"""2x zoom on the real EXE under unicorn: A off leaves native packets untouched; B on doubles map packets and crops them on
whole texels, keeps UI in place with a copy on top, keeps the cursor's size; C overlay follows 2x-view and never piles on
the edge; D decide toggles once per press, directions pan 4 px and clamp. Run from build/ with RE2_GAME_EXE set."""
import re,struct
from pathlib import Path
R=Path(__file__).resolve().parent
exec((R/'test_native-v6.4.py').read_text().split('# ---- harness end')[0])
UI,CURSOR=1030,1020
imp_p=struct.unpack_from('<I',b,o+96+8)[0]
stub=0x25000100;u.mem_write(stub,bytes.fromhex('31c0c21000')) # VirtualProtect fails cleanly: floor_keys logs and returns
while struct.unpack_from('<I',di,imp_p+12)[0]:
 lookup,_,_,_,iat=struct.unpack_from('<5I',di,imp_p);lookup=lookup or iat;i=0
 while (e:=struct.unpack_from('<I',di,lookup+i*4)[0]):
  if not e&0x80000000 and di[e+2:di.index(0,e+2)]==b'VirtualProtect':u.mem_write(0x10000000+iat+i*4,struct.pack('<I',stub))
  i+=1
 imp_p+=20
for va in (0x4021c0,):u.mem_write(va,bytes.fromhex('c20800'))
u.mem_write(0x4ed950,bytes.fromhex('c3'))
u.mem_map(0x22000000,0x10000);u.mem_write(0x6805b8,struct.pack('<I',0x22000000))
for s in range(0x29):u.mem_write(0x67c7d8+s*12,struct.pack('<III',1000+s,256,0))
call('KeyMapTestInit',0x400000);call('KeyMapTestTexture',5000)
def native_call(fn):
 u.mem_write(0x20008000,struct.pack('<I',0x20000100));u.reg_write(UC_X86_REG_ESP,0x20008000);u.emu_start(fn,0x20000100,count=2000000)
def state(floor,on_floor=True):
 u.mem_write(0x691f7a,bytes([floor]));u.mem_write(0x989ed0,bytes(4));u.mem_write(0x98ec04,b'\xff'*24);u.mem_write(0x98ec00,b'\xff'*4);u.mem_write(0x98ec1c,b'\xff'*12);u.mem_write(0x691f62,b'\0');u.mem_write(0x691fb8,bytes(4))
 u.mem_write(0x98eb14,struct.pack('<hh',1,0) if on_floor else struct.pack('<hh',6,0))
 u.mem_write(0x989f28,struct.pack('<i',-5000));u.mem_write(0x989f30,struct.pack('<i',-5000))
 native_call(0x4fa7d0) # room sprite sizes are loaded per floor
 u.mem_write(0x21000000,b'\xa5'*0x20000);u.mem_write(0x524e1c,struct.pack('<II',0x21000000,0x21020000))
def packets():
 end=struct.unpack('<I',u.mem_read(0x524e1c,4))[0];out=[]
 for p in range(0x21000000,end,32):
  d=bytes(u.mem_read(p,32));x0,y0,x1,y1=struct.unpack_from('<4h',d,16)
  out.append(dict(cmd=struct.unpack_from('<I',d,4)[0],t=struct.unpack_from('<I',d,8)[0],x0=x0,y0=y0,x1=x1,y1=y1,uv=tuple(d[24:28]),color=struct.unpack_from('<I',d,28)[0],raw=d))
 return out
def native(floor):state(floor);native_call(0x4fa990);return packets()
def is_ui(p):return p['t']==UI or (p['t']==CURSOR and p['uv'][1]>=24)
def is_map(p):return 1000<=p['t']<1041 and not is_ui(p) and p['t']!=CURSOR
assert call('KeyMapTestZoomState')==0
for floor in (2,3,6,13,16):
 want=native(floor);state(floor);call('KeyMapTestDrawMap');got=packets()
 assert [p['raw'] for p in got[:len(want)]]==[p['raw'] for p in want],floor        # A
def press(bit=0x1000):u.mem_write(0x988608,struct.pack('<I',bit));call('KeyMapTestZoomInput');u.mem_write(0x988608,bytes(4));call('KeyMapTestZoomInput')
press();assert call('KeyMapTestZoomState')==1                                      # D toggle
u.mem_write(0x988608,struct.pack('<I',0x1000));call('KeyMapTestZoomInput');call('KeyMapTestZoomInput');assert call('KeyMapTestZoomState')==0;u.mem_write(0x988608,bytes(4));call('KeyMapTestZoomInput')
press(0x2000);assert call('KeyMapTestZoomState')==0                                # cancel does not toggle
press()
state(2);call('KeyMapTestDrawMap') # first frame centres the view
cases=[(160,120),(0,0),(320,240),(161,57)]
seen=0
for floor in (2,3,6,13,16):
 want=native(floor)
 for vx,vy in cases:
  call('KeyMapTestZoomView',vx,vy);state(floor);call('KeyMapTestDrawMap');got=packets();n=len(want)
  ui=[p for p in want if is_ui(p)]
  extra=got[n:]
  for a,w in zip(got,want):
   if is_ui(w):assert a['raw']==w['raw'] ;continue                                 # B UI in place
   if w['t']==CURSOR:
    assert a['color']==0 and a['cmd']==0x400025 or (a['x1']-a['x0'],a['y1']-a['y0'])==(11,11);continue
   ax0,ax1=2*w['x0']-vx,2*w['x1']+1-vx;ay0,ay1=2*w['y0']-vy,2*w['y1']+1-vy
   if ax1<1 or ax0>318 or ay1<1 or ay0>238:
    assert a['cmd']==0x400025 and a['color']==0,(floor,w);continue                 # hidden, not moved
   if a['cmd']==0x400025 and a['color']==0:
    assert ax1-ax0<4 or ay1-ay0<4 or ax1<3 or ax0>316 or ay1<3 or ay0>236,(floor,w,a);continue # only slivers vanish
   assert 1<=a['x0']<=a['x1']<=318 and 1<=a['y0']<=a['y1']<=238,(a,w)
   assert (a['x1']-a['x0']+1)%2==0 and (a['y1']-a['y0']+1)%2==0
   assert a['uv'][2]-a['uv'][0]+1==(a['x1']-a['x0']+1)//2 and a['uv'][3]-a['uv'][1]+1==(a['y1']-a['y0']+1)//2,(a,w)
   assert a['uv'][0]-w['uv'][0]==(a['x0']-ax0)//2 and a['uv'][1]-w['uv'][1]==(a['y0']-ay0)//2,(a,w)
   seen+=1
  copies=[p for p in extra if is_ui(p)]
  assert [p['raw'] for p in copies]==[p['raw'] for p in ui],floor                  # B copied on top
  for p in extra:
   if p['t']==5000:assert 1<=p['x0'] and p['x1']<=318 and 1<=p['y0'] and p['y1']<=238,p # C
assert seen>200
# C overlay anchors: room names at 2x-view, off-screen ones absent.
def rows(path,name):
 body=(R/path).read_text().split(name,1)[1].split('={',1)[-1].split('};',1)[0]
 return [tuple(int(x,0) for x in m.split(',')) for m in re.findall(r'\{([-0-9x, ]+)\}',body)]
labels=rows('room_labels-en.h','room_labels_EN[]')
call('KeyMapTestZoomView',160,120);state(2);call('KeyMapTestDrawMap');got=[p for p in packets() if p['t']==5000]
found=0
for pl,fl,sn,x,y,label,lx0,ly0,lx1,ly1 in rows('room_names-en.h','room_names_EN[]'):
 if pl or fl!=2 or lx0|ly0|lx1|ly1:continue
 _,_,_,w,h=labels[label];w,h=(w+2)//4,(h+2)//4;sx,sy=2*x-160-w//2,2*y-120-h//2
 if 2<sx and sx+w<317 and 2<sy and sy+h<237:
  assert any(p['x0']==sx and p['y0']==sy and p['x1']==sx+w-1 and p['y1']==sy+h-1 for p in got),(x,y,sx,sy);found+=1
assert found>=8,found
# D pan: 4 px per held frame, clamps to the doubled map.
def hold(bit,n=1):
 u.mem_write(0x9885fc,struct.pack('<I',bit))
 for _ in range(n):call('KeyMapTestZoomInput')
 u.mem_write(0x9885fc,bytes(4))
def view():return call('KeyMapTestZoomX'),call('KeyMapTestZoomY')
call('KeyMapTestZoomView',100,100)
hold(0x2000);assert view()==(104,100);hold(0x8000,2);assert view()==(96,100);hold(0x1000);assert view()==(96,96);hold(0x4000,2);assert view()==(96,104)
hold(0x2000,200);hold(0x4000,200);assert view()==(320,240);hold(0x8000,200);hold(0x1000,200);assert view()==(0,0)
press();assert call('KeyMapTestZoomState')==0
want=native(2);state(2);call('KeyMapTestDrawMap');assert [p['raw'] for p in packets()[:len(want)]]==[p['raw'] for p in want]
print('PASS zoom',seen,'map packets',found,'names')
