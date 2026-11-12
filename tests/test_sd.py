"""SD mode (no HD pack; 2026-11-12). Table checks: every named room has an SD name inside the screen, outside every room, clear of
the screen furniture and of every possible marker, no two names overlap, each leader starts 1..3 px inside its own room and ends
at the name (the box starts on the next pixel; the sprite's ink bounds may trim a pixel); the atlas sprites stay inside 8-bit texture coordinates and carry pixels; every door key has an approved lock.
Emulated draw on the real EXE with SD forced: every quad is a 1:1 sprite (or a 1 px leader) on screen, the legend is text, no opacity
packets, no item names; detection follows DisplayMode. Run from build/ with RE2_GAME_EXE set (data/ and fixtures copied)."""
import json,re,struct
from pathlib import Path
R=Path(__file__).resolve().parent
exec((R/'test_native-v6.4.py').read_text().split('# ---- harness end')[0])
import numpy as np
def arr(text,name):
 body=text.split(name,1)[1].split('};',1)[0]
 return body
assets=(R/'sd_assets.h').read_text()
SPR=[tuple(map(int,m)) for m in re.findall(r'\{(\d+),(\d+),(\d+),(\d+),(\d+)\}',arr(assets,'sd_sprites[] = {'))]
PX=np.array([int(v,16) for v in re.findall(r'0x[0-9a-f]+',assets.split('sd_pixels[SD_PAGES][65536] = {',1)[1])],np.uint16).reshape(-1,256,256)
assert len(PX)==int(re.search(r'#define SD_PAGES (\d+)',assets)[1])
for page,su,sv,sw,sh in SPR:
 assert su+sw<256 and sv+sh<256,(page,su,sv,sw,sh)                # 8-bit texture coordinates: u+w, v+h stay below 256
 assert PX[page,sv:sv+sh,su:su+sw].any(),(page,su,sv,sw,sh)
# --- layout tables
layout=json.loads((R/'sd-layout.json').read_text())
shapes=json.loads((R/'room_shapes.json').read_text())['floors']
def hrows(name):
 return [(int(m[1]),int(m[2]),int(m[3]),m[4],m[5]) for l in (R/name).read_text().splitlines() if (m:=re.match(r'\{(\d+),(\d+),(\d+),.*\}, /\* ([\w,]+) (.*) \*/',l))]
def rect_cells(r):return {(r['x']+x,r['y']+j) for j,runs in enumerate(r['runs']) for a,n in runs for x in range(a,min(a+n,r['w']))}
def struct_rows(path,name):
 t=(R/path).read_text();t=t[t.index(name+'[]'):];t=t[:t.index('};')]
 return [tuple(int(v) for v in re.findall(r'-?\d+',m)) for m in re.findall(r'\{([^{}]*)\}',t[t.index('{')+1:])]
marks={}
def add(pl,fl,x,y):marks.setdefault((pl&1,fl),set()).add((x,y))
for r in struct_rows('items.h','map_items'):add(r[0],r[1],r[2]+6,r[3]+6)
for r in struct_rows('overlay_data.h','map_markers'):add(r[0],r[1],r[4]+6,r[5]+6)
for r in struct_rows('overlay_data.h','map_documents'):add(r[0],r[1],r[5]+6,r[6]+6)
for r in struct_rows('overlay_data.h','map_interactions'):
 if r[3] in (6,20):add(r[0],r[1],r[4]+6,r[5]+6)
doors=struct_rows('doors-all.h','doors')
for r in doors:add(r[0],r[1],r[2],r[3])
HUD=[(8,14,100,36),(252,24,30,44),(154,18,12,9),(154,196,12,9),(5,114,9,12),(306,114,9,12)]
def gap(a,b):return max(a[0]-(b[0]+b[2]),b[0]-(a[0]+a[2]),a[1]-(b[1]+b[3]),b[1]-(a[1]+a[3]))
sprites={}
for lang in ('en','ko'):
 rows=hrows(f'room_names-{lang}.h')
 body=arr(assets,f'sd_rooms_{lang}[] = {{')
 table=re.findall(r'\{(\d+),(-?\d+),(-?\d+),(\d+),\{([-\d,]+)\},(\d+),(-?\d+),(-?\d+),(\d+),\{([-\d,]+)\}\}',body)
 assert len(table)==len(rows)==248==len([l for l in (R/f'room_names-{lang}.h').read_text().splitlines() if l.startswith('{')])   # every runtime row
 if lang=='en':table_en=table
 by_floor={}
 for j,(pl,fl,seen,code,name) in enumerate(rows):
  sp,x,y,n,pts,isp,ix,iy,zn,zpts=table[j];sp,x,y,n,isp,ix,iy,zn=int(sp),int(x),int(y),int(n),int(isp),int(ix),int(iy),int(zn);zpts=[int(v) for v in zpts.split(',')];pts=[int(v) for v in pts.split(',')]
  assert sp!=0xFFFF,(lang,code,name)
  _,_,_,w,h=SPR[sp];assert n>=2,(lang,name,'no leader')
  box=(x,y,w-1,h-1);assert 2<=x and x+w<=318 and 2<=y and y+h<=238,(lang,name,box)
  by_floor.setdefault((pl,fl),[]).append((seen,name,box,[(pts[2*k],pts[2*k+1]) for k in range(n)],(isp,ix,iy),(zn,zpts)))
 for (pl,fl),names in by_floor.items():
  rects=next(f['rooms'] for f in shapes if (f['pl'],f['floor'])==(pl,fl));cells={r['seen']:rect_cells(r) for r in rects};allc=set().union(*cells.values())
  boxes=[b for _,_,b,_,_,_ in names]
  inner=[]
  for i,(seen,name,box,leader,(isp,ix,iy),(zn,zpts)) in enumerate(names):
   x,y,w,h=box
   if isp==0xFFFF:   # 2x leader: horizontal/vertical, at most one bend, starts 1..3 px inside the doubled room, ends at the doubled end
    assert zn in (1,2),(lang,pl,fl,name,'no 2x leader')
    c2={(2*a+i2,2*b+j2) for a,b in cells[seen] for i2 in (0,1) for j2 in (0,1)};pts2=[(zpts[2*k],zpts[2*k+1]) for k in range(zn)]+[(2*leader[-1][0],2*leader[-1][1])]
    assert pts2[0] in c2,(lang,pl,fl,name,'2x leader starts outside its room')
    assert all(a_[0]==b_[0] or a_[1]==b_[1] for a_,b_ in zip(pts2,pts2[1:])),(lang,pl,fl,name,'2x leader is not horizontal/vertical',pts2)
   if isp!=0xFFFF:   # 2x zoom: the name inside its doubled room, clear of the 9x9 markers, clear of the other inside names
    _,_,_,iw,ih=SPR[isp];c2={(2*a+i2,2*b+j2) for a,b in cells[seen] for i2 in (0,1) for j2 in (0,1)}
    assert all((ix+i2,iy+j2) in c2 for i2 in range(iw) for j2 in range(ih)),(lang,pl,fl,name,'inside name leaves its room')
    for mx,my in marks.get((pl,fl),()):assert not(ix<2*mx+5 and 2*mx-4<ix+iw and iy<2*my+5 and 2*my-4<iy+ih),(lang,pl,fl,name,'inside name on a marker')
    for k0 in inner:assert not(ix<k0[0]+k0[2] and k0[0]<ix+iw and iy<k0[1]+k0[3] and k0[1]<iy+ih),(lang,pl,fl,name,'inside names overlap')
    inner.append((ix,iy,iw,ih))
   assert not any((x+i2,y+j2) in allc for i2 in range(w) for j2 in range(h)),(lang,pl,fl,name,'name on a room')
   for hx,hy,hw,hh in HUD:assert not(x<hx+hw and hx<x+w and y<hy+hh and hy<y+h),(lang,pl,fl,name,'on screen furniture')
   for mx,my in marks.get((pl,fl),()):assert not(x<mx+5 and mx-4<x+w and y<my+5 and my-4<y+h),(lang,pl,fl,name,'on a marker',mx,my)
   for k in range(i):assert gap(box,boxes[k])>=1,(lang,pl,fl,name,names[k][1],'names overlap')
   sx,sy=leader[0];assert (sx,sy) in cells[seen],(lang,name,'leader start outside its room')
   ex,ey=leader[-1];assert gap((ex,ey,1,1),box)==0,(lang,pl,fl,name,'leader end far from the name',leader,box)
# every key that opens a door has an approved SD lock
lock=[int(v,0) for v in re.findall(r'0x[0-9A-Fa-f]+|\d+',arr(assets,'sd_lock_sprite[100] = {').split('}')[0])]
missing={k[6] for k in doors if k[6]<100 and lock[k[6]]==0xFFFF}
assert not missing,missing
# --- emulated draw
for va in (0x4021c0,):u.mem_write(va,bytes.fromhex('c20800'))
call('KeyMapTestInit',0x400000);call('KeyMapTestTexture',5000)
def draw(floor,zoom=False):
 u.mem_write(0x989ed0,bytes(32));u.mem_write(0x98eb2c,bytes(0xc0));u.mem_write(0x98ed2c,bytes(32));u.mem_write(0x98ec04,b'\xff'*32)
 u.mem_write(0x691f7a,bytes([floor]));u.mem_write(0x691f62,b'\0');u.mem_write(0x691fb8,bytes(4))
 u.mem_write(0x21000000,b'\xa5'*0x40000);u.mem_write(0x524e1c,struct.pack('<II',0x21000000,0x21040000));call('KeyMapTestDraw')
 end=struct.unpack('<I',u.mem_read(0x524e1c,4))[0];out=[]
 for p in range(0x21000000,end,32):
  d=bytes(u.mem_read(p,32));x0,y0,x1,y1=struct.unpack_from('<4h',d,16)
  out.append(dict(cmd=struct.unpack_from('<I',d,4)[0],t=struct.unpack_from('<I',d,8)[0],x0=x0,y0=y0,x1=x1,y1=y1,uv=tuple(d[24:28])))
 return out
def toggle(bit):call('KeyMapTestToggle',0,bit);call('KeyMapTestToggle',0,0)
# imports with more than one argument need their own stub (the harness stub pops one argument)
def stub_import(name,ret):
 imp_p=struct.unpack_from('<I',b,o+96+8)[0];addr=0x25000200+len(name)*16
 u.mem_write(addr,bytes.fromhex('31c0c2')+struct.pack('<H',ret))
 while struct.unpack_from('<I',di,imp_p+12)[0]:
  lookup,_,_,_,iat=struct.unpack_from('<5I',di,imp_p);lookup=lookup or iat;i=0
  while (e:=struct.unpack_from('<I',di,lookup+i*4)[0]):
   if not e&0x80000000 and di[e+2:di.index(0,e+2)]==name.encode():u.mem_write(0x10000000+iat+i*4,struct.pack('<I',addr))
   i+=1
  imp_p+=20
stub_import('GetPrivateProfileIntA',16);stub_import('lstrcpyA',8)
# detection: the stubbed imports read 0 (no config keys, no bio2hd module), so Auto = SD; HD and SD force their mode
assert call('KeyMapTestSdDecide',0,0x20000000)==1 and call('KeyMapTestSdDecide',1,0x20000000)==0 and call('KeyMapTestSdDecide',2,0x20000000)==1
# Auto decision table (user 2026-11-13): HD only with Classic REbirth AND the HD pack AND RetroMode off AND LowResEnable off
for rebirth in (0,1):
 for hd in (0,1):
  for retro in (0,1):
   for low in (0,1):assert call('KeyMapTestSdAuto',rebirth,hd,retro,low)==(0 if (rebirth and hd and not retro and not low) else 1),(rebirth,hd,retro,low)
call('KeyMapTestSdMode',1)
for bit in (4,8,16,64,128,256,131072):toggle(bit)       # every category on
toggle(4096);toggle(4096)                              # scope 3
assert call('KeyMapTestScope')==3
rect_of={(su,sv,sw,sh) for _,su,sv,sw,sh in SPR}
for floor in (2,3,4,9,13,16):
 q=draw(floor);assert len(q)>20,floor
 for p in q:
  assert p['t']==5000 and p['cmd']==0x24,p                        # one texture, opaque: no opacity packets in SD
  assert 1<=p['x0']<=p['x1']<=318 and 1<=p['y0']<=p['y1']<=238,p
  w,h=p['x1']-p['x0']+1,p['y1']-p['y0']+1;uw,uh=p['uv'][2]-p['uv'][0]+1,p['uv'][3]-p['uv'][1]+1
  if (uw,uh)==(1,1):continue                                       # a 1 px leader run (or the unit-sized texel)
  assert (uw,uh)==(w,h),p                                          # 1:1 texels
  assert (p['uv'][0],p['uv'][1],w,h) in rect_of,p                  # an SD sprite, not an HD atlas cell
 # every room name of the screen (English, all rooms shown) sits at its layout position, 1:1, unless the legend pushed it
 pos={(p['x0'],p['y0'],p['x1']-p['x0']+1,p['y1']-p['y0']+1) for p in q}
 for j,(pl,fl,seen,code,name) in enumerate(hrows('room_names-en.h')):
  if (pl,fl)!=(0,floor):continue
  sp,x,y,n,_,_,_,_,_,_=table_en[j];_,_,_,w,h=SPR[int(sp)]
  assert (int(x),int(y),w,h) in pos or int(y)+h>238-5*11-6,(floor,name)
 legend=[p for p in q if p['y0']>=238-5*11-4]
 assert len(legend)>=14,(floor,len(legend))                       # title, hide, 12 rows (+ names that sit above)
for lang_toggle in (32,):
 toggle(lang_toggle);q=draw(2);assert call('KeyMapTestLanguage')==0 and len(q)>30
 toggle(lang_toggle)


# Lock markers (2026-11-13): beside the native 8x8 door bar, in the room not entered yet, in SD too. All rooms visited here, so the destination
# side: out from the bar centre towards that room's centre, clear of the bar (4 + 4 + 1 px); LockSide=0 keeps the marker on the door (x,y).
def lock_quads(floor,rect):
 return [(p['x0']+4,p['y0']+4) for p in draw(floor) if p['t']==5000 and (p['uv'][0],p['uv'][1],p['x1']-p['x0']+1,p['y1']-p['y0']+1)==rect]
checked=exact=0
for floor in range(2,20):
 here=[d for d in doors if d[0]==0 and d[1]==floor and d[6]<100 and lock[d[6]]!=0xFFFF and d[7]==0 and d[8]==255 and d[13]!=255 and (d[2],d[3])!=(d[11],d[12])]
 for d in here:
  _,_,su,sv,sw,sh=SPR[lock[d[6]]] and (0,)+SPR[lock[d[6]]]
  rect=(su,sv,sw,sh);same=[e for e in here if lock[e[6]]==lock[d[6]]]
  if len(same)!=1 or not(6<=d[2]<=312 and 6<=d[3]<=232 and 6<=d[11]<=312 and 6<=d[12]<=232):continue
  call('KeyMapTestLockSide',0)
  if lock_quads(floor,rect)!=[(d[2],d[3])]:continue   # hidden under a key marker on this screen
  def bar_h():
   for va in range(0x53da70,0x53dae0,8):
    e=bytes(u.mem_read(va,8))
    if struct.unpack_from('<hh',e,4)==(d[2],d[3]):return e[3]&1
  ptr,count=struct.unpack('<IB',u.mem_read(0x53eaf8+floor*8,5));rc=None
  for k in range(count):
   qq=bytes(u.mem_read(ptr+k*16,16))
   if qq[12]==d[13]:rc=(struct.unpack_from('<h',qq,4)[0]+qq[2]//2,struct.unpack_from('<h',qq,6)[0]+qq[3]//2)
  hb=bar_h();aw,ah=((6,4) if hb else (4,6)) if hb is not None else (2,2);cx,cy=(d[2]+aw//2,d[3]+ah//2) if hb is not None else (d[2],d[3]);sx=-1 if rc[0]-cx<0 else 1;sy=-1 if rc[1]-cy<0 else 1
  tx,ty=aw//2+4,ah//2+4     # 9x9 marker touching the bar's art
  ax=(not hb) if hb is not None else abs(rc[0]-cx)>=abs(rc[1]-cy)
  cands=[(cx+sx*tx,cy),(cx,cy+sy*ty),(cx,cy-sy*ty),(cx-sx*tx,cy)] if ax else [(cx,cy+sy*ty),(cx+sx*tx,cy),(cx-sx*tx,cy),(cx,cy-sy*ty)]
  call('KeyMapTestLockSide',1)
  if any(c[0]<6 or c[0]>312 or c[1]<6 or c[1]>232 for c in cands):continue   # clamped to the screen
  got=lock_quads(floor,rect)
  assert len(got)==1 and got[0] in cands,(floor,d,cands,got)   # the first side no key marker covers
  exact+=got[0]==cands[0]
  call('KeyMapTestLockSide',0);checked+=1
assert checked>=3 and exact>=2,(checked,exact)
stub_import('VirtualProtect',16)   # floor_keys: VirtualProtect fails cleanly
u.mem_write(0x4ed950,bytes.fromhex('c3'));u.mem_map(0x22000000,0x10000);u.mem_write(0x6805b8,struct.pack('<I',0x22000000))
for k in range(0x29):u.mem_write(0x67c7d8+k*12,struct.pack('<III',1000+k,256,0))
# 2x zoom: markers and names keep their 1:1 size, names follow the map (leader start at 2x), nothing leaves the screen
def press(bit=0x1000):u.mem_write(0x988608,struct.pack('<I',bit));call('KeyMapTestZoomInput');u.mem_write(0x988608,bytes(4));call('KeyMapTestZoomInput')
press();assert call('KeyMapTestZoomState')==1
for vx,vy in ((160,120),(0,0),(320,240)):
 call('KeyMapTestZoomView',vx,vy);q=draw(2)
 assert len(q)>20
 for p in q:
  if p['t']!=5000:continue
  assert 1<=p['x0']<=p['x1']<=318 and 1<=p['y0']<=p['y1']<=238,p
  uw,uh=p['uv'][2]-p['uv'][0]+1,p['uv'][3]-p['uv'][1]+1
  assert (uw,uh)==(1,1) or (p['x1']-p['x0']+1,p['y1']-p['y0']+1)==(uw,uh) or p['x0']<=1 or p['x1']>=318 or p['y0']<=1 or p['y1']>=238,p   # 1:1 unless cropped at the edge
# zoomed: a name that fits inside its room is drawn there (doubled position minus the view), the others keep their leaders
call('KeyMapTestZoomView',160,120);q=draw(2);pos={(p['x0'],p['y0']) for p in q}
inside_drawn=0
for j,(pl,fl,seen,code,name) in enumerate(hrows('room_names-en.h')):
 if (pl,fl)!=(0,2):continue
 sp,x,y,n,_,isp,ix,iy,_,_=table_en[j]
 if int(isp)==0xFFFF:continue
 _,_,_,iw,ih=SPR[int(isp)];sx,sy=int(ix)-160,int(iy)-120
 if 2<=sx and 2<=sy and sx+iw<=318 and sy+ih<=238 and not(sy+ih>238-5*11-4 and sx<2+280):
  assert (sx,sy) in pos,(name,sx,sy);inside_drawn+=1
assert inside_drawn>=3,inside_drawn
# 2x zoom: the lock marker keeps its size and touches the doubled bar art (4x6 / 6x4 texels doubled)
call('KeyMapTestLockSide',1);call('KeyMapTestZoomView',60,150)
tested=0
for d in [e for e in doors if e[0]==0 and e[1]==2 and e[6] in (90,91,92)]:
 hb=None
 for va in range(0x53da70,0x53dae0,8):
  e=bytes(u.mem_read(va,8))
  if struct.unpack_from('<hh',e,4)==(d[2],d[3]):hb=e[3]&1
 aw,ah=(6,4) if hb else (4,6);cx,cy=2*(d[2]+aw//2)-60,2*(d[3]+ah//2)-150
 ptr,count=struct.unpack('<IB',u.mem_read(0x53eaf8+2*8,5))
 for k in range(count):
  qq=bytes(u.mem_read(ptr+k*16,16))
  if qq[12]==d[13]:rc=(struct.unpack_from('<h',qq,4)[0]+qq[2]//2,struct.unpack_from('<h',qq,6)[0]+qq[3]//2)
 sx=-1 if rc[0]-(d[2]+aw//2)<0 else 1;sy=-1 if rc[1]-(d[3]+ah//2)<0 else 1
 tx,ty=aw+4,ah+4
 cands=[(cx+sx*tx,cy),(cx,cy+sy*ty),(cx,cy-sy*ty),(cx-sx*tx,cy)] if not hb else [(cx,cy+sy*ty),(cx+sx*tx,cy),(cx-sx*tx,cy),(cx,cy-sy*ty)]
 _,_,su,sv,sw,sh=(0,)+SPR[lock[d[6]]]
 got=[(p['x0']+4,p['y0']+4) for p in draw(2) if p['t']==5000 and (p['uv'][0],p['uv'][1],p['x1']-p['x0']+1,p['y1']-p['y0']+1)==(su,sv,sw,sh)]
 if 12<=cx<=300 and 12<=cy<=160 and not any(c[1]>170 for c in cands):assert len(got)==1 and got[0] in cands,(d,cands,got);tested+=1
assert tested>=1,tested
call('KeyMapTestLockSide',0)
# names are part of the map: panning moves every drawn name by exactly the view change (no pulling to the screen edge, no leader re-ending)
def sprite_quads(vx,vy):
 call('KeyMapTestZoomView',vx,vy);return [(p['x0'],p['y0'],p['x1']-p['x0']+1,p['y1']-p['y0']+1) for p in draw(2) if p['t']==5000]
va,vb=sprite_quads(120,90),sprite_quads(150,110)
moved=0
for j,(pl,fl,seen,code,name) in enumerate(hrows('room_names-en.h')):
 if (pl,fl)!=(0,2):continue
 sp,x,y,n,pts,isp,ix,iy,_,_=table_en[j];_,_,_,w,h=SPR[int(sp)];pts=[int(v) for v in pts.split(',')];n=int(n)
 a_=(2*pts[2*n-2]-120+int(x)-pts[2*n-2],2*pts[2*n-1]-90+int(y)-pts[2*n-1],w,h)   # leader end follows the map, the name keeps its offset
 b_=(a_[0]-30,a_[1]-20,w,h)
 if int(isp)==0xFFFF and 8<=a_[0] and a_[0]+w<=310 and 8<=a_[1] and a_[1]+h<=230 and 8<=b_[0] and b_[0]+w<=310 and 8<=b_[1] and b_[1]+h<=230 and not (a_[1]+h>180 or b_[1]+h>180):
  assert a_ in va and b_ in vb,(name,a_,b_);moved+=1
assert moved>=2,moved
# 2x leaders are exactly horizontal or vertical: every 1 px leader run of a zoomed frame is a one-pixel-thick bar, never a staircase
call('KeyMapTestZoomView',100,60)
for floor in (2,3,13):
 q=draw(floor);runs=[p for p in q if (p['uv'][2]-p['uv'][0]+1,p['uv'][3]-p['uv'][1]+1)==(1,1) and p['t']==5000]
 assert runs,floor
 assert all(p['x0']==p['x1'] or p['y0']==p['y1'] for p in runs),(floor,[p for p in runs if p['x0']!=p['x1'] and p['y0']!=p['y1']][:3])
 assert len(runs)<=3*len(hrows('room_names-en.h')),len(runs)   # one or two bars per name, not a staircase of rows
print('SD tests passed')
