import os
from pathlib import Path
from collections import Counter
import struct,json,re
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EAX
R=Path(__file__).resolve().parent
GAME=Path(os.environ['RE2_GAME_EXE'])
DLL=R/'RE2.KeyMapNames-v6.4.asi'
def parse(blob,base):
 pe=struct.unpack_from('<I',blob,60)[0];o=pe+24;preferred=struct.unpack_from('<I',blob,o+28)[0];size=struct.unpack_from('<I',blob,o+56)[0];im=bytearray(size);n=struct.unpack_from('<H',blob,pe+6)[0];im[:struct.unpack_from('<I',blob,o+60)[0]]=blob[:struct.unpack_from('<I',blob,o+60)[0]]
 for i in range(n):
  h=o+struct.unpack_from('<H',blob,pe+20)[0]+i*40;vs,rv,rs,raw=struct.unpack_from('<IIII',blob,h+8);im[rv:rv+rs]=blob[raw:raw+rs]
 rv,z=struct.unpack_from('<II',blob,o+96+5*8);p=rv
 while z and p<rv+z:
  page,ln=struct.unpack_from('<II',im,p);assert ln>=8
  for j in range(p+8,p+ln,2):
   e=struct.unpack_from('<H',im,j)[0]
   if e>>12==3:
    t=page+(e&4095);v=struct.unpack_from('<I',im,t)[0];struct.pack_into('<I',im,t,(v+base-preferred)&0xffffffff)
  p+=ln
 return im,o,blob
u=Uc(UC_ARCH_X86,UC_MODE_32);gi,_,_=parse(GAME.read_bytes(),0x400000);u.mem_map(0x400000,(len(gi)+4095)//4096*4096);u.mem_write(0x400000,bytes(gi))
di,o,b=parse(DLL.read_bytes(),0x10000000);u.mem_map(0x10000000,(len(di)+4095)//4096*4096)
imp=struct.unpack_from('<I',b,o+96+8)[0];u.mem_map(0x25000000,0x1000);u.mem_write(0x25000000,bytes.fromhex('31c0c20400'))
p=imp
while struct.unpack_from('<I',di,p+12)[0]:
 lookup,_,_,name,iat=struct.unpack_from('<5I',di,p);lookup=lookup or iat;i=0
 while struct.unpack_from('<I',di,lookup+i*4)[0]:struct.pack_into('<I',di,iat+i*4,0x25000000);i+=1
 p+=20
u.mem_write(0x10000000,bytes(di));u.mem_map(0x20000000,0x10000);u.mem_map(0x21000000,0x40000)
rv=struct.unpack_from('<I',b,o+96)[0];n=struct.unpack_from('<I',di,rv+24)[0];func,names,ords=struct.unpack_from('<3I',di,rv+28);exports={}
for i in range(n):
 p=struct.unpack_from('<I',di,names+4*i)[0];end=di.index(0,p);name=di[p:end].decode();ord=struct.unpack_from('<H',di,ords+2*i)[0];exports[name]=0x10000000+struct.unpack_from('<I',di,func+ord*4)[0]
def call(name,*args):
 u.mem_write(0x20008000,struct.pack('<'+'I'*(len(args)+1),0x20000100,*args));u.reg_write(UC_X86_REG_ESP,0x20008000);u.emu_start(exports[name],0x20000100,count=1000000)
 assert u.reg_read(UC_X86_REG_ESP)==0x20008004
 return u.reg_read(UC_X86_REG_EAX)
# ---- harness end (test_upload-v6.py execs everything above) ----

# Header data (independent Python model of what must appear).
def rows(text,start):
 body=text.split(start,1)[1].split('};',1)[0]
 return [tuple(int(x,0) for x in m.split(',')) for m in re.findall(r'\{([-0-9x, ]+)\}',body)]
def pixels(path,name):
 body=(R/path).read_text().split(name,1)[1].split('={',1)[1].split(';',1)[0]
 return [int(v,0) for v in re.findall(r'0x[0-9a-fA-F]+|\d+',body)]
guards=rows((R/'items.h').read_text(),'map_item_guards[]')
items=rows((R/'items.h').read_text(),'map_items[]')
spade=[r for r in items if r[5]==89]
assert len(spade)==2 and all((r[2],r[3])==(149,125) for r in spade)
rooms=rows((R/'room_names.h').read_text(),'room_names[]')
room_labels=rows((R/'room_labels.h').read_text(),'room_labels[]')
item_labels=rows((R/'item_labels.h').read_text(),'item_labels[ITEM_LABEL_COUNT]')
icons=rows((R/'atlas.h').read_text(),'icons[]')
doors=rows((R/'doors-all.h').read_text(),'doors[]')
ov=(R/'overlay_data.h').read_text()
pick_guards=rows(ov,'room_pickup_guards[]');pickups=rows(ov,'room_pickups[]');markers=rows(ov,'map_markers[]')
doc_guards=rows(ov,'document_guards[]');documents=rows(ov,'map_documents[]')
interaction_guards=rows(ov,'interaction_guards[]');interactions=rows(ov,'map_interactions[]')
oicons=rows((R/'overlay_icons.h').read_text(),'overlay_icons[]')
ICON_TEX=int(re.search(r'OVERLAY_ICON_TEX (\d+)',(R/'overlay_icons.h').read_text())[1]);ICON_W=ICON_TEX//int(re.search(r'OVERLAY_ICON_SCALE (\d+)',(R/'overlay_icons.h').read_text())[1])
MAPS=set(range(200,206))
COMMON={20,21,22,24,25,26,27,29,30,35,38,39,40}
assert len(pickups)>300 and len(markers)>=50 and {m[3] for m in markers}=={9,10} and {i[0] for i in oicons}==({9,10,11,12,13}|{100+x for x in COMMON})
assert len(interactions)>1000 and {m[0] for m in interactions}=={0,1} and {m[3] for m in interactions}=={0,3,4,5,6,7,9,10,11,12,13,14}
assert all(m[6]+m[7]<=len(interaction_guards) and m[1]<20 and m[2]<256 for m in interactions) and all(g[0]<=34 and g[2] in (0,1) for g in interaction_guards)
assert all(p[3] in (8,34) and p[5]+p[6]<=len(pick_guards) for p in pickups) and all(g[0]<=34 for g in pick_guards)
doc_ids={106,107,108,109,111,112,113,114,115,116,117,118,119,120,121,122,123,125,126}
assert documents and {d[4] for d in documents}<=doc_ids and all(d[3] in (8,34) and d[8]+d[9]<=len(doc_guards) for d in documents)
ROOM_PAGES=int(re.search(r'ROOM_LABEL_PAGE_COUNT (\d+)',(R/'room_labels.h').read_text())[1])
ROOM_HELP_LABEL=int(re.search(r'ROOM_HELP_LABEL (\d+)',(R/'room_labels.h').read_text())[1])
ROOM_HELP_LABEL_COUNT=int(re.search(r'ROOM_HELP_LABEL_COUNT (\d+)',(R/'room_labels.h').read_text())[1])
ITEM_PAGES=int(re.search(r'ITEM_LABEL_PAGE_COUNT (\d+)',(R/'item_labels.h').read_text())[1])
assert len(room_labels)>96 and ROOM_HELP_LABEL+ROOM_HELP_LABEL_COUNT==len(room_labels) and ROOM_HELP_LABEL_COUNT==15 and len(item_labels)==48 and len(items)==356
assert {20,21,22,24,25,26,27,29,30,35,38,39,40} <= {i[0] for i in item_labels}
help_text=[label['text'] for label in json.loads((R/'room_names-provenance.json').read_text())['labels'][-ROOM_HELP_LABEL_COUNT:]]
label_data=json.loads((R/'room_names-provenance.json').read_text())['labels']
assert {label['font_px'] for label in label_data[-ROOM_HELP_LABEL_COUNT:]}=={16}
assert all(label['font_px']>16 for label in label_data[:ROOM_HELP_LABEL])
wrapped=[label for label in label_data[:ROOM_HELP_LABEL] if '\n' in label['text']]
assert len(wrapped)>0 and all(len(label['text'].splitlines())==2 and label['w']<=204 for label in wrapped)
assert help_text==['DISPLAY STATUS','0 ALL: ON','0 ALL: OFF','1 ROOMS: ON','1 ROOMS: OFF','2 LOCKS: ON','2 LOCKS: OFF','3 ITEMS: ON','3 ITEMS: OFF','4 DOCS: ON','4 DOCS: OFF','5 PUZZLES: ON','5 PUZZLES: OFF','9 LANGUAGE: KOREAN','9 LANGUAGE: ENGLISH']
assert all(r[5]<len(room_labels) for r in rooms) and all(i[8]+i[9]<=len(guards) for i in items)
assert all(i[6]<=34 and g[0]<=34 for i in items for g in guards[i[8]:i[8]+i[9]]) # bank_bit table bound
room_px=pixels('room_labels.h','room_label_pixels');item_px=pixels('item_labels.h','item_label_pixels')
pages={bytes(struct.pack('<65536H',*room_px[k*65536:(k+1)*65536])):('room',k) for k in range(ROOM_PAGES)}
pages.update({bytes(struct.pack('<65536H',*item_px[k*65536:(k+1)*65536])):('item',k) for k in range(ITEM_PAGES)})
pages[bytes(struct.pack('<65536H',*pixels('atlas.h','atlas_pixels')))]=('atlas',0)
pages[bytes(struct.pack('<65536H',*pixels('overlay_icons.h','overlay_icon_pixels')))]=('icon',0)
assert len(pages)>=ROOM_PAGES+ITEM_PAGES+2
# C-style assets retain hard, palette-limited pixels in every packed icon region.
key_pixels=pixels('atlas.h','atlas_pixels');overlay_pixels=pixels('overlay_icons.h','overlay_icon_pixels')
style_regions=[(key_pixels,i[1],i[2],i[3],i[4]) for i in icons]+[(overlay_pixels,i[1],i[2],ICON_TEX,ICON_TEX) for i in oicons if i[0]!=12]
assert len(style_regions)==32
for bitmap,x,y,w,h in style_regions:
 colors={bitmap[yy*256+xx] for yy in range(y,y+h) for xx in range(x,x+w)}-{0}
 assert 1<len(colors)<=17,(x,y,w,h,len(colors))
puzzle_sprite=next(i for i in oicons if i[0]==12)
pu,pv=puzzle_sprite[1:]
assert {overlay_pixels[y*256+x] for y in range(pv,pv+32) for x in range(pu,pu+32)}=={0,(238>>3)|((184>>3)<<5)|((48>>3)<<10)}
assert overlay_pixels[(pv+2)*256+pu+16] and not overlay_pixels[(pv+2)*256+pu+2]
KO=R/'korean-assets'
ko_room_labels=rows((KO/'room_labels.h').read_text(),'room_labels[]')
ko_item_labels=rows((KO/'item_labels.h').read_text(),'item_labels[ITEM_LABEL_COUNT]')
ko_rooms=rows((KO/'room_names.h').read_text(),'room_names[]')
ko_header=(KO/'room_labels.h').read_text()
ko_room_pages=int(re.search(r'ROOM_LABEL_PAGE_COUNT (\d+)',ko_header)[1])
ko_item_pages=int(re.search(r'ITEM_LABEL_PAGE_COUNT (\d+)',(KO/'item_labels.h').read_text())[1])
ko_help_start=int(re.search(r'ROOM_HELP_LABEL (\d+)',ko_header)[1])
ko_help_count=int(re.search(r'ROOM_HELP_LABEL_COUNT (\d+)',ko_header)[1])
ko_help_text=[label['text'] for label in json.loads((KO/'room_names-provenance.json').read_text())['labels'][-ko_help_count:]]
assert ko_help_count==15 and ko_help_text==['표시 상태','0 전체 켜짐','0 전체 꺼짐','1 방 이름 켜짐','1 방 이름 꺼짐','2 잠긴 문 켜짐','2 잠긴 문 꺼짐','3 아이템 켜짐','3 아이템 꺼짐','4 문서 켜짐','4 문서 꺼짐','5 퍼즐 켜짐','5 퍼즐 꺼짐','9 언어: 한국어','9 언어: 영어']
ko_room_px=pixels(KO/'room_labels.h','room_label_pixels');ko_item_px=pixels(KO/'item_labels.h','item_label_pixels')
for k in range(ko_room_pages):pages.setdefault(bytes(struct.pack('<65536H',*ko_room_px[k*65536:(k+1)*65536])),('room',k))
for k in range(ko_item_pages):pages.setdefault(bytes(struct.pack('<65536H',*ko_item_px[k*65536:(k+1)*65536])),('item',k))

BANKS={0:0x989e6c,1:0x989ed0,3:0x98eb2c,4:0x98eb4c,8:0x98ebb4,34:0x98ebd4,255:0x98ed2c}
def visible_help(state):
 stage=call('KeyMapTestInteractionStage')
 indices=[0,1 if state&1 else 2,3 if state&2 else 4,5 if state&4 else 6,7 if state&8 else 8,9 if state&16 else 10,11 if stage else 12,14 if call('KeyMapTestLanguage') else 13]
 return Counter({('help',)+room_labels[ROOM_HELP_LABEL+n]:1 for n in indices})
def model(pl,floor,flags,bits,seen,state=31,mode=0):
 def bb(bank,bit):return bit in bits.get(bank,()) or (bank==1 and bit<32 and flags&(0x80000000>>bit)!=0)
 out=Counter()
 if mode!=0 or floor>=20:return out
 stage=call('KeyMapTestInteractionStage')
 out.update(visible_help(state))
 if state&3==3:
  for m in markers:
   if m[0]==pl and m[1]==floor and m[2] in seen:
    i=[i for i in oicons if i[0]==m[3]][0];out[('icon',0,i[1],i[2],ICON_TEX,ICON_TEX)]+=1
 if state&5==5:
  for d in doors:
   dpl,dfl,x,y,s,unlock,key,mask,bank=d
   if dpl!=pl or dfl!=floor or s not in seen:continue
   if (key==93 and flags&0x40000000) or (key in (94,95,98,99) and not flags&0x40000000):continue
   if not flags&0x40000000:
    if mask&64:continue
   elif (pl and mask&64) or mask&128:continue
   if bb(bank,unlock):continue
   ic=[i for i in icons if i[0]==key]
   if ic:out[('atlas',0,)+ic[0][1:]]+=1
 if state&9==9:
  for it in items:
   ipl,ifl,x,y,s,item,bank,bit,gs,gc=it
   if ipl!=pl or ifl!=floor or s not in seen or bb(bank,bit):continue
   if any(bb(g[0],g[1])!=g[2] for g in guards[gs:gs+gc]):continue
   if item in COMMON or item in MAPS:
    i=[i for i in oicons if i[0]==(13 if item in MAPS else 100+item)][0]
    out[('icon',0,i[1],i[2],ICON_TEX,ICON_TEX)]+=1
   else:
    l=[l for l in item_labels if l[0]==item][0]
    out[('item',l[1],0,0,4,4)]+=1;out[('item',)+l[1:]]+=1
 if state&17==17:
  for d in documents:
   pl0,floor0,seen0,bank,item,x,y,bit,gs,gc=d
   if pl0!=pl or floor0!=floor or seen0 not in seen or bb(bank,bit):continue
   if any(bb(g[0],g[1])!=g[2] for g in doc_guards[gs:gs+gc]):continue
   i=[i for i in oicons if i[0]==11][0]
   out[('icon',0,i[1],i[2],ICON_TEX,ICON_TEX)]+=1
 if state&1 and stage:
  for m in interactions:
   if m[0]!=pl or m[1]!=floor or m[2] not in seen or m[3] not in (6,7):continue
   if any(bb(g[0],g[1])!=g[2] for g in interaction_guards[m[6]:m[6]+m[7]]):continue
   i=[i for i in oicons if i[0]==12][0]
   out[('icon',0,i[1],i[2],32,32)]+=1
 if state&3==3:
  for r in rooms:
   if r[0]==pl and r[1]==floor and r[2] in seen:
    out[('room',)+room_labels[r[5]]]+=1
    if r[6]|r[7]|r[8]|r[9]:out[('room',room_labels[r[5]][0],0,0,1,1)]+=1
 return out

# Native texture creation (0x405ec0) stubbed: hand out ids, remember which pixels each id carries.
u.mem_write(0x4021c0,bytes.fromhex('c20800')) # Marni queue insert; buffer pointer advance is the DLL's own.
u.mem_map(0x22000000,0x900000);u.mem_write(0x6805b8,struct.pack('<I',0x22000000));u.mem_write(0x228c8338,struct.pack('<I',1))
u.mem_write(0x405ec0,bytes.fromhex('c20800'));created={}
def create(u,a,n,_):
 desc=struct.unpack('<I',u.mem_read(u.reg_read(UC_X86_REG_ESP)+4,4))[0];ptr=struct.unpack('<I',u.mem_read(desc+4,4))[0]
 tid=len(created)+1;created[tid]=pages[bytes(u.mem_read(ptr,131072))];u.reg_write(UC_X86_REG_EAX,tid)
u.hook_add(UC_HOOK_CODE,create,begin=0x405ec0,end=0x405ec0)
call('KeyMapTestInit',0x400000)

def run(pl,floor,flags=None,bits={},seen=range(256),free=0x20000,mode=0):
 flags=(pl<<31) if flags is None else flags
 seen=set(seen);state=call('KeyMapTestState');puzzles=call('KeyMapTestInteractionStage')
 u.mem_write(0x989ed0,bytes(32));u.mem_write(0x98eb2c,bytes(0xc0));u.mem_write(0x98ed2c,bytes(32))
 u.mem_write(0x989ed0,struct.pack('<I',flags))
 def ibit(bank,bit):return bit in bits.get(bank,()) or (bank==1 and bit<32 and flags&(0x80000000>>bit)!=0)
 for bank,bs in bits.items():
  for n in bs:
   q=BANKS[bank]+(n//32)*4;v=struct.unpack('<I',u.mem_read(q,4))[0];u.mem_write(q,struct.pack('<I',v|(0x80000000>>(n%32))))
 sv=bytearray(32)
 for s in seen:struct.pack_into('<I',sv,(s//32)*4,struct.unpack_from('<I',sv,(s//32)*4)[0]|(0x80000000>>(s%32)))
 u.mem_write(0x98ec04,bytes(sv));u.mem_write(0x691f7a,bytes([floor]));u.mem_write(0x691f62,bytes([mode]));u.mem_write(0x691fb8,struct.pack('<hh',4,6))
 u.mem_write(0x21000000,b'\xa5'*0x30000);u.mem_write(0x524e1c,struct.pack('<II',0x21000000,0x21000000+free));call('KeyMapTestDraw')
 end=struct.unpack('<I',u.mem_read(0x524e1c,4))[0]
 assert 0x21000000<=end<=0x21000000+free and (end-0x21000000)%32==0
 assert bytes(u.mem_read(end,16))==b'\xa5'*16 # nothing written past the last queued quad
 got=Counter();rects=[];reserved=[];last_item_marker=None
 if state&3==3:
  reserved += [(m[4]+10-4,m[5]+12-4,8,8) for m in markers if m[0]==pl and m[1]==floor and m[2] in seen]
  if state&17==17:
   for d in documents:
    dp,df,ds,bank,item,x,y,bit,gs,gc=d
    if dp==pl and df==floor and ds in seen and not ibit(bank,bit) and all(ibit(g[0],g[1])==g[2] for g in doc_guards[gs:gs+gc]):reserved.append((x+6,y+8,8,8))
  if puzzles:
   for m in interactions:
    if m[0]==pl and m[1]==floor and m[2] in seen and m[3] in (6,7) and all(ibit(g[0],g[1])==g[2] for g in interaction_guards[m[6]:m[6]+m[7]]):reserved.append((m[4]+7,m[5]+9,6,6))
 for p in range(0x21000000,end,32):
  q=u.mem_read(p,32);cmd,tex=struct.unpack_from('<II',q,4);x,y,x1,y1=struct.unpack_from('<4h',q,16)
  assert cmd==0x24 and tex in created and 1<=x<=x1<=318 and 1<=y<=y1<=238 and (x<x1 or y<y1),(x,y,x1,y1)
  kind,page=created[tex];uu,vv,sw,sh=q[24],q[25],q[26]-q[24]+1,q[27]-q[25]+1;w,h=x1-x+1,y1-y+1
  if kind=='atlas':
   assert w==12
   assert any((uu,vv,sw,sh)==(i[1],i[2],i[3],i[4]) and h==max(3,(i[4]*12+i[3]//2)//i[3]) for i in icons),(uu,vv,sw,sh,w,h)
   rects.append((x,y,w,h));reserved.append((x,y,w,h))
  elif kind=='icon':
   icon_kind=next(i[0] for i in oicons if (i[1],i[2])==(uu,vv))
   if icon_kind>=120 or icon_kind==13:
    item=icon_kind-100 if icon_kind!=13 else 200
    assert (item in COMMON or item in MAPS) and (w,h)==((ICON_W*90+50)//100,)*2
    assert any(i[0]==pl and i[1]==floor and (i[5]==item or icon_kind==13 and i[5] in MAPS) and i[2]+10-w//2==x and i[3]+12-h//2==y for i in items),(item,x,y)
    rects.append((x,y,w,h));reserved.append((x,y,w,h))
   elif icon_kind==11:
    assert (w,h)==(ICON_W,ICON_W);rects.append((x,y,w,h));reserved.append((x,y,w,h))
    assert any(min(max(d[5]+6+4-w//2,1),318-w)==x and min(max(d[6]+6+6-h//2,1),238-h)==y for d in documents if d[0]==pl and d[1]==floor),(x,y)
   elif icon_kind==12:
    assert (w,h)==(6,6) and puzzles and state&1
    assert any(m[0]==pl and m[1]==floor and m[2] in seen and m[3] in (6,7) and
       min(max(m[4]+6+4-3,1),312)==x and min(max(m[5]+6+6-3,1),232)==y and
       all(ibit(g[0],g[1])==g[2] for g in interaction_guards[m[6]:m[6]+m[7]]) for m in interactions),(x,y)
    rects.append((x,y,w,h));reserved.append((x,y,w,h))
   else:
    assert (w,h)==(ICON_W,ICON_W);rects.append((x,y,w,h));reserved.append((x,y,w,h))
    # Exactly centred on projected point + 6 (arrow-sprite centre), pan (4,6), clamped only at edges.
    assert any(min(max(m[4]+6+4-w//2,1),318-w)==x and min(max(m[5]+6+6-h//2,1),238-h)==y for m in markers if m[0]==pl and m[1]==floor),(x,y)
  elif (uu,vv,sw,sh)==(0,0,4,4):
   assert kind=='item' and (w,h)==(4,4)
   is_item=any(min(max(i[2]+6+4-2,1),314)==x and min(max(i[3]+6+6-2,1),234)==y for i in items if i[0]==pl and i[1]==floor)
   assert is_item,(x,y)
   last_item_marker=(x,y)
   reserved.append((x,y,w,h))
  elif kind=='room' and (uu,vv,sw,sh)==(0,0,1,1):
   assert w==1 or h==1;assert any(min(r[6],r[8])+4==x and min(r[7],r[9])+6==y and abs(r[8]-r[6])+1==w and abs(r[9]-r[7])+1==h for r in rooms if r[6]|r[7]|r[8]|r[9]),(x,y,w,h)
   reserved.append((x,y,w,h))
  elif kind=='room':
   assert (w,h)==((sw+2)//4,(sh+2)//4),(w,h,sw,sh);rects.append((x,y,w,h))
   help_rows=room_labels[ROOM_HELP_LABEL:ROOM_HELP_LABEL+ROOM_HELP_LABEL_COUNT]
   if (page,uu,vv,sw,sh) in help_rows:
    n=help_rows.index((page,uu,vv,sw,sh))
    state=call('KeyMapTestState');stage=call('KeyMapTestInteractionStage');language=call('KeyMapTestLanguage')
    selected=[0,1 if state&1 else 2,3 if state&2 else 4,5 if state&4 else 6,7 if state&8 else 8,9 if state&16 else 10,11 if stage else 12,14 if language else 13]
    assert n in selected,(n,selected)
    row=selected.index(n)
    chosen=[help_rows[index] for index in selected]
    heights=[(label[4]+2)//4 for label in chosen]
    widths=[(label[3]+2)//4 for label in chosen]
    col,slot=divmod(row,4)
    col_start=col*4
    expected_x=8+(max(widths[:4])+8 if col else 0)
    expected_y=238-(sum(heights[col_start:col_start+4])+2)+sum(heights[col_start:col_start+slot])
    assert (x,y)==(expected_x,expected_y),(x,y,w,h,expected_x,expected_y)
    got[('help',page,uu,vv,sw,sh)]+=1
    reserved.append((x,y,w,h))
    continue
   matches=[r for r in rooms if r[0]==pl and r[1]==floor and room_labels[r[5]]==(page,uu,vv,sw,sh)]
   assert matches,(page,uu,vv,sw,sh)
   # Same least-overlap placement rule for Korean and English room names.
   def room_position(r):
    candidates=[]
    for ox,oy in ((0,0),(0,9),(0,-9),(0,18),(0,-18),(18,0),(-18,0),(18,12),(-18,12)):
     cx=min(max(r[3]+4-w//2+ox,1),318-w);cy=min(max(r[4]+6-h//2+oy,1),238-h);score=0
     for rx,ry,rw,rh in reserved:
      iw=min(cx+w,rx+rw)-max(cx,rx);ih=min(cy+h,ry+rh)-max(cy,ry)
      if iw>0 and ih>0:score+=iw*ih
     candidates.append((score,cx,cy))
    return min(candidates,key=lambda q:q[0])[1:]
   assert any(room_position(r)==(x,y) for r in matches),((x,y),matches)
   reserved.append((x,y,w,h))
  elif kind=='item':
   assert (w,h)==((sw+2)//4,(sh+2)//4),(w,h,sw,sh)
   assert last_item_marker is not None, 'item label must follow its pickup dot'
   px,py=last_item_marker[0]+2,last_item_marker[1]+2
   offsets=((0,0),(0,9),(0,-9),(0,18),(0,-18),(18,0),(-18,0),(18,12),(-18,12))
   candidates=[]
   for ox,oy in offsets:
    cx=min(max(px-w//2+ox,1),318-w);cy=min(max(py-h//2+oy,1),238-h);score=0
    for rx,ry,rw,rh in reserved:
     iw=min(cx+w,rx+rw)-max(cx,rx);ih=min(cy+h,ry+rh)-max(cy,ry)
     if iw>0 and ih>0:score+=iw*ih
    candidates.append((score,cx,cy))
   expected_x,expected_y=min(candidates,key=lambda q:q[0])[1:]
   assert (x,y)==(expected_x,expected_y),((x,y),(expected_x,expected_y))
   last_item_marker=None;rects.append((x,y,w,h));reserved.append((x,y,w,h))
  else:assert (w,h)==((sw+1)//2,(sh+1)//2),(w,h,sw,sh);rects.append((x,y,w,h))
  got[(kind,page,uu,vv,sw,sh)]+=1
 overlaps=sum(1 for i,a in enumerate(rects) for c in rects[i+1:] if a[0]<c[0]+c[2] and c[0]<a[0]+a[2] and a[1]<c[1]+c[3] and c[1]<a[1]+a[3])
 return got,overlaps

def check(pl,floor,flags=None,bits={},seen=range(256)):
 f=(pl<<31) if flags is None else flags
 got,ov=run(pl,floor,flags,bits,seen);want=model(pl,floor,f,bits,set(seen),call('KeyMapTestState'))
 assert got==want,(pl,floor,hex(f),bits,got-want,want-got)
 return got,ov

counts={};overlaps={};pickup_hidden=0
for pl in (0,1):
 for scen,extra in (('A',0),('B',0x40000000),('A_flag6',0x02000000),('B_flag6',0x42000000)):
  for floor in range(20):
   flags=(pl<<31)|extra;got,ov=check(pl,floor,flags)
   counts[f'{"LC"[pl]}{scen}F{floor}']={k:sum(v for kk,v in got.items() if kk[0]==k) for k in ('atlas','item','room')}
   if ov:overlaps[f'{"LC"[pl]}{scen}F{floor}']=ov
   # Every visible pickup disappears once its own pickup bank bit is set.
   for it in items:
    if it[0]!=pl or it[1]!=floor:continue
    base=model(pl,floor,flags,{},set(range(256)))
    if it[5] in COMMON or it[5] in MAPS:
     icon=next(i for i in oicons if i[0]==(13 if it[5] in MAPS else 100+it[5]));key=('icon',0,icon[1],icon[2],ICON_TEX,ICON_TEX)
    else:
     l=[l for l in item_labels if l[0]==it[5]][0];key=('item',)+l[1:]
    after,_=check(pl,floor,flags,{it[6]:{it[7]}})
    if all(((g[0]==1 and g[1]<32 and flags&(0x80000000>>g[1])!=0))==g[2] for g in guards[it[8]:it[8]+it[9]]):
     assert after[key]<base[key],it;pickup_hidden+=1
# Wall maps retain physical-pickup hiding even when map information is already
# unlocked or a companion is active; synthetic IDs never enter game inventory.
map_rows=[it for it in items if 200<=it[5]<=205]
assert len(map_rows)==14 and {it[5] for it in map_rows}==set(range(200,206))
assert all(it[9]==0 for it in map_rows)
map_flags={200:(8,83),201:(4,122),202:(8,137),203:(8,162),204:(34,25),205:(4,165)}
assert all(it[6:8]==map_flags[it[5]] for it in map_rows)
treatment_map=next(('icon',0,i[1],i[2],ICON_TEX,ICON_TEX) for i in oicons if i[0]==13)
assert any(it[:8]==(0,6,183,61,64,202,8,137) for it in map_rows)
for flags in (0x40000000,0x42000000,0x50000000):
 got,_=check(0,6,flags)
 assert struct.unpack('<I',u.mem_read(0x98ec1c,4))[0]==0xffffffff # bank33 map-info bits already set
 assert got[treatment_map]==1
 assert check(0,6,flags,bits={8:{137}})[0][treatment_map]==0
 assert check(0,6,flags,seen=[])[0][treatment_map]==0
call('KeyMapTestToggle',0,0);call('KeyMapTestToggle',0,8)
assert check(0,6,0x40000000)[0][treatment_map]==0
call('KeyMapTestToggle',0,0);call('KeyMapTestToggle',0,8)
assert check(0,6,0x40000000)[0][treatment_map]==1

# Weapon Box Key is found at the cable-car platform in all four scenarios;
# the separate Power Room Key at Laboratory B5 is scenario B only.
weapon_label=('item',)+[l for l in item_labels if l[0]==63][0][1:]
weapon_lock=('atlas',0)+[i for i in icons if i[0]==63][0][1:]
for pl,scenario in ((0,0),(0,0x40000000),(1,0),(1,0x40000000)):
 got,_=check(pl,9,(pl<<31)|scenario,seen=[90]);assert got[weapon_label]==1,(pl,scenario,got.get(weapon_label,0))
 got,_=check(pl,17,(pl<<31)|scenario,seen=[120]);assert got[weapon_lock]==1,(pl,scenario,got.get(weapon_lock,0))
 got,_=check(pl,17,(pl<<31)|scenario,bits={4:{159}},seen=[120]);assert got[weapon_lock]==0,(pl,scenario,got.get(weapon_lock,0))
# Leon's Rook Plug in the 1F Interrogation Room has an exact native projection;
# it is present in both scenarios and disappears after pickup.
rook_rows=[it for it in items if it[0]==0 and it[1]==2 and it[2:5]==(176,90,44) and it[5]==60]
assert len(rook_rows)==1 and rook_rows[0][7]==56 and rook_rows[0][6]==8 and rook_rows[0][9]==0
rook_label=('item',)+[l for l in item_labels if l[0]==60][0][1:]
for scenario in (0,0x40000000):
 got,_=check(0,2,scenario,seen=[44]);assert got[rook_label]==1,('Rook Plug',scenario,got.get(rook_label,0))
 got,_=check(0,2,scenario,bits={8:{56}},seen=[44]);assert got.get(rook_label,0)==0,('Rook Plug pickup',scenario)
assert all(it[0]!=1 or it[5]!=60 for it in items)
# Claire A/B's Eagle Stone replaces the Leon-only Rook Plug at the same shelf.
eagle_rows=[it for it in items if it[0]==1 and it[1]==2 and it[2:5]==(176,90,44) and it[5]==58]
assert len(eagle_rows)==1 and eagle_rows[0][7]==56 and eagle_rows[0][6]==8 and eagle_rows[0][9]==0
eagle_label=('item',)+[l for l in item_labels if l[0]==58][0][1:]
for scenario in (0,0x40000000):
 got,_=check(1,2,(1<<31)|scenario,seen=[44]);assert got[eagle_label]==1,('Eagle Stone',scenario)
 got,_=check(1,2,(1<<31)|scenario,bits={8:{56}},seen=[44]);assert got.get(eagle_label,0)==0,('Eagle Stone pickup',scenario)
assert all(it[0]!=0 or it[5]!=58 for it in items)
# Leon has four Small-Key-locked doors; all are available in A and B and disappear after unlocking.
small_locks=[d for d in doors if d[0]==0 and d[6]==31]
assert len(small_locks)==4 and not [d for d in doors if d[0]==1 and d[6]==31]
small_icon=('atlas',0)+[i for i in icons if i[0]==31][0][1:]
for d in small_locks:
 for scenario in (0,0x40000000):
  got,_=check(0,d[1],scenario,seen=[d[4]])
  assert got[small_icon]>=1,(d,scenario,got.get(small_icon,0))
  got,_=check(0,d[1],scenario,bits={255:{d[5]}},seen=[d[4]])
  assert got[small_icon]<1,(d,scenario,got.get(small_icon,0))
# Documents have their own key and pickup bits; toggling them cannot toggle core items.
doc_icon=next(('icon',0,i[1],i[2],ICON_TEX,ICON_TEX) for i in oicons if i[0]==11)
doc_case=next((d for d in documents for flags in ((d[0]<<31),(d[0]<<31)|0x40000000)
               if model(d[0],d[1],flags,{}, {d[2]}).get(doc_icon,0)),None)
assert doc_case
for d in documents:
 flags=d[0]<<31;gate_bits={}
 for bank,bit,want in doc_guards[d[8]:d[8]+d[9]]:
  if bank==1 and bit<32:
   if want:flags|=0x80000000>>bit
  elif want:gate_bits.setdefault(bank,set()).add(bit)
 got,_=check(d[0],d[1],flags,gate_bits,seen=[d[2]])
 if got[doc_icon]:
  hidden,_=check(d[0],d[1],flags,{**gate_bits,d[3]:gate_bits.get(d[3],set())|{d[7]}},seen=[d[2]])
  assert hidden[doc_icon]<got[doc_icon],d
up_key_lock=('atlas',0)+[i for i in icons if i[0]==94][0][1:]
for pl,scenario,expected in ((0,0,0),(0,0x40000000,1),(1,0,0),(1,0x40000000,1)):
 got,_=check(pl,10,(pl<<31)|scenario,seen=[92]);assert got[up_key_lock]==expected,(pl,scenario,got.get(up_key_lock,0))
for item,floor,seen,expected in ((93,10,93,{(0,0):1,(0,0x40000000):0,(1,0):1,(1,0x40000000):0}),
                                (95,13,103,{(0,0):0,(0,0x40000000):1,(1,0):0,(1,0x40000000):1}),
                                (99,18,123,{(0,0):0,(0,0x40000000):1,(1,0):0,(1,0x40000000):1}),
                                (98,16,105,{(0,0):0,(0,0x40000000):1,(1,0):0,(1,0x40000000):0})):
 lock=('atlas',0)+[i for i in icons if i[0]==item][0][1:]
 for pl,scenario in ((0,0),(0,0x40000000),(1,0),(1,0x40000000)):
  got,_=check(pl,floor,(pl<<31)|scenario,seen=[seen]);assert got[lock]==expected[pl,scenario],(item,pl,scenario,got.get(lock,0))
power_label=('item',)+[l for l in item_labels if l[0]==95][0][1:]
for pl,scenario,expected in ((0,0,0),(0,0x40000000,1),(1,0,0),(1,0x40000000,1)):
 got,_=check(pl,17,(pl<<31)|scenario,seen=[120]);assert got[power_label]==expected,(pl,scenario,got.get(power_label,0))
# The C. Panel Key (U) and Platform Key are B-scenario-only pickups; the third
# Small Key is Leon B only. These assertions guard the location data as well as
# the renderer's scenario filtering.
for item,floor,seen,expected in ((94,11,96,{(0,0):0,(0,0x40000000):1,(1,0):0,(1,0x40000000):1}),
                                (99,18,127,{(0,0):0,(0,0x40000000):1,(1,0):0,(1,0x40000000):1})):
 label=('item',)+[l for l in item_labels if l[0]==item][0][1:]
 for pl,scenario in ((0,0),(0,0x40000000),(1,0),(1,0x40000000)):
  got,_=check(pl,floor,(pl<<31)|scenario,seen=[seen]);assert got[label]==expected[pl,scenario],(item,pl,scenario,got.get(label,0))
small_key=('item',)+[l for l in item_labels if l[0]==31][0][1:]
for pl,scenario,expected in ((0,0,0),(0,0x40000000,1),(1,0,0),(1,0x40000000,0)):
 got,_=check(pl,8,(pl<<31)|scenario,seen=[77]);assert got[small_key]==expected,(31,pl,scenario,got.get(small_key,0))
master_key=('item',)+[l for l in item_labels if l[0]==98][0][1:]
for pl,scenario,expected in ((0,0,0),(0,0x40000000,1),(1,0,0),(1,0x40000000,1)):
 got,_=check(pl,13 if pl==0 else 16,(pl<<31)|scenario,seen=[103 if pl==0 else 107],bits={4:{92}} if pl==1 and scenario else {});assert got[master_key]==expected,(98,pl,scenario,got.get(master_key,0))
wolf_medal=('item',)+[l for l in item_labels if l[0]==73][0][1:]
for pl,scenario,expected in ((0,0,1),(0,0x40000000,1),(1,0,0),(1,0x40000000,1)):
 got,_=check(pl,8,(pl<<31)|scenario,seen=[77]);assert got[wolf_medal]==expected,(73,pl,scenario,got.get(wolf_medal,0))
# Room labels/items only for visited rooms.
assert run(0,2,seen=())[0]==visible_help(call('KeyMapTestState'))
only200=[r for r in rooms if r[0]==0 and r[1]==2][0][2]
got,_=check(0,2,seen=[only200]);assert sum(v for k,v in got.items() if k[0]=='room')==1
# Spot checks from items-report.md (would fail with the raw-mask bank_bit bug: value=1 guards).
guard1=[it for it in items if any(g[2]==1 for g in guards[it[8]:it[8]+it[9]])]
assert guard1
seen_guard1=sum(1 for it in guard1 for extra in (0,0x40000000,0x02000000,0x42000000) if model(it[0],it[1],(it[0]<<31)|extra,{},set(range(256)))[('item',)+[l for l in item_labels if l[0]==it[5]][0][1:]])
assert seen_guard1>0 # these rows are covered by the differential runs above
assert counts['LAF2']['item']>0 and counts['LAF2']['room']>0 and counts['CBF3']['item']>0
# Other characters/floors never leak: Leon data never drawn for Claire.
assert all(model(1,f,0x80000000,{},set(range(256)))==run(1,f)[0] for f in range(20))
# Exit modes and floor>=20 draw nothing.
assert all(sum(run(0,2,mode=m)[0].values())==0 for m in (1,2,3)) and sum(run(0,20)[0].values())==0
# Buffer safety: 8192-byte headroom kept; exactly floor((free-8192)/32) quads when tight.
full=sum(run(0,2)[0].values());assert full>=3
assert sum(run(0,2,free=8192+32*3)[0].values())==3 and sum(run(0,2,free=8192+31)[0].values())==0 and sum(run(0,2,free=1000)[0].values())==0
# Texture cache: one create per page per device; device change re-creates.
before=len(created)
for f in range(20):run(0,f);run(1,f)
assert len(created)==before
u.mem_write(0x228c8338,struct.pack('<I',2));run(0,2);assert len(created)>before
assert {('atlas',0),('icon',0)}|{('room',k) for k in range(ROOM_PAGES)} <= set(created.values())
# ---- v6.2 room tint: run the REAL native room loop 0x4fa990 (unicorn) with and without the fill hook ----
EXE=GAME.read_bytes()
def exe_va(va,n):
 pe=struct.unpack_from('<I',EXE,60)[0]
 for i in range(struct.unpack_from('<H',EXE,pe+6)[0]):
  o=pe+24+struct.unpack_from('<H',EXE,pe+20)[0]+40*i;_,rv,rs,raw=struct.unpack_from('<IIII',EXE,o+8)
  if 0x400000+rv<=va<0x400000+rv+rs:return EXE[raw+va-0x400000-rv:raw+va-0x400000-rv+n]
# Static: the DllMain-validated call-site bytes really are in the shipped EXE.
site=exe_va(0x4faf38,15);assert site[:8]==bytes.fromhex('6a006a0a6a2056e8') and 0x4faf44+struct.unpack_from('<i',site,8)[0]==0x440280 and site[12:]==bytes.fromhex('83c410')
for s0 in (0x4fa552,0x4fb60b,0x4fb7e7):b5=exe_va(s0,5);assert b5[0]==0xe8 and s0+5+struct.unpack_from('<i',b5,1)[0]==0x4fa990
ORIG=bytes(u.mem_read(0x4faf3f,5));STUB=call('KeyMapTestFillHook')
for slot in range(41):u.mem_write(0x67c7d8+slot*12,struct.pack('<III',0x7000+slot,4,0)) # texture handle, CLUT rows, status
u.mem_write(0x4021c0,bytes.fromhex('c20800'));u.mem_write(0x402240,bytes.fromhex('c20800'))
def pending(pl,floor,seen,bits,flags):
 bb=lambda bank,bit:bit in bits.get(bank,()) or (bank==1 and bit<32 and flags&(0x80000000>>bit)!=0)
 return any(p[0]==pl and p[1]==floor and p[2]==seen and not bb(p[3],p[4]) and all(bb(g[0],g[1])==g[2] for g in pick_guards[p[5]:p[5]+p[6]]) for p in pickups)
def table(pl,floor):
 ptr,cnt=struct.unpack('<IB',exe_va((0x53eb98 if pl else 0x53eaf8)+floor*8,5))
 return [exe_va(ptr+i*16,16) for i in range(cnt)]
def native_loop(pl,floor,hooked,flags=None,bits={},seen=range(160),cur=None,floormap=0,bank32=(),free=0x20000):
 flags=(pl<<31) if flags is None else flags
 u.mem_write(0x4faf3f,b'\xe8'+struct.pack('<i',STUB-0x4faf44) if hooked else ORIG)
 u.ctl_remove_cache(0x4faf00,0x4faf80) # unicorn caches translated blocks; drop them after patching code
 for a,n in ((0x989ed0,32),(0x98eb2c,0xc0),(0x98ec00,0x40),(0x98ed2c,32),(0x989e6c,4)):u.mem_write(a,bytes(n))
 u.mem_write(0x989ed0,struct.pack('<I',flags))
 def setbit(base,n):q=base+(n//32)*4;v=struct.unpack('<I',u.mem_read(q,4))[0];u.mem_write(q,struct.pack('<I',v|(0x80000000>>(n%32))))
 for bank,bs in bits.items():
  for n in bs:setbit(BANKS[bank],n)
 for s in seen:setbit(0x98ec04,s)
 for b in bank32:setbit(0x98ec18,b)
 if floormap:u.mem_write(0x98ec1c,b'\xff'*4)
 stage,room=cur if cur else (6,0x3f) # (6,0x3f): no table match -> no current room
 u.mem_write(0x98eb14,struct.pack('<hh',stage,room));u.mem_write(0x691f7a,bytes([floor]));u.mem_write(0x9888d8,b'\0')
 u.mem_write(0x691fb8,struct.pack('<hh',0,0));u.mem_write(0x21000000,b'\xa5'*0x30000);u.mem_write(0x524e1c,struct.pack('<II',0x21000000,0x21000000+free))
 u.reg_write(UC_X86_REG_ESP,0x20008000);u.emu_start(0x4fa990,0x4faf56,count=2000000)
 end=struct.unpack('<I',u.mem_read(0x524e1c,4))[0];assert bytes(u.mem_read(end,16))==b'\xa5'*16
 return [bytes(u.mem_read(p,32)) for p in range(0x21000000,end,32)]
FILL=0x7000+0x20
# Seen bank 0x98ec04 is 160 bits: bank32 (0x98ec18) / bank33 (0x98ec1c) follow it (table 0x53b218).
assert all(e[12]<160 for pl in (0,1) for f in range(20) for e in table(pl,f))
def split(packets):
 tint=[p for p in packets if struct.unpack_from('<I',p,8)[0]==FILL and struct.unpack_from('<I',p,4)[0]&0x200000]
 return [p for p in packets if p not in tint],tint
tint_counts={};tint_checks=0
for pl in (0,1):
 for floor in range(20):
  ents=table(pl,floor)
  if not ents:continue
  for flags in ((pl<<31),(pl<<31)|0x40000000):
   for floormap,b32 in ((0,()),(1,()),(0,tuple(range(32)))):
    plain=native_loop(pl,floor,False,flags,floormap=floormap,bank32=b32);hooked=native_loop(pl,floor,True,flags,floormap=floormap,bank32=b32)
    base,tint=split(hooked);assert base==plain # native packets byte-identical; only extra tint packets
    want=Counter((e[4]|e[5]<<8,e[6]|e[7]<<8) for i,e in enumerate(ents) if not(floor==2 and i==14) and pending(pl,floor,e[12],{},flags))
    got=Counter(struct.unpack_from("<hh",p,16) for p in tint);assert got==want,(pl,floor,want-got,got-want,[q.hex() for q in hooked if struct.unpack_from("<I",q,8)[0]==FILL][:3],hex(struct.unpack("<I",u.mem_read(0x524e20,4))[0]))
    for p in tint:assert struct.unpack_from('<I',p,4)[0]==0x200025 and struct.unpack_from('<I',p,0x1c)[0]==0x606060 and struct.unpack_from('<I',p,12)[0]&1
    tint_checks+=1;tint_counts[f'{"LC"[pl]}F{floor}{"AB"[flags>>30&1]}']=len(tint)
# Unvisited rooms: native draws (with floor map) stay identical and no tint at all.
for pl in (0,1):
 for floor in (2,3):
  for fm in (0,1):
   a=native_loop(pl,floor,False,seen=(),floormap=fm);b=native_loop(pl,floor,True,seen=(),floormap=fm);assert a==b and not split(b)[1]
# Current room stays native red (CLUT row 1, 50% blend) and never gets the pink pass; rows with bank32 (+2) also keep row parity.
cur_room=[(i,e) for i,e in enumerate(table(0,2)) if i!=14 and pending(0,2,e[12],{},0)][0]
stage_room=[(1,int(n[5:7],16)) for n in ['ROOM2000']][0]
for stage,room in ((1,r) for r in range(0x40)):
 # find a (stage,room) the native map resolves to this floor/index
 if u.mem_write(0x20008000,struct.pack('<III',0x20000100,stage,room)) or True:
  u.reg_write(UC_X86_REG_ESP,0x20008000);u.emu_start(0x4faf80,0x20000100,count=500);fl=u.reg_read(UC_X86_REG_EAX)
  u.reg_write(UC_X86_REG_ESP,0x20008000);u.mem_write(0x20008000,struct.pack('<III',0x20000100,fl,room));u.emu_start(0x4fb1c0,0x20000100,count=500)
  if fl==2 and u.reg_read(UC_X86_REG_EAX)==cur_room[0]:break
else:raise AssertionError('no current-room id found')
for b32 in ((),tuple(range(32))):
 plain=native_loop(0,2,False,cur=(stage,room),bank32=b32);hooked=native_loop(0,2,True,cur=(stage,room),bank32=b32)
 base,tint=split(hooked);assert base==plain
 pos=(cur_room[1][4]|cur_room[1][5]<<8,cur_room[1][6]|cur_room[1][7]<<8)
 fills=[p for p in base if struct.unpack_from('<I',p,8)[0]==FILL and struct.unpack_from('<hh',p,16)==pos]
 assert fills and all(struct.unpack_from('<I',p,12)[0]&1 for p in fills) # native red row
 assert pos not in [struct.unpack_from('<hh',p,16) for p in tint]
 assert all(struct.unpack_from('<I',p,12)[0]==(3 if b32 else 1) for p in tint),(b32,[(struct.unpack_from('<I',p,12)[0],struct.unpack_from('<hh',p,16)) for p in tint],bytes(u.mem_read(0x98ec00,0x40)).hex()) # pink pass = row|1 of the room's own row
# Blue when cleared: set every pickup bit of floor-2 rows -> no tint.
allbits={8:{p[4] for p in pickups if p[3]==8},34:{p[4] for p in pickups if p[3]==34}}
assert not split(native_loop(0,2,True,bits=allbits))[1] and not split(native_loop(1,3,True,bits=allbits))[1]
# One room: pink until its last pending pickup bit is set, then native blue only.
room=[e for i,e in enumerate(table(0,2)) if i!=14 and pending(0,2,e[12],{},0)][0];rp=[p for p in pickups if p[0]==0 and p[1]==2 and p[2]==room[12]]
assert len(split(native_loop(0,2,True,seen=[room[12]]))[1])==1
assert not split(native_loop(0,2,True,seen=[room[12]],bits={p[3]:{x[4] for x in rp if x[3]==p[3]} for p in rp}))[1]
# Buffer safety: with < 32+8192 free after the native fill, the pink pass is skipped and natives are untouched.
for free in (8192+31,8192+32*6,8192+32*30,1000):
 a=native_loop(0,2,False,free=free);b=native_loop(0,2,True,free=free);base,tint=split(b);assert base==a
 assert all(free-32*b.index(p)>=32+8192 for p in tint) # pink pass only while label headroom remains
 if free<8192+32:assert not tint
assert split(native_loop(0,2,True,free=8192+32*30))[1] # and it does draw when there is room
# Visited save markers and documents have separate icon UVs; neither leaks into unvisited rooms.
g,_=check(0,2)
save_uv={(0,i[1],i[2],ICON_TEX,ICON_TEX) for i in oicons if i[0] in (9,10)}
doc_uv={(0,i[1],i[2],ICON_TEX,ICON_TEX) for i in oicons if i[0]==11}
assert sum(v for k,v in g.items() if k[0]=='icon' and k[1:] in save_uv)==sum(1 for m in markers if m[0]==0 and m[1]==2)>=3
doc_case_flags=(doc_case[0]<<31)
assert check(doc_case[0],doc_case[1],doc_case_flags,seen=[doc_case[2]])[0][doc_icon]>0
unseen={s for s in range(256) if s not in {m[2] for m in markers}|{d[2] for d in documents}|{m[2] for m in interactions}|{i[4] for i in items}}
assert not [k for k in run(0,2,seen=unseen)[0] if k[0]=='icon']
def toggle(key,mode=0):
 call('KeyMapTestToggle',mode,0);call('KeyMapTestToggle',mode,key)
 return call('KeyMapTestState')
assert call('KeyMapTestState')==31
assert call('KeyMapTestInteractionStage')==1
assert toggle(64,1)==31 and call('KeyMapTestInteractionStage')==1 # puzzle switch is restricted to the interactive map
puzzle_uv={(0,i[1],i[2],32,32) for i in oicons if i[0]==12}
puzzles_on=run(0,3,seen=range(256))[0]
assert sum(v for k,v in puzzles_on.items() if k[0]=='icon' and k[1:] in puzzle_uv)>0
assert toggle(64)==31 and call('KeyMapTestInteractionStage')==0
puzzles_off=run(0,3,seen=range(256))[0]
assert not any(k[0]=='icon' and k[1:] in puzzle_uv for k in puzzles_off)
assert toggle(64)==31 and call('KeyMapTestInteractionStage')==1
assert toggle(2,1)==31 # hotkeys outside the interactive map are ignored
assert toggle(2)==29 and toggle(4)==25 and toggle(8)==17 and toggle(16)==1 # room, lock, item and document switches are independent
g,_=check(0,2);assert g==visible_help(call('KeyMapTestState'))+Counter({k:v for k,v in g.items() if k[0]=='icon' and k[1:] in puzzle_uv}) and not any(k[0] in ('room','atlas','item') for k in g)
assert toggle(1)==0 # master off hides every overlay except the help line
g,_=check(0,2);assert g==visible_help(call('KeyMapTestState'))
assert toggle(2)==2 and toggle(1)==3 # category state is retained while master is off
g,_=check(0,2);assert sum(v for k,v in g.items() if k[0]=='room')>0 and sum(v for k,v in g.items() if k[0]=='icon')>0 and not any(k[0]=='atlas' for k in g) and all(k==('item',0,0,0,4,4) for k in g if k[0]=='item')
assert toggle(2)==1 # hiding room names also hides typewriter/item-box icons
g,_=check(0,2);assert not any(k[0]=='room' for k in g) and all(k[0]!='icon' or k[1:] in puzzle_uv for k in g)
assert toggle(2)==3
assert toggle(4)==7 and toggle(8)==15 and toggle(16)==31 # restore defaults for remaining checks
g,_=check(doc_case[0],doc_case[1],doc_case_flags,seen=[doc_case[2]]);assert any(k[0]=='icon' and k[1:] in doc_uv for k in g)
assert toggle(16)==15
g,_=check(doc_case[0],doc_case[1],doc_case_flags,seen=[doc_case[2]]);assert not any(k[0]=='icon' and k[1:] in doc_uv for k in g) and call('KeyMapTestState')&8
assert toggle(16)==31
assert call('KeyMapTestLanguage')==1 # English is the first-launch default.
assert toggle(32,1)==31 and call('KeyMapTestLanguage')==1 # language switch is map-only.
assert toggle(32)==31 and call('KeyMapTestLanguage')==0
english_fixture=(rooms,room_labels,item_labels,ROOM_PAGES,ITEM_PAGES,ROOM_HELP_LABEL,ROOM_HELP_LABEL_COUNT)
rooms,room_labels,item_labels=ko_rooms,ko_room_labels,ko_item_labels
ROOM_PAGES,ITEM_PAGES,ROOM_HELP_LABEL,ROOM_HELP_LABEL_COUNT=ko_room_pages,ko_item_pages,ko_help_start,ko_help_count
g,_=check(0,2);assert sum(v for k,v in g.items() if k[0]=='room')>0
assert toggle(32)==31 and call('KeyMapTestLanguage')==1
rooms,room_labels,item_labels,ROOM_PAGES,ITEM_PAGES,ROOM_HELP_LABEL,ROOM_HELP_LABEL_COUNT=english_fixture
g,_=check(0,2);assert sum(v for k,v in g.items() if k[0]=='room')>0
source=(R/'re2_keymap.c').read_text()
assert 'GetPrivateProfileIntA("MapOverlay","English",1,settings_path)' in source and 'WritePrivateProfileStringA("MapOverlay",keys[i],value,settings_path)' in source
assert 'keys[]={"All","Rooms","Locks","Items","Documents","Puzzles","English"}' in source and 'if(pressed&127)save_settings();' in source
report={'passed':True,'revision':'6.4-bilingual-puzzle-markers','dll_sha256':__import__('hashlib').sha256(DLL.read_bytes()).hexdigest(),
 'per_map_counts':counts,'label_overlap_pairs':overlaps,'pickups_hidden_by_own_bank_bit':pickup_hidden,'guard_value1_rows_visible':seen_guard1,'texture_creates':len(created),
 'checks':['six icon-only area-map markers share toggle 3; Treatment Pool remains visible with bank33 map-info bits set and companion-state flag variations, hides after bank8 bit137 or when unvisited','differential model vs native draw for Leon/Claire x A/B x bank1 bit6 x floors 0-19','13 common pickups use small, item-specific icons only; names are omitted; pickup bank and scenario gates are preserved','four Leon Small-Key locks visible in A/B and hidden by unlock bits','document markers visible only before their own pickup bits and behind document-only toggle 4','all projected SCE 6/7 puzzle/device markers use a flat amber diamond in the core-item marker style and map-only key 5','all non-puzzle interaction AOT markers are excluded','visited-room gating for puzzle markers','pickup bank bit hiding','guard value=1 (raw-mask bit checker)','exit modes 1-3 and floor>=20 suppressed','8192-byte buffer headroom and sentinel','per-page texture cache and device reset','quad bounds/UV/quarter-size item label geometry','room names use the same collision-aware placement in both languages','all room names try one centered line, then retry as two centered lines if the room mask rejects it; Records Room and Emergency Stairway placement assertions','0-5 overlay toggles plus map-only 9 English/Korean language switch','English first-launch default and INI-backed saved toggle state','smaller-font, zero-line-gap, two-paragraph live-status legend always drawn, including when overlays are hidden','REAL native room loop 0x4fa990 hooked vs unhooked: native packets byte-identical, pink pass only for visited non-current rooms with pending pickups','current room stays native red row','cleared rooms no tint','unvisited untouched','tint buffer headroom','save/item-box icons visited-only and room-name-toggle gated'],
 'live_gpu_verified':False,'tint_per_map':tint_counts,'tint_differential_runs':tint_checks}
(R/'native-test-results-v6.4.json').write_text(json.dumps(report,indent=1,ensure_ascii=False))
print('PASS',{k:v for k,v in report.items() if k not in ('per_map_counts',)})
