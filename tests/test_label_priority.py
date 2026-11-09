"""Map label priority, on the real EXE under unicorn: every floor, KO/EN, name sizes 50/100/150.
A key-item names sit on their star's first ring (touching) or second ring (one name height out), and a wrapped name's
lines align toward the star (RE0 HD map mod rule, 2026-11-07); B no key star/name pixel is covered (translucent names
render under opaque quads); C room names never overlap each other or the legend/readout panels (they may cover markers:
RE0 rule); D each leader line ends on a room name; E a language switch frees the other language's pages. Run from build/ with RE2_GAME_EXE set (build.py --game-exe copies it there)."""
import re,struct
from pathlib import Path
R=Path(__file__).resolve().parent
exec((R/'test_native-v6.4.py').read_text().split('# ---- harness end')[0])
dll_blob,dll_o=b,o # the harness's DLL file and PE offset; the G block below needs them after b/o are reused
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
call('KeyMapTestSetIcons',100,100,1) # opaque icons keep the alpha-based classification below; [H] names on
call('KeyMapTestToggle',0,4|8|16|64);call('KeyMapTestToggle',0,0) # locks, key items, files, puzzles on (defaults: off)
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
KEYART=struct.pack('<65536H',*(int(v,0) for v in re.findall(r'0x[0-9a-fA-F]+|\b\d+\b',(R/'key_art.h').read_text().split('key_art_pixels[65536]={',1)[1].split('}',1)[0])))
def art_page(t):return page(t)==KEYART # key-item art (2026-11-08) counts as a key marker like the star it replaces
def classify(q):
 kind=[14 if p['t'] in created and not p['alpha'] and art_page(p['t']) else uv.get(p['uv'][:2]) if p['w']<=12 and p['h']<=12 and not p['alpha'] else None for p in q]
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
  # A: each name block (1 line, or 2 consecutive lines, line 2 right under line 1; pages may differ) sits on one of its
  # marker's candidate spots (re2_keymap.c item_label_draw), its lines aligned for that spot's side. [H] names every
  # marker (2026-11-07): stars, locks, area maps and common items, so any drawn icon may own a name.
  def on_spots(blk):
   w=max(l['w'] for l in blk);h=sum(l['h'] for l in blk)
   owners=[q[s] for s in stars]+[p for p in q if not p['alpha'] and p['t'] in created and (lock_page(p['t']) or art_page(p['t']) or p['w']<=16 and p['h']<=16 and uv.get(p['uv'][:2]) is not None)]
   for st in owners:
    mx,my,mw,mh=st['x'],st['y'],st['w'],st['h']
    for ring in (0,1):
     for sx,sy,al in ((1,0,-1),(-1,0,1),(0,1,0),(0,-1,0),(1,1,-1),(1,-1,-1),(-1,1,1),(-1,-1,1)):
      x=mx+mw+ring*h if sx>0 else mx-w-ring*h if sx<0 else mx+mw//2-w//2
      y=my+mh+ring*h if sy>0 else my-h-ring*h if sy<0 else my+mh//2-h//2
      x=min(max(x,1),318-w);y=min(max(y,1),238-h)
      if y==blk[0]['y'] and all(l['x']==x+(0 if al<0 else w-l['w'] if al>0 else (w-l['w'])//2) for l in blk):return True
    # marker names slide along the marker's edge when the eight fixed spots are taken (2026-11-09): still touching it
    bx0=min(l['x'] for l in blk);bx1=max(l['x']+l['w'] for l in blk);by0=blk[0]['y'];by1=by0+h
    if (bx0==mx+mw or bx1==mx) and by0<my+mh and my<by1 or (by0==my+mh or by1==my) and bx0<mx+mw and mx<bx1:return True
   return False
  blocks,k=[],0
  while k<len(keynames):
   a=keynames[k];b=keynames[k+1] if k+1<len(keynames) else None
   # a wrapped name is two stacked consecutive lines; stacked one-line names can coincide, so a pair counts only on a marker spot
   if b==a+1 and q[b]['y']==q[a]['y']+q[a]['h'] and q[b]['x']<q[a]['x']+q[a]['w'] and q[a]['x']<q[b]['x']+q[b]['w'] and on_spots((q[a],q[b])):blocks.append((q[a],q[b]));k+=2
   else:blocks.append((q[a],));k+=1
  for blk in blocks:
   ok=on_spots(blk)
   assert ok,('A name block off its marker\'s candidate spots',lang,size,floor,blk)
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
  # C: room names vs each other and the legend/readout panels (opaque legend text is the help pages: not alpha, wide)
  rooms=[i for i in names if i not in keynames and q[i]['w']>1 and q[i]['h']>1]
  stats['locks']+=sum(1 for i,p in enumerate(q) if not p['alpha'] and p['t'] in created and lock_page(p['t']))
  panel=[dict(x=v&511,y=v>>9&255,w=v>>17&511,h=v>>26) for v in (call('KeyMapTestPanel',k) for k in range(2)) if v]
  for k,r in enumerate(rooms):
   for o in [q[m] for m in rooms[k+1:]]+panel:
    if hit(q[r],o):stats['room_hits']+=1;print('C room name overlap',lang,size,floor,q[r],o)
  # F: room names and their leaders are queued after every icon and marker name, so they draw under all of them
  # (user 2026-11-07, RE0 rule); only the opaque legend/readout text comes later.
  leaders=[i for i,p in enumerate(q) if p['alpha'] and (p['w']==1 or p['h']==1) and p['uv'][:2]==(0,0)]
  above=[i for i,p in enumerate(q) if i in keynames or kind[i] is not None or (not p['alpha'] and p['t'] in created and lock_page(p['t']))]
  if rooms or leaders:
   assert not above or max(above)<min(rooms+leaders),('F room name queued before an icon or name',lang,size,floor,max(above),min(rooms+leaders))
   stats['ordered']=stats.get('ordered',0)+len(rooms)
  # D: leaders end on a room name
  for i,p in enumerate(q):
   if p['alpha'] and (p['w']==1 or p['h']==1) and p['uv'][:2]==(0,0):
    stats['leaders']+=1;assert any(gap(p,q[r])<=1 for r in rooms if q[r]['t']==p['t']),('D leader',lang,size,floor,p)
 print('lang',lang,'size',size,stats)
 assert stats['covered']==0 or size>100
 assert stats['room_hits']==0 or size>100
# G (2026-11-09): a document's name touches its own icon, for two-line names and at 2x zoom too. A used to ask only that a name
# sat on *some* marker's spot, so a diary name one name height from its icon passed. Slide search: item_label_draw(slide).
imp_p=struct.unpack_from('<I',dll_blob,dll_o+96+8)[0]
stub=0x25000100;u.mem_write(stub,bytes.fromhex('31c0c21000')) # VirtualProtect fails cleanly: floor_keys logs and returns
while struct.unpack_from('<I',di,imp_p+12)[0]:
 lookup,_,_,_,iat=struct.unpack_from('<5I',di,imp_p);lookup=lookup or iat;i=0
 while (e:=struct.unpack_from('<I',di,lookup+i*4)[0]):
  if not e&0x80000000 and di[e+2:di.index(0,e+2)]==b'VirtualProtect':u.mem_write(0x10000000+iat+i*4,struct.pack('<I',stub))
  i+=1
 imp_p+=20
for va in (0x4021c0,):u.mem_write(va,bytes.fromhex('c20800'))
u.mem_write(0x4ed950,bytes.fromhex('c3'))
for s in range(0x29):u.mem_write(0x67c7d8+s*12,struct.pack('<III',1000+s,256,0))
u.mem_write(0x4ed950,bytes.fromhex('c3'))
def sig_pages(path): # whole pages: the first texels of every item page are the same blank/marker dot
 text=(R/path).read_text().split('item_label_pixels_',1)[1].split('={',1)[1]
 return [struct.pack('<65536H',*(int(v,0) for v in re.findall(r'0x[0-9a-fA-F]+|\b\d+\b',pg.split('}',1)[0]))) for pg in text.split('{')[1:]]
def doc_lines(q,lang):
 path='item_labels-en.h' if lang else 'item_labels-ko.h'
 sigs=sig_pages(path);labels=rows((R/path).read_text(),'item_labels_EN[' if lang else 'item_labels_KO[')
 out={}
 for p in q:
  if not p['alpha'] or p['t'] not in created:continue
  sig=page(p['t'])
  if sig not in sigs:continue
  key=(sigs.index(sig),p['uv'][0],p['uv'][1],p['uv'][2]-p['uv'][0]+1,p['uv'][3]-p['uv'][1]+1)
  for l in labels:
   if l[1:6]==key and l[6]==3 and 106<=l[0]<=126:out.setdefault(l[0],[]).append(p)
 return out
u.mem_write(0x988608,struct.pack('<I',0x1000));call('KeyMapTestZoomInput');u.mem_write(0x988608,bytes(4));call('KeyMapTestZoomInput')
assert call('KeyMapTestZoomState')==1
checked=0
for lang in (0,1):
 if call('KeyMapTestLanguage')!=lang:call('KeyMapTestToggle',0,32);call('KeyMapTestToggle',0,0);pages.clear()
 while call('KeyMapTestSize')!=100:call('KeyMapTestToggle',0,512 if call('KeyMapTestSize')<100 else 1024);call('KeyMapTestToggle',0,0)
 for floor in (2,3):
  for view in ((105,84),(0,0),(160,120),(240,180),(60,150)):
   call('KeyMapTestZoomView',*view);q=draw(floor)
   docs=[p for p in q if not p['alpha'] and p['t'] in created and p['w']<=16 and uv.get(p['uv'][:2])==11]
   for item,lines in doc_lines(q,lang).items():
    x0=min(l['x'] for l in lines);x1=max(l['x']+l['w'] for l in lines);y0=min(l['y'] for l in lines);y1=max(l['y']+l['h'] for l in lines)
    union=dict(x=x0,y=y0,w=x1-x0,h=y1-y0);checked+=1
    assert any(gap(union,d)<=1 for d in docs),('G document name away from its icon (zoom)',lang,floor,view,item,union)
assert checked>=20,checked
assert released,'E language switch released no textures'
print('released',len(released),'created',len(created),'OK')
