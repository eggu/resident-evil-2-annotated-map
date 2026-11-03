"""Pinned map data, stdlib only. Run from the repository root.
A projected locks (drawers) sit in the room they belong to; B no room-name leader shares a vertical/horizontal line
with a room outline: it leaves its own room clear of the corners and no wall runs beside it (right-angle crossings of an enclosing room are fine)."""
import json,re
from pathlib import Path
R=Path(__file__).resolve().parent.parent
PROJ,CLEAR,MARGIN=6,2,3
def rows(path,name):
 body=(R/'src'/path).read_text().split(name,1)[1].split('={',1)[-1].split('};',1)[0]
 return [tuple(int(v,0) for v in m.split(',')) for m in re.findall(r'\{([-0-9x, ]+)\}',body)]
floors={}
for f in json.loads((R/'data/room_shapes.json').read_text())['floors']:
 grid=floors.setdefault((f['pl'],f['floor']),{})
 for s in f['rooms']:
  for y,runs in enumerate(s['runs']):
   for a,n in runs:
    for x in range(a,a+n):grid[(s['x']+x,s['y']+y)]=s['seen']
failures=[]
for pl,floor,x,y,seen,unlock,key,mask,bank in rows('doors-all.h','doors[]'):
 if key in (31,48) and floors[(pl,floor)].get((x,y))!=seen: # Small Key / Lockpick are always drawers, never doors
  failures.append(('drawer outside its room',pl,floor,x,y,seen,floors[(pl,floor)].get((x,y))))
for name in ('room_names-en.h','room_names-ko.h'):
 for pl,floor,seen,x,y,label,sx,sy,ex,ey in rows(name,'[]'):
  if not sx|sy|ex|ey:continue
  grid=floors[(pl,floor)];px,py=(1,0) if sx==ex else (0,1)
  a=b=0
  while grid.get((sx+px*(a+1),sy+py*(a+1)))==grid.get((sx,sy)):a+=1
  while grid.get((sx-px*(b+1),sy-py*(b+1)))==grid.get((sx,sy)):b+=1
  if min(a,b)<min(MARGIN,(a+b)//2) or not a+b:failures.append((name,'starts at a corner',pl,floor,seen,(sx,sy,ex,ey)))
  n=max(abs(ex-sx),abs(ey-sy));dx,dy=(ex>sx)-(ex<sx),(ey>sy)-(ey<sy)
  for k in range(1,n+1):
   p=(sx+dx*k,sy+dy*k)
   if any(grid.get((p[0]+px*d,p[1]+py*d))!=grid.get(p) for d in (-CLEAR,-1,1,CLEAR)):
    failures.append((name,'runs along an outline',pl,floor,seen,(sx,sy,ex,ey)));break
for f in failures:print(f)
assert not failures,f'{len(failures)} geometry failures'
print('PASS map geometry')
