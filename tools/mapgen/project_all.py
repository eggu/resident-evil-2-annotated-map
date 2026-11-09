from pathlib import Path
import os,struct,json
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
from pathlib import Path
import struct,json
root=Path(os.environ['RE2_GAME']);b=(root/'Resident Evil 2.exe').read_bytes();pe=struct.unpack_from('<I',b,60)[0];secs=[]
for i in range(struct.unpack_from('<H',b,pe+6)[0]):
 o=pe+24+struct.unpack_from('<H',b,pe+20)[0]+40*i;vs,rv,rs,raw=struct.unpack_from('<IIII',b,o+8);secs.append((rv,rs,raw))
def off(va):
 for rv,rs,raw in secs:
  if rv<=va-0x400000<rv+rs:return raw+va-0x400000-rv

R=Path(__file__).resolve().parent;u=Uc(UC_ARCH_X86,UC_MODE_32);u.mem_map(0x400000,0x1000000)
for rv,rs,raw in secs:u.mem_write(0x400000+rv,b[raw:raw+rs])
u.mem_map(0x20000000,0x10000)
def call(fn,a,c):
 u.reg_write(UC_X86_REG_ESP,0x20008000);u.mem_write(0x20008000,struct.pack('<III',0x20000100,a,c));u.emu_start(fn,0x20000100,count=500);return u.reg_read(UC_X86_REG_EAX)
# The projector returns the top-left of the 12 px player cursor; items and markers add this too (re2_keymap.c PROJ_CENTRE).
# Without it the Reception Room drawer drew 2 px inside the West Office (user 2026-11-02). Native lock-table rows are not projected.
PROJ=6
a=json.loads((R/'all-locks.json').read_text());result=[]
from extract_items import NativeMap
native=NativeMap(b)
def sub_floors(pl,stage,room,raw):
 # Every map sub-floor the native picks for this room (NativeMap.floors), default state first.
 out=[]
 for level in (0,raw[4]):
  for f in native.floors(pl,stage,room,level):
   if f not in out:out.append(f)
 return out
def project(floor,ptr,index,x,z):
 u.mem_write(0x989f28,struct.pack('<i',x));u.mem_write(0x989f30,struct.pack('<i',z));u.mem_write(0x691fb8,b'\0'*4);u.reg_write(UC_X86_REG_EBX,ptr+index*16);u.reg_write(UC_X86_REG_EBP,0);u.reg_write(UC_X86_REG_ESI,0x20001000);u.emu_start(0x4faa19,0x4faae3,count=200)
 return tuple(v+PROJ for v in struct.unpack('<hh',u.mem_read(0x20001008,4)))
def other_side(pl,floor,raw):
 """LockSide=1 (RE1 HD map mod style, user 2026-11-07): the door AOT's own destination, Door_aot_se bytes 14..25
 (next x,y,z,cdir_y, next_stage, next_room, next_cut, next_nfloor). The arrival point is projected into the destination
 room when the native map draws that room on this floor; else (stairs, other floors) there is no other side (255)."""
 nx,nz=struct.unpack_from('<hxxh',raw,14);stage,room,level=raw[22],raw[23],raw[25]
 if floor not in native.floors(pl,stage,room,level):return 0,0,255
 index=call(0x4fb1c0,floor,room);table=0x53eb98 if pl else 0x53eaf8;ptr,cnt=struct.unpack_from('<IB',b,off(table)+floor*8)
 if index>=cnt:return 0,0,255
 return project(floor,ptr,index,nx,nz)+(b[off(ptr)+index*16+12],)
def native_lock_floors(lock):
 # Floors on which the native map itself places this door lock (0x53da70 table). A door in a multi-level room
 # (603 Pump Room spans B1/B2) is drawn only there, not on every sub-floor (user 2026-10-23: phantom B2 key).
 return sorted({struct.unpack_from('<BB',b,off(va))[1] for va in range(0x53da70,0x53dae0,8) if b[off(va)]==lock})
for d0 in a:
 stage=int(d0['room'][4],16)-1;room=int(d0['room'][5:7],16);raw=bytes.fromhex(d0['raw'])
 nat=native_lock_floors(d0['key_id']&63) if d0['kind']=='door' else []
 for floor in nat or sub_floors(d0['pl'],stage,room,raw):
  d=dict(d0);index=call(0x4fb1c0,floor,room)
  if not 0<=floor<20:raise ValueError(d)
  table=0x53eb98 if d['pl'] else 0x53eaf8;ptr,cnt=struct.unpack_from('<IB',b,off(table)+floor*8)
  if index>=cnt:continue
  q=b[off(ptr)+index*16:off(ptr)+index*16+16];x,z,w,h=struct.unpack_from('<hhHH',raw,6)
  u.mem_write(0x989f28,struct.pack('<i',x+w//2));u.mem_write(0x989f30,struct.pack('<i',z+h//2));u.mem_write(0x691fb8,b'\0'*4);u.reg_write(UC_X86_REG_EBX,ptr+index*16);u.reg_write(UC_X86_REG_EBP,0);u.reg_write(UC_X86_REG_ESI,0x20001000);u.emu_start(0x4faa19,0x4faae3,count=200)
  px,py=(v+PROJ for v in struct.unpack('<hh',u.mem_read(0x20001008,4)));ax,ay=px,py # AOT centre: the door's own side
  x2,y2,seen2=other_side(d['pl'],floor,raw) if d['kind']=='door' else (0,0,255)
  lock=d['key_id'] if d['kind']=='event' else (d['key_id']&63 if d['kind']=='door' else struct.unpack_from('<H',raw,14)[0])
  assert lock<(256 if d['kind']=='event' else 64)
  meta=0
  for va in range(0x53da70,0x53dae0,8):
   k,f,flags,_,xx,yy=struct.unpack_from('<BBBBhh',b,off(va))
   if k==lock and f==floor and d['kind']=='door':px,py,meta=xx,yy,flags;break
  d.update(bank=4 if d['kind']=='event' else 255,floor=floor,room_index=index,x=px,y=py,seen=q[12],unlock=lock,scenario_mask=meta&192,
           x1=ax,y1=ay,x2=x2,y2=y2,seen2=seen2)
  if not any((r['pl'],r['floor'],r['x'],r['y'],r['item'])==(d['pl'],floor,px,py,d['item']) for r in result):result.append(d)
# The power-room boundary has an additional native marker on the other floor.
for pl in (0,1):
 d=next(x for x in result if x['pl']==pl and x['item']==95).copy()
 floor=13;room=4;idx=call(0x4fb1c0,floor,room);table=0x53eb98 if pl else 0x53eaf8;ptr,cnt=struct.unpack_from('<IB',b,off(table)+floor*8);assert idx<cnt
 q=b[off(ptr)+idx*16:off(ptr)+idx*16+16];d.update(floor=floor,room_index=idx,seen=q[12],x=176,y=123,x1=176,y1=123,x2=0,y2=0,seen2=255,other_side=True);result.append(d)
# B4 east corridor (60C) shutter to the B4 experiment room: opened by using the Lab Card Key (97) at a
# scripted reader, not a DoorAotSet lock. Native lock marker 21 sits at (203,172) on floor 16 (table 0x53daf0
# region); 60C function 4 opens the shutter and sets bank4 bit 96 (also read by 610 init).
for pl in (0,1):
 floor=16;room=0x0c;idx=call(0x4fb1c0,floor,room);table=0x53eb98 if pl else 0x53eaf8;ptr,cnt=struct.unpack_from('<IB',b,off(table)+floor*8);assert idx<cnt
 q=b[off(ptr)+idx*16:off(ptr)+idx*16+16]
 result.append(dict(pl=pl,room=f'ROOM60C{pl}.RDT',kind='event',item=97,key_id=96,floor=floor,room_index=idx,seen=q[12],x=203,y=172,unlock=96,bank=4,scenario_mask=0,note='lab card key shutter'))
# Item-locked doors: the door_aot is UNLOCKED, but while a bank4 (FG_COMMON) bit is clear the script replaces it
# with a "locked" event/message and puts an item-use SCE_FLAG_CHG beside it; using the item sets the bit
# (re-scd pl0/pl1 *.s). (room, stage, room id, door AOT x,z,w,h, icon item, bank4 bit, characters, note)
ITEM_DOORS=(
 ('211',1,0x11,(-23122,-13116,2600,1800),52,14,(0,1),'Armory: Red Card reader (211 main_06)'),
 ('21A',1,0x1a,(-6638,-3897,2270,2270),75,59,(0,1),'Kennel manhole: Manhole Opener (21A, V_USED_ITEM 75 sets bit 59)'),
 ('303',2,0x03,(-27206,-13094,3020,1030),62,58,(0,),'Plug Passage shutter: four chess plugs set bit 58 (303, Leon only)'),
)
for code,stage,room,(x,z,w,h),item,bit,pls,note in ITEM_DOORS:
 for pl in pls:
  floor=call(0x4faf80,stage,room);idx=call(0x4fb1c0,floor,room)
  table=0x53eb98 if pl else 0x53eaf8;ptr,cnt=struct.unpack_from('<IB',b,off(table)+floor*8);assert 0<=floor<20 and idx<cnt,(code,floor,idx)
  q=b[off(ptr)+idx*16:off(ptr)+idx*16+16]
  u.mem_write(0x989f28,struct.pack('<i',x+w//2));u.mem_write(0x989f30,struct.pack('<i',z+h//2));u.mem_write(0x691fb8,b'\0'*4);u.reg_write(UC_X86_REG_EBX,ptr+idx*16);u.reg_write(UC_X86_REG_EBP,0);u.reg_write(UC_X86_REG_ESI,0x20001000);u.emu_start(0x4faa19,0x4faae3,count=200)
  px,py=(v+PROJ for v in struct.unpack('<hh',u.mem_read(0x20001008,4)))
  result.append(dict(pl=pl,room=f'ROOM{code}{pl}.RDT',kind='event',item=item,key_id=bit,floor=floor,room_index=idx,seen=q[12],x=px,y=py,unlock=bit,bank=4,scenario_mask=0,note=note))
assert {d['item'] for d in result}=={31,48,63,83,88,89,90,91,92,93,94,95,97,98,99,52,62,75}
print([(d['pl'],d['room'],d['item'],d['floor'],d['x'],d['y'],d['unlock']) for d in result]);(R/'all-projected-locks.json').write_text(json.dumps(result,indent=2))
seen_rows=set();result=[d for d in result if not ((d['pl'],d['floor'],d['x'],d['y'],d['item'],d['unlock'],d['seen']) in seen_rows or seen_rows.add((d['pl'],d['floor'],d['x'],d['y'],d['item'],d['unlock'],d['seen'])))]
lines=['static const Door doors[]={']
for d in result:lines.append('{%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d},'%(d['pl'],d['floor'],d['x'],d['y'],d['seen'],d['unlock'],d['item'],d['scenario_mask'],d['bank'],
             d.get('x1',d['x']),d.get('y1',d['y']),d.get('x2',0),d.get('y2',0),d.get('seen2',255)))
lines.append('};');(R/'doors-all.h').write_text('\n'.join(lines))
