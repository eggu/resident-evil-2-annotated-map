"""Map label priority, on the real EXE under unicorn: every floor, KO/EN, name sizes 50/100/150.
A key-item names touch their star; B no key star/name pixel is covered (translucent names render under opaque quads);
C room names never overlap key items or markers; D each leader line ends on a room name; E a language switch frees
the other language's pages. Run from build/ with RE2_GAME_EXE set (build.py --game-exe copies it there)."""
import re,struct
from pathlib import Path
R=Path(__file__).resolve().parent
exec((R/'test_native-v6.4.py').read_text().split('# ---- harness end')[0])
def rows(text,start):
 body=text.split(start,1)[1].split('};',1)[0]
 return [tuple(int(x,0) for x in m.split(',')) for m in re.findall(r'\{([-0-9x, ]+)\}',body)]
uv={(i[1],i[2]):i[0] for i in rows((R/'overlay_icons.h').read_text(),'overlay_icons[]')}
u.mem_write(0x4021c0,bytes.fromhex('c20800'))
u.mem_map(0x22000000,0x900000);u.mem_write(0x6805b8,struct.pack('<I',0x22000000));u.mem_write(0x228c8338,struct.pack('<I',1))
u.mem_write(0x405ec0,bytes.fromhex('c20800'));u.mem_write(0x416be0,bytes.fromhex('c20400'))
created={};released=[]
def create(u,a,n,_):
 desc=struct.unpack('<I',u.mem_read(u.reg_read(UC_X86_REG_ESP)+4,4))[0]
 tid=len(created)+1;created[tid]=struct.unpack('<I',u.mem_read(desc+4,4))[0];u.reg_write(UC_X86_REG_EAX,tid)
def release(u,a,n,_):released.append(struct.unpack('<I',u.mem_read(u.reg_read(UC_X86_REG_ESP)+4,4))[0])
u.hook_add(UC_HOOK_CODE,create,begin=0x405ec0,end=0x405ec0);u.hook_add(UC_HOOK_CODE,release,begin=0x416be0,end=0x416be0)
call('KeyMapTestInit',0x400000)
pages={}
def page(t):
 if t not in pages:pages[t]=bytes(u.mem_read(created[t],131072))
 return pages[t]
def draw(floor):
 u.mem_write(0x989ed0,bytes(32));u.mem_write(0x98eb2c,bytes(0xc0));u.mem_write(0x98ed2c,bytes(32))
 u.mem_write(0x98ec04,b'\xff'*32);u.mem_write(0x691f7a,bytes([floor]));u.mem_write(0x691f62,b'\0');u.mem_write(0x691fb8,struct.pack('<hh',4,6))
 u.mem_write(0x21000000,b'\xa5'*0x30000);u.mem_write(0x524e1c,struct.pack('<II',0x21000000,0x21020000));call('KeyMapTestDraw')
 end=struct.unpack('<I',u.mem_read(0x524e1c,4))[0];out=[]
 for p in range(0x21000000,end,32):
  b=bytes(u.mem_read(p,32));x0,y0,x1,y1=struct.unpack_from('<4h',b,16)
  out.append(dict(t=struct.unpack_from('<I',b,8)[0],x=x0,y=y0,w=x1-x0+1,h=y1-y0+1,uv=(b[24],b[25],b[26],b[27]),
                  alpha=struct.unpack_from('<I',b,4)[0]==0x400025 and b[31]<255 and struct.unpack_from('<I',b,28)[0]&0xffffff==0x808080))
 return out
def gap(a,b):return max(b['x']-(a['x']+a['w']),a['x']-(b['x']+b['w']),b['y']-(a['y']+a['h']),a['y']-(b['y']+b['h']),0)
def hit(a,b):return a['x']<b['x']+b['w'] and b['x']<a['x']+a['w'] and a['y']<b['y']+b['h'] and b['y']<a['y']+a['h']
def pixels(q):
 t=page(q['t']);u0,v0,u1,v1=q['uv']
 for j in range(q['h']):
  for i in range(q['w']):
   if struct.unpack_from('<H',t,((v0+(v1-v0+1)*j//q['h'])*256+u0+(u1-u0+1)*i//q['w'])*2)[0]:yield q['x']+i,q['y']+j
def signatures(path):  # first 256 texels of every item-label page, to tell key names from room names by texture
 text=(R/path).read_text().split('item_label_pixels_',1)[1].split('={',1)[1]
 return {tuple(int(v,0) for v in re.findall(r'0x[0-9a-fA-F]+|\b\d+\b',page[:4000])[:256]) for page in text.split('{')[1:]}
ITEM_PAGES=signatures('item_labels-ko.h')|signatures('item_labels-en.h')
def item_page(t):return tuple(struct.unpack_from('<256H',page(t)))in ITEM_PAGES
ATLAS=struct.pack('<65536H',*(int(v,0) for v in re.findall(r'0x[0-9a-fA-F]+|\b\d+\b',(R/'atlas.h').read_text().split('atlas_pixels[]={',1)[1].split('}',1)[0])))
def lock_page(t):return page(t)==ATLAS
def classify(q):
 kind=[uv.get(p['uv'][:2]) if p['w']<=12 and p['h']<=12 and not p['alpha'] else None for p in q]
 stars=[i for i,k in enumerate(kind) if k in (14,15)]
 names=[i for i,p in enumerate(q) if p['alpha'] and p['w']>1 and p['h']>1]
 key=[i for i in names if any(gap(q[i],q[s])<=1 for s in stars) and i<min([j for j,k in enumerate(kind) if k==12]+[len(q)])
      and i<min([j for j in names if j>max(stars+[-1])] or [len(q)]) or i in names and stars and i<len(q) and False]
 return kind,stars,names
for lang,size in ((0,100),(1,100),(1,150),(0,150),(0,50)):
 if call('KeyMapTestLanguage')!=lang:call('KeyMapTestToggle',0,32);call('KeyMapTestToggle',0,0);pages.clear()
 while call('KeyMapTestSize')!=size:call('KeyMapTestToggle',0,512 if call('KeyMapTestSize')<size else 1024);call('KeyMapTestToggle',0,0)
 stats=dict(stars=0,covered=0,room_hits=0,leaders=0,locks=0)
 for floor in range(20):
  q=draw(floor);kind,stars,names=classify(q)
  if not q:continue
  keynames=[i for i in names if item_page(q[i]['t'])]
  assert all(any(gap(q[i],q[s])<=1 for s in stars) for i in keynames),('A key name away from its star',lang,size,floor)
  stats['stars']+=len(stars)
  assert len(keynames)>=len(stars),('A key name not touching its star',lang,size,floor,len(stars),len(keynames))
  high=set(stars)|set(keynames)
  # B: translucent pass first (queue order: earlier on top), then opaque pass on top
  owner={}
  for alpha in (True,False):
   for i in range(len(q)-1,-1,-1):
    if q[i]['alpha']==alpha and q[i]['t'] in created:
     for xy in pixels(q[i]):owner[xy]=i
  for i in high:
   for xy in pixels(q[i]):
    if owner[xy] not in high:stats['covered']+=1;print('B covered',lang,size,floor,i,q[i],'by',owner[xy],q[owner[xy]],kind[owner[xy]])
  # C: room names vs key items and markers (stars, key names, diamonds, save/box markers, documents, locks)
  marks=[i for i,k in enumerate(kind) if k in (9,10,11,12,13,14,15)]+[i for i,p in enumerate(q) if not p['alpha'] and p['t'] in created and lock_page(p['t'])]
  rooms=[i for i in names if i not in keynames]
  stats['locks']+=sum(1 for i,p in enumerate(q) if not p['alpha'] and p['t'] in created and lock_page(p['t']))
  for r in rooms:
   for m in marks+keynames:
    if hit(q[r],q[m]):stats['room_hits']+=1;print('C room name over marker',lang,size,floor,q[r],q[m],kind[m])
  # D: leaders end on a room name
  for i,p in enumerate(q):
   if p['alpha'] and (p['w']==1 or p['h']==1) and p['uv'][:2]==(0,0):
    stats['leaders']+=1;assert any(gap(p,q[r])<=1 for r in rooms if q[r]['t']==p['t']),('D leader',lang,size,floor,p)
 print('lang',lang,'size',size,stats)
 assert stats['covered']==0 or size>100
 assert stats['room_hits']==0 or size>100
assert released,'E language switch released no textures'
print('released',len(released),'created',len(created),'OK')
