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
 u.mem_write(0x20008000,struct.pack('<'+'I'*(len(args)+1),0x20000100,*args));u.reg_write(UC_X86_REG_ESP,0x20008000);u.emu_start(exports[name],0x20000100,count=20000000)
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
key_art=rows((R/'key_art.h').read_text(),'key_art[]')
assert len(key_art)==37 and not {a[0] for a in key_art}&{i[0] for i in icons} # Codex key sprites (2026-11-08) beside the lock-icon sprites
doors=rows((R/'doors-all.h').read_text(),'doors[]')
ov=(R/'overlay_data.h').read_text()
pick_guards=rows(ov,'room_pickup_guards[]');pickups=rows(ov,'room_pickups[]');markers=rows(ov,'map_markers[]')
doc_guards=rows(ov,'document_guards[]');documents=rows(ov,'map_documents[]')
interaction_guards=rows(ov,'interaction_guards[]');interactions=rows(ov,'map_interactions[]')
oicons=rows((R/'overlay_icons.h').read_text(),'overlay_icons[]')
mon_guards=rows((R/'monsters.h').read_text(),'monster_guards[]');monsters=rows((R/'monsters.h').read_text(),'map_monsters[]')
assert len(monsters)>2000 and {m[5] for m in monsters}==set(range(12)) and {50+c for c in range(12)}<={i[0] for i in oicons}
PUZZLE_KEY_W=int(re.search(r'#define PUZZLE_KEY_W (\d+)',(R/'re2_keymap.c').read_text())[1])
LOCK_TENTHS=int(re.search(r'#define LOCK_ICON_TENTHS (\d+)',(R/'re2_keymap.c').read_text())[1])
ICON_TEX=int(re.search(r'OVERLAY_ICON_TEX (\d+)',(R/'overlay_icons.h').read_text())[1]);ICON_W=ICON_TEX//int(re.search(r'OVERLAY_ICON_SCALE (\d+)',(R/'overlay_icons.h').read_text())[1])
MAPS=set(range(200,206))
COMMON={20,21,22,24,25,26,27,29,30,35,38,39,40}
assert len(pickups)>300 and len(markers)>=50 and {m[3] for m in markers}=={9,10} and {i[0] for i in oicons}==({9,10,11,12,13,14,15,16}|{100+x for x in COMMON}|set(range(50,62)))
assert len(interactions)>1000 and {0,1}<={m[0] for m in interactions}<={0,1,2,3} and {m[3] for m in interactions}=={0,3,4,5,6,9,10,11,12,13,14,20} # 20 = event markers; SCE_WATER (7) wading zones are not puzzles
assert all(m[6]+m[7]<=len(interaction_guards) and m[1]<20 and m[2]<256 for m in interactions) and all((g[0]<=34 or g[0] in (130,131)) and g[2] in (0,1) for g in interaction_guards)
assert all(p[3] in (8,34) and p[5]+p[6]<=len(pick_guards) for p in pickups) and all(g[0]<=34 or g[0] in (130,131) for g in pick_guards)
doc_ids={106,107,108,109,111,112,113,114,115,116,117,118,119,120,121,122,123,125,126}
assert documents and {d[4] for d in documents}<=doc_ids and all(d[3] in (8,34) and d[8]+d[9]<=len(doc_guards) for d in documents)
ROOM_PAGES=int(re.search(r'ROOM_LABEL_PAGE_COUNT (\d+)',(R/'room_labels.h').read_text())[1])
ROOM_HELP_LABEL=int(re.search(r'ROOM_HELP_LABEL (\d+)',(R/'room_labels.h').read_text())[1])
ROOM_HELP_LABEL_COUNT=int(re.search(r'ROOM_HELP_LABEL_COUNT (\d+)',(R/'room_labels.h').read_text())[1])
help_icon_x=(lambda text:[int(v) for v in re.search(r'room_help_icon_x\[\]=\{([^}]*)\}',text)[1].split(',')])((R/'room_labels.h').read_text())
ITEM_PAGES=int(re.search(r'ITEM_LABEL_PAGE_COUNT (\d+)',(R/'item_labels.h').read_text())[1])
assert len(room_labels)>96 and ROOM_HELP_LABEL+ROOM_HELP_LABEL_COUNT==len(room_labels) and ROOM_HELP_LABEL_COUNT==57 and len({l[0] for l in item_labels})==128 and len(items)==1178 # 128 = 126 + Lockpick and Special Key, which only name their locks (2026-11-07); +event rewards (Main Fuse, plugs...) and 4-point pickups (Fuse Case), 2026-10-23; 76 key/map/common names + 15 document titles + 35 puzzle names
# Leon B Vacant Factory B1 Shotgun Parts (ROOM5020, AOT attribute 0x71 incl. UNDER) is a [3] key item; no Rocket Launcher event row.
assert any(i[:2]==(0,9) and i[5]==34 and i[6:8]==(34,21) for i in items) and not any(i[5]==17 and i[0]<2 for i in items) # Rocket Launcher: Extreme Battle rows only
assert {20,21,22,24,25,26,27,29,30,35,38,39,40} <= {i[0] for i in item_labels}
help_text=[label['text'] for label in json.loads((R/'room_names-provenance.json').read_text())['labels'][-ROOM_HELP_LABEL_COUNT:]]
label_data=json.loads((R/'room_names-provenance.json').read_text())['labels']
assert label_data[-ROOM_HELP_LABEL_COUNT]['font_px']==22
assert {label['font_px'] for label in label_data[-ROOM_HELP_LABEL_COUNT+1:]}=={20}
assert json.loads((R/'room_names-provenance.json').read_text())['legend_stroke']==3
assert all(label['font_px']>16 for label in label_data[:ROOM_HELP_LABEL])
wrapped=[label for label in label_data[:ROOM_HELP_LABEL] if '\n' in label['text']]
assert (len(wrapped)>0)==(True) and all(len(label['text'].splitlines())==2 and label['w']<=204 for label in wrapped)
assert help_text[:22]==(['Map Notes', '[0] ALL: ON', '[0] ALL: OFF', '[1] ROOMS: ON', '[1] ROOMS: OFF', '[2] LOCKS: ON', '[2] LOCKS: OFF', '[3] KEY ITEMS: ON', '[3] KEY ITEMS: OFF', '[4] FILES & MAPS: ON', '[4] FILES & MAPS: OFF', '[5] PUZZLES: ON', '[5] PUZZLES: OFF', '[\\] LANGUAGE: KOREAN', '[\\] LANGUAGE: ENGLISH', '[8] ENEMIES: ON', '[8] ENEMIES: OFF', '[7] ITEMS: ON', '[7] ITEMS: OFF', '[9] VISITED', '[9] REVEALED', '[9] ALL ROOMS'] if True else ['지도 메모', '[0] 전체 켜짐', '[0] 전체 꺼짐', '[1] 방 이름 켜짐', '[1] 방 이름 꺼짐', '[2] 잠긴 문 켜짐', '[2] 잠긴 문 꺼짐', '[3] 핵심 아이템 켜짐', '[3] 핵심 아이템 꺼짐', '[4] 문서·지도 켜짐', '[4] 문서·지도 꺼짐', '[5] 퍼즐 켜짐', '[5] 퍼즐 꺼짐', '[9] 한국어', '[9] 영어', '[7] 적 켜짐', '[7] 적 꺼짐', '[6] 일반 아이템 켜짐', '[6] 일반 아이템 꺼짐', '[8] 방문 방', '[8] 공개 방', '[8] 전체 방'])
assert all(r[5]<len(room_labels) for r in rooms) and all(i[8]+i[9]<=len(guards) for i in items)
assert all((i[6]<=34 or i[6]==255) and (g[0]<=34 or g[0] in (130,131)) for i in items for g in guards[i[8]:i[8]+i[9]]) # bank_bit table bound; 255 = never hidden (zapping B markers)
room_px=pixels('room_labels.h','room_label_pixels');item_px=pixels('item_labels.h','item_label_pixels')
pages={bytes(struct.pack('<65536H',*room_px[k*65536:(k+1)*65536])):('room',k) for k in range(ROOM_PAGES)}
pages.update({bytes(struct.pack('<65536H',*item_px[k*65536:(k+1)*65536])):('item',k) for k in range(ITEM_PAGES)})
pages[bytes(struct.pack('<65536H',*pixels('atlas.h','atlas_pixels')))]=('atlas',0)
pages[bytes(struct.pack('<65536H',*pixels('overlay_icons.h','overlay_icon_pixels')))]=('icon',0)
pages[bytes(struct.pack('<65536H',*pixels('key_art.h','key_art_pixels')))]=('keyart',0)
assert len(pages)>=ROOM_PAGES+ITEM_PAGES+2
# C-style assets retain hard, palette-limited pixels in every packed icon region.
key_pixels=pixels('atlas.h','atlas_pixels');overlay_pixels=pixels('overlay_icons.h','overlay_icon_pixels')
style_regions=[(key_pixels,i[1],i[2],i[3],i[4]) for i in icons]+[(overlay_pixels,i[1],i[2],ICON_TEX,ICON_TEX) for i in oicons if i[0] not in (12,14,15) and not 50<=i[0]<62] # drawn markers excluded
assert len(style_regions)==36 # 18 key icons (52 Red Card, 75 Manhole Opener, 62 Chess Plug added) + 18 overlay icons (the event diamond added 2026-11-08)
for bitmap,x,y,w,h in style_regions:
 colors={bitmap[yy*256+xx] for yy in range(y,y+h) for xx in range(x,x+w)}-{0}
 assert 1<len(colors)<=17,(x,y,w,h,len(colors))
puzzle_sprite=next(i for i in oicons if i[0]==12)
pu,pv=puzzle_sprite[1:]
assert {overlay_pixels[y*256+x] for y in range(pv,pv+32) for x in range(pu,pu+32)}=={0,0x421,(238>>3)|((184>>3)<<5)|((48>>3)<<10)} # amber diamond with dark rim
assert overlay_pixels[(pv+2)*256+pu+16] and not overlay_pixels[(pv+2)*256+pu+2]
# Monster head sprites: nonempty, distinct, palette-limited and transparent outside each silhouette.
mon_sprites=[tuple(overlay_pixels[y*256+x] for y in range(i[2],i[2]+32) for x in range(i[1],i[1]+32)) for i in sorted(oicons) if 50<=i[0]<62]
assert len(mon_sprites)==len(set(mon_sprites))==12
assert all(0 in sprite and 2<len(set(sprite)-{0})<=16 for sprite in mon_sprites)
KO=R/'korean-assets'
ko_room_labels=rows((KO/'room_labels.h').read_text(),'room_labels[]')
ko_item_labels=rows((KO/'item_labels.h').read_text(),'item_labels[ITEM_LABEL_COUNT]')
ko_rooms=rows((KO/'room_names.h').read_text(),'room_names[]')
ko_header=(KO/'room_labels.h').read_text()
ko_help_icon_x=(lambda text:[int(v) for v in re.search(r'room_help_icon_x\[\]=\{([^}]*)\}',text)[1].split(',')])(ko_header)
ko_room_pages=int(re.search(r'ROOM_LABEL_PAGE_COUNT (\d+)',ko_header)[1])
ko_item_pages=int(re.search(r'ITEM_LABEL_PAGE_COUNT (\d+)',(KO/'item_labels.h').read_text())[1])
ko_help_start=int(re.search(r'ROOM_HELP_LABEL (\d+)',ko_header)[1])
ko_help_count=int(re.search(r'ROOM_HELP_LABEL_COUNT (\d+)',ko_header)[1])
ko_help_text=[label['text'] for label in json.loads((KO/'room_names-provenance.json').read_text())['labels'][-ko_help_count:]]
assert ko_help_count==57 and ko_help_text[:22]==['지도 메모', '[0] 전체 켜짐', '[0] 전체 꺼짐', '[1] 방 이름 켜짐', '[1] 방 이름 꺼짐', '[2] 잠긴 문 켜짐', '[2] 잠긴 문 꺼짐', '[3] 핵심 아이템 켜짐', '[3] 핵심 아이템 꺼짐', '[4] 문서·지도 켜짐', '[4] 문서·지도 꺼짐', '[5] 퍼즐 켜짐', '[5] 퍼즐 꺼짐', '[\\] 언어: 한국어', '[\\] 언어: 영어', '[8] 적 켜짐', '[8] 적 꺼짐', '[7] 일반 아이템 켜짐', '[7] 일반 아이템 꺼짐', '[9] 방문 방', '[9] 공개 방', '[9] 전체 방']
ko_room_px=pixels(KO/'room_labels.h','room_label_pixels');ko_item_px=pixels(KO/'item_labels.h','item_label_pixels')
for k in range(ko_room_pages):pages.setdefault(bytes(struct.pack('<65536H',*ko_room_px[k*65536:(k+1)*65536])),('room',k))
for k in range(ko_item_pages):pages.setdefault(bytes(struct.pack('<65536H',*ko_item_px[k*65536:(k+1)*65536])),('item',k))

# Orange pending-room pages: each floor's 1-bit fill mask expanded to R=0xe0,G=0x78 RGB555 (re2_keymap.c PENDING_RGB555).
for fl,line in enumerate(l for l in (R/'fill_masks.h').read_text().splitlines() if l.startswith('{')):
 m=bytes(int(x) for x in line.strip('{},').split(','));assert len(m)==8192
 pages.setdefault(struct.pack('<65536H',*((0x1c|0x0f<<5) if m[i>>3]&(0x80>>(i&7)) else 0 for i in range(65536))),('fill',fl))
rank_glyphs=rows((R/'rank_glyphs.h').read_text(),'rank_glyphs[]')
pages.setdefault(bytes(struct.pack('<65536H',*pixels(R/'rank_glyphs.h','rank_glyph_pixels'))),('rank',0))
def rank_ref(secs,saves,sprays,flags):
 # Independent restatement of the native result-screen formula (0x4b6e10..0x4b7099).
 steps=0 if secs<=9000 else min(10,-(-(secs-9000)//3600))
 score=100-10*steps+(100-5*saves if saves<=19 else 0)+(100-15*sprays if sprays<=5 else 0)
 if flags&0x800000:score=max(0,score-50)
 return score,next((k for k,l in enumerate((269,199,144,99)) if score>=l),4)
fill_rows=[bytes(int(x) for x in l.strip('{},').split(',')) for l in (R/'fill_masks.h').read_text().splitlines() if l.startswith('{')]
def legend_keys(floor):
 return Counter()
def rank_keys(flags):
 # Rank display defaults off (INI Rank=0, absent under test); the formula is checked via KeyMapTestRank.
 return Counter()
 w=16 if call('KeyMapTestLanguage') else 21
 ids=[w,11,3,0,0,w+1,0,10,0,0,10,0,0,w+2,0,w+3,0]
 return Counter(('rank',0)+tuple(rank_glyphs[i]) for i in ids)
def item_on(item,state):
 # [3] key items, [6] common pickups, [4] area maps (with documents)
 return bool(state&16) if item in MAPS else bool(call('KeyMapTestCommon')) if item in COMMON else bool(state&8)
BANKS={33:0x98ec1c,6:0x98eb74,7:0x98eb94,0:0x989e6c,1:0x989ed0,3:0x98eb2c,4:0x98eb4c,8:0x98ebb4,29:0x98ed24,34:0x98ebd4,255:0x98ed2c} # 29 = FG_ZAPPING ([0x53b218+29*4])
def visible_help(state):
 return Counter(('help',)+room_labels[ROOM_HELP_LABEL+n] for n in help_ids(state))
def help_ids(state):
 # Title line: title, [H] item names (26 on / 27 off), zoom (22), hide (25); ten state rows; readout (2026-11-07):
 # 28/29 name hints, 30/31 Shift/Ctrl, 32/33 icon hints, 34.. values 10%..200%.
 stage=call('KeyMapTestInteractionStage');icons=call('KeyMapTestIcons')
 return [0,{1:26,0:27,2:54}[icons>>19&3],22,25,1 if state&1 else 2,3 if state&2 else 4,5 if state&4 else 6,7 if state&8 else 8,9 if state&16 else 10,11 if stage else 12,17 if call('KeyMapTestCommon') else 18,15 if call('KeyMapTestMonsters') else 16,18+call('KeyMapTestScope'),14 if call('KeyMapTestLanguage') else 13,55 if call('KeyMapTestEvents') else 56,
         28,29,30+(icons>>17&1),30+(icons>>17&1),32,33]+[33+v//10 for v in (call('KeyMapTestOpacity'),call('KeyMapTestSize'),icons>>8&255,icons&255)]
CAT_KEY,CAT_LOCK,CAT_PUZZLE,CAT_DOCUMENT,CAT_COMMON=range(5) # ItemLabel.cat: each name category has its own colour
def item_keys(item,cat=CAT_KEY):
 # A wrapped name is two consecutive item_labels entries of the same item (generate_item_labels.display_lines).
 return [('item',)+l[1:6] for l in item_labels if l[0]==item and l[6]==cat]
def panels():
 out=[]
 for i in range(2):
  v=call('KeyMapTestPanel',i)
  if v:out.append((v&511,v>>9&255,v>>17&511,v>>26))
 return out
def in_panel(x,y,w,h):return any(x<px+pw and px<x+w and y<py+ph and py<y+h for px,py,pw,ph in panels())
# [H] names every marker (2026-11-07): lock, area-map and common-item names are optional in the model (placement may
# drop them: a common-item name only goes where it covers nothing of weight >= 2, and an icon may be hidden).
OPTIONAL=Counter()
def names_on():return call('KeyMapTestIcons')>>16&1
def art_fit(x,y,sz,aw,ah): # key art: longest side fills the marker box, aspect kept, at least 2 px thick (2026-11-08)
 m=max(aw,ah);mn=2 if sz>=4 else 1;w=max(mn,(sz*aw+m//2)//m);h=max(mn,(sz*ah+m//2)//m)
 return (x+(sz-w)//2,y+(sz-h)//2,w,h)
def model(pl,floor,flags,bits,seen,state=31,mode=0):
 def bb(bank,bit):return bit in bits.get(bank,()) or (bank==1 and bit<32 and flags&(0x80000000>>bit)!=0)
 out=Counter();OPTIONAL.clear()
 if mode!=0 or floor>=20:return out
 stage=call('KeyMapTestInteractionStage')
 out.update(visible_help(state));out.update(rank_keys(flags));out.update(legend_keys(floor))
 if state&3==3:
  for m in markers:
   if m[0]==pl and m[1]==floor and m[2] in seen:
    i=[i for i in oicons if i[0]==m[3]][0];out[('icon',0,i[1],i[2],ICON_TEX,ICON_TEX)]+=1
 if state&5==5:
  for d in doors:
   dpl,dfl,x,y,s,unlock,key,mask,bank,*_=d
   if dpl!=pl or dfl!=floor or s not in seen:continue
   if (key==93 and flags&0x40000000) or (key in (94,95,98,99) and not flags&0x40000000):continue
   if not flags&0x40000000:
    if mask&64:continue
   elif (pl and mask&64) or mask&128:continue
   if bb(bank,unlock):continue
   ic=[i for i in icons if i[0]==key]
   if ic:out[('atlas',0,)+ic[0][1:]]+=1
   if ic and names_on():OPTIONAL.update(item_keys(key,CAT_LOCK))
 replaced=set() # puzzles a key item turns into the combined marker: their plain diamond is not drawn
 if state&1:
  for it in items:
   ipl,ifl,x,y,s,item,bank,bit,gs,gc=it
   if not item_on(item,state) or ipl!=pl or ifl!=floor or s not in seen or (bank!=255 and bb(bank,bit)):continue
   if any(bb(g[0],g[1])!=g[2] for g in guards[gs:gs+gc]):continue
   if item in COMMON or item in MAPS:
    i=[i for i in oicons if i[0]==(13 if item in MAPS else 100+item)][0]
    out[('icon',0,i[1],i[2],ICON_TEX,ICON_TEX)]+=1
    if names_on():OPTIONAL.update(item_keys(item,CAT_COMMON if item in COMMON else CAT_DOCUMENT))
   else:
    near=next((k for k,m in enumerate(interactions) if stage and m[0]==pl and m[1]==floor and m[2] in seen and m[3] in (6,7) and
               abs(m[4]-x)<=5 and abs(m[5]-y)<=5 and all(bb(g[0],g[1])==g[2] for g in interaction_guards[m[6]:m[6]+m[7]])),None)
    if near is not None:replaced.add(near)
    sz,(cx,cy)=(PUZZLE_KEY_W,interactions[near][4:6]) if near is not None else ((ICON_W*90+50)//100,(x,y))
    near=near is not None
    if in_panel(min(max(cx+10-sz//2,1),318-sz),min(max(cy+12-sz//2,1),238-sz),sz,sz):continue # star and name skipped under a panel
    art=next((a for a in icons if a[0]==item),None);kart=next((a for a in key_art if a[0]==item),None)
    if kart:out[('keyart',0,)+kart[1:]]+=1
    elif art:out[('keyatlas',0,)+art[1:]]+=1
    else:
     i=[i for i in oicons if i[0]==(15 if near else 14)][0]
     out[('icon',0,i[1],i[2],ICON_TEX,ICON_TEX)]+=1
    if call('KeyMapTestIcons')>>16&1:out.update(item_keys(item,CAT_KEY))
 if state&17==17:
  for d in documents:
   pl0,floor0,seen0,bank,item,x,y,bit,gs,gc=d
   if pl0!=pl or floor0!=floor or seen0 not in seen or bb(bank,bit):continue
   if any(bb(g[0],g[1])!=g[2] for g in doc_guards[gs:gs+gc]):continue
   i=[i for i in oicons if i[0]==11][0]
   out[('icon',0,i[1],i[2],ICON_TEX,ICON_TEX)]+=1
   if names_on():OPTIONAL.update(item_keys(item,CAT_DOCUMENT)) # document title, only where it covers nothing of weight >= 2
 if state&1 and stage:
  for k,m in enumerate(interactions):
   if k in replaced or m[0]!=pl or m[1]!=floor or m[2] not in seen or m[3] not in (6,7):continue
   if any(bb(g[0],g[1])!=g[2] for g in interaction_guards[m[6]:m[6]+m[7]]):continue
   if in_panel(m[4]+10-3,m[5]+12-3,6,6):continue
   i=[i for i in oicons if i[0]==12][0]
   out[('icon',0,i[1],i[2],32,32)]+=1
   if names_on() and m[8]:OPTIONAL.update(item_keys(m[8],CAT_PUZZLE)) # puzzle name, dropped like the diamond when a key name covers it
 if state&1 and call('KeyMapTestMonsters'):
  for m in monsters:
   mpl0,mfl,x,y,s0,cat,dbank,gid,gs,gc=m
   if mpl0!=pl or mfl!=floor or s0 not in seen or (gid!=255 and bb(6 if dbank==6 and not flags&0x2000000 else 7,gid)):continue
   if any(bb(g[0],g[1])!=g[2] for g in mon_guards[gs:gs+gc]):continue
   i=[i for i in oicons if i[0]==50+cat][0];out[('icon',0,i[1],i[2],ICON_TEX,ICON_TEX)]+=1
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
# RE1-style defaults: only All and Rooms start on; the checks below run with every category on.
assert call('KeyMapTestState')==3 and call('KeyMapTestInteractionStage')==0 and call('KeyMapTestCommon')==0 and call('KeyMapTestMonsters')==0
assert call('KeyMapTestIcons')==100|80<<8 # icon size 100, icon opacity 80, [H] item names off, Shift, lock at the door
call('KeyMapTestToggle',0,0);call('KeyMapTestToggle',0,4|8|16|64|128|16384);call('KeyMapTestToggle',0,0)
assert call('KeyMapTestIcons')>>16&1

def revealed_seen(pl,floor,flags):
 # Native unvisited-room test (0x4fae74..0x4faea9): entry mask +0xe (+0xf if 0x989ef8&1), bit0 needs B, bit1 needs A.
 ptr,cnt=struct.unpack('<IB',u.mem_read((0x53eb98 if pl else 0x53eaf8)+floor*8,5));alt=u.mem_read(0x989ef8,1)[0]&1;b=bool(flags&0x40000000)
 out=set()
 for k in range(cnt):
  e=u.mem_read(ptr+k*16,16);m=e[0xf if alt else 0xe]
  if not (m&1 and not b) and not (m&2 and b):out.add(e[0xc])
 return out
RANK_Y=8
def run(pl,floor,flags=None,bits={},seen=range(256),free=0x20000,mode=0,mpl=None):
 mpl=pl if mpl is None else mpl # marker row key (re2_keymap.c marker_pl)
 npl=pl if mpl==4 else mpl # monster_pl: 4th Survivor keeps its monsters
 flags=(pl<<31) if flags is None else flags
 seen=set(seen);state=call('KeyMapTestState');puzzles=call('KeyMapTestInteractionStage')
 u.mem_write(0x989ed0,bytes(32));u.mem_write(0x98eb2c,bytes(0xc0));u.mem_write(0x98ed2c,bytes(32));u.mem_write(0x98ed24,bytes(8))
 u.mem_write(0x989ed0,struct.pack('<I',flags))
 def ibit(bank,bit):return bit in bits.get(bank,()) or (bank==1 and bit<32 and flags&(0x80000000>>bit)!=0)
 sv=bytearray(32)
 for s in seen:struct.pack_into('<I',sv,(s//32)*4,struct.unpack_from('<I',sv,(s//32)*4)[0]|(0x80000000>>(s%32)))
 scope=call('KeyMapTestScope') # [8]: placement model sees what the DLL shows
 seen_drawn=set(range(256)) if scope==3 else seen|(revealed_seen(pl,floor,flags) if scope==2 and floor<20 and u.mem_read((0x53eb98 if pl else 0x53eaf8)+floor*8+5,1)[0] in bits.get(33,()) else set())
 u.mem_write(0x98ec04,bytes(sv));u.mem_write(0x691f7a,bytes([floor]));u.mem_write(0x691f62,bytes([mode]));u.mem_write(0x691fb8,struct.pack('<hh',4,6))
 for bank,bs in ((k,v) for k,v in bits.items() if k in BANKS): # after the 32-byte visited write, which also covers bank33 0x98ec1c
  for n in bs:
   q=BANKS[bank]+(n//32)*4;v=struct.unpack('<I',u.mem_read(q,4))[0];u.mem_write(q,struct.pack('<I',v|(0x80000000>>(n%32))))
 u.mem_write(0x21000000,b'\xa5'*0x30000);u.mem_write(0x524e1c,struct.pack('<II',0x21000000,0x21000000+free));call('KeyMapTestDraw')
 seen=seen_drawn
 end=struct.unpack('<I',u.mem_read(0x524e1c,4))[0]
 assert 0x21000000<=end<=0x21000000+free and (end-0x21000000)%32==0
 assert bytes(u.mem_read(end,16))==b'\xa5'*16 # nothing written past the last queued quad
 got=Counter();rects=[];reserved=[];last_item_marker=None;legend_rects=[];help_rects=[];rank_xs=[]
 if state&3==3:
  reserved += [(m[4]+10-4,m[5]+12-4,8,8) for m in markers if m[0]==mpl and m[1]==floor and m[2] in seen]
  if True:
   for it in items:
    if item_on(it[5],state) and it[0]==mpl and it[1]==floor and it[4] in seen and not ibit(it[6],it[7]) and all(ibit(g[0],g[1])==g[2] for g in guards[it[8]:it[8]+it[9]]):
     reserved.append((min(max(it[2]+7,1),311)-2,min(max(it[3]+9,1),231)-2,11,11))
  if state&17==17:
   for d in documents:
    dp,df,ds,bank,item,x,y,bit,gs,gc=d
    if dp==mpl and df==floor and ds in seen and not ibit(bank,bit) and all(ibit(g[0],g[1])==g[2] for g in doc_guards[gs:gs+gc]):reserved.append((x+6,y+8,8,8))
  if call('KeyMapTestMonsters'):
   for m in monsters:
    if m[0]==npl and m[1]==floor and m[4] in seen and not (m[7]!=255 and ibit(6 if m[6]==6 and not flags&0x2000000 else 7,m[7])) and all(ibit(g[0],g[1])==g[2] for g in mon_guards[m[8]:m[8]+m[9]]):reserved.append((m[2]+7,m[3]+9,6,6))
  if puzzles:
   for m in interactions:
    if m[0]==mpl and m[1]==floor and m[2] in seen and m[3] in (6,7) and all(ibit(g[0],g[1])==g[2] for g in interaction_guards[m[6]:m[6]+m[7]]):reserved.append((m[4]+7,m[5]+9,6,6))
 for p in range(0x21000000,end,32):
  q=u.mem_read(p,32);cmd,tex=struct.unpack_from('<II',q,4);x,y,x1,y1=struct.unpack_from('<4h',q,16)
  assert cmd in (0x24,0x400025) and tex in created and 1<=x<=x1<=318 and 1<=y<=y1<=238 and (x<x1 or y<y1),(x,y,x1,y1)
  kind,page=created[tex];uu,vv,sw,sh=q[24],q[25],q[26]-q[24]+1,q[27]-q[25]+1;w,h=x1-x+1,y1-y+1
  is_name=kind=='item' or kind=='room' and (page,uu,vv,sw,sh) not in room_labels[ROOM_HELP_LABEL:]
  # Names use the name opacity, map icons (atlas/icon pages) the icon opacity (2026-11-07); legend text stays opaque.
  alpha=call('KeyMapTestOpacity') if is_name else call('KeyMapTestIcons')>>8&255 if kind in ('icon','atlas','keyart') else 100
  expected_cmd=0x400025 if alpha<100 else 0x24
  assert cmd==expected_cmd,(kind,cmd,expected_cmd)
  if cmd==0x400025:assert struct.unpack_from('<I',q,28)[0]==(((alpha*255+50)//100)<<24)|0x808080
  if (w,h) in ((5,5),(3,3)) and kind in ('icon','atlas','item','fill'):
   got[('legend',kind,uu,vv,sw,sh)]+=1;legend_rects.append((x,y,w,h));continue
  art_positions=[]
  if kind in ('atlas','keyart'):
   for it in items:
    if it[0]!=mpl or it[1]!=floor or not any(a[0]==it[5] and tuple(a[1:])==(uu,vv,sw,sh) for a in (icons if kind=='atlas' else key_art)):continue
    pz=next((m for m in interactions if puzzles and state&1 and m[0]==mpl and m[1]==floor and m[2] in seen and m[3]==6 and abs(m[4]-it[2])<=5 and abs(m[5]-it[3])<=5 and all(ibit(g[0],g[1])==g[2] for g in interaction_guards[m[6]:m[6]+m[7]])),None)
    sz,(cx,cy)=(PUZZLE_KEY_W,pz[4:6]) if pz else ((ICON_W*90+50)//100,it[2:4])
    art_positions.append(art_fit(min(max(cx+10-sz//2,1),318-sz),min(max(cy+12-sz//2,1),238-sz),sz,sw,sh))
  if kind in ('atlas','keyart') and (x,y,w,h) in art_positions:
   matches=[i for i in items if i[0]==mpl and i[1]==floor and any(a[0]==i[5] and tuple(a[1:])==(uu,vv,sw,sh) for a in (icons if kind=='atlas' else key_art))]
   assert matches,(floor,uu,vv,sw,sh)
   last_item_marker=(x+w//2,y+h//2,(max(w,h)+1)//2+1);reserved.append((x,y,w,h));got[('keyatlas' if kind=='atlas' else 'keyart',page,uu,vv,sw,sh)]+=1;continue
  assert kind!='keyart',(x,y,w,h,uu,vv,sw,sh)
  if kind=='atlas':
   # icon_box (2026-10-27): longest visible side scaled to LOCK_ICON_TENTHS/10 px, aspect kept.
   assert any((uu,vv,sw,sh)==(i[1],i[2],i[3],i[4]) and (w,h)==tuple(max(1,(d*LOCK_TENTHS+max(sw,sh)*5)//(max(sw,sh)*10)) for d in (sw,sh)) for i in icons),(uu,vv,sw,sh,w,h)
   rects.append((x,y,w,h));reserved.append((x,y,w,h))
  elif kind=='icon':
   icon_kind=next(i[0] for i in oicons if (i[1],i[2])==(uu,vv))
   if icon_kind>=120 or icon_kind==13:
    item=icon_kind-100 if icon_kind!=13 else 200
    assert (item in COMMON or item in MAPS) and (w,h)==((ICON_W*90+50)//100,)*2
    # Area maps under a diamond/star become a badge 3 px down-right of it (2026-10-28 East Office safe).
    shifts=((0,0),(3,3)) if icon_kind==13 else ((0,0),)
    assert any(i[0]==mpl and i[1]==floor and (i[5]==item or icon_kind==13 and i[5] in MAPS) and (x-(i[2]+10-w//2),y-(i[3]+12-h//2)) in shifts for i in items),(item,x,y)
    rects.append((x,y,w,h));reserved.append((x,y,w,h))
   elif icon_kind in (14,15): # [3] key-item star (90% icon size); 15 = 6 px combined marker over a puzzle within 5 px
    sw7=(ICON_W*90+50)//100;assert state&8 and w==h
    def star_at(i):
     pz=[m for m in interactions if puzzles and state&1 and m[0]==mpl and m[1]==floor and m[2] in seen and m[3] in (6,7) and
         abs(m[4]-i[2])<=5 and abs(m[5]-i[3])<=5 and all(ibit(g[0],g[1])==g[2] for g in interaction_guards[m[6]:m[6]+m[7]])]
     sz,(cx,cy)=(PUZZLE_KEY_W,pz[0][4:6]) if pz else (sw7,i[2:4])  # combined marker 6 px (2026-10-26)
     return (14+bool(pz),sz,min(max(cx+6+4-sz//2,1),318-sz),min(max(cy+6+6-sz//2,1),238-sz)),(cx+10,cy+12,(sz+1)//2+1)
    hit=[star_at(i)[1] for i in items if i[0]==mpl and i[1]==floor and star_at(i)[0]==(icon_kind,w,x,y)];assert hit,(icon_kind,x,y,w)
    last_item_marker=hit[0];reserved.append((x,y,w,h)) # label anchor = drawn marker centre
   elif icon_kind==11:
    assert (w,h)==(ICON_W,ICON_W);rects.append((x,y,w,h));reserved.append((x,y,w,h))
    assert any(min(max(d[5]+6+4-w//2,1),318-w)==x and min(max(d[6]+6+6-h//2,1),238-h)==y for d in documents if d[0]==mpl and d[1]==floor),(x,y)
   elif 50<=icon_kind<62:
    assert (w,h)==(6,6) and call('KeyMapTestMonsters') and state&1
    assert any(m[0]==npl and m[1]==floor and m[5]==icon_kind-50 and min(max(m[2]+6+4-3,1),312)==x and min(max(m[3]+6+6-3,1),232)==y for m in monsters),(x,y)
    rects.append((x,y,w,h));reserved.append((x,y,w,h))
   elif icon_kind==12:
    assert (w,h)==(6,6) and puzzles and state&1
    assert any(m[0]==mpl and m[1]==floor and m[2] in seen and m[3] in (6,7) and
       min(max(m[4]+6+4-3,1),312)==x and min(max(m[5]+6+6-3,1),232)==y and
       all(ibit(g[0],g[1])==g[2] for g in interaction_guards[m[6]:m[6]+m[7]]) for m in interactions),(x,y)
    rects.append((x,y,w,h));reserved.append((x,y,w,h))
   elif icon_kind==16:
    assert (w,h)==(6,6) and call('KeyMapTestEvents') and state&1
    assert any(m[0]==mpl and m[1]==floor and m[2] in seen and m[3]==20 and
       min(max(m[4]+6+4-3,1),312)==x and min(max(m[5]+6+6-3,1),232)==y and
       all(ibit(g[0],g[1])==g[2] for g in interaction_guards[m[6]:m[6]+m[7]]) for m in interactions),(x,y)
    rects.append((x,y,w,h));reserved.append((x,y,w,h))
   else:
    assert (w,h)==(ICON_W,ICON_W);rects.append((x,y,w,h));reserved.append((x,y,w,h))
    # Exactly centred on projected point + 6 (arrow-sprite centre), pan (4,6), clamped only at edges.
    assert any(min(max(m[4]+6+4-w//2,1),318-w)==x and min(max(m[5]+6+6-h//2,1),238-h)==y for m in markers if m[0]==mpl and m[1]==floor),(x,y)
  elif kind=='box':
   assert x>=160 and (w,h)==((sw+2)//4,(sh+2)//4) or (uu,vv,sw,sh)==(0,0,4,4),(x,y,w,h)
  elif kind=='rank' and y<200: # item-box panel counts (top right) reuse the digit page
   assert x>=160 and (w,h)==((sw+2)//4,(sh+2)//4),(x,y,w,h)
  elif kind=='rank':
   assert (w,h)==((sw+2)//4,(sh+2)//4) and RANK_Y<=y<=RANK_Y+5 and x>=60,(x,y,w,h) # quarter-size line, bottom centre right of the legend
   rank_xs.append((x,w))
  elif kind=='room' and (uu,vv,sw,sh)==(0,0,1,1):
   assert w==1 or h==1;assert any(min(r[6],r[8])+4==x and min(r[7],r[9])+6==y and abs(r[8]-r[6])+1==w and abs(r[9]-r[7])+1==h for r in rooms if r[6]|r[7]|r[8]|r[9]),(x,y,w,h)
   reserved.append((x,y,w,h))
  elif kind=='room':
   help_rows=room_labels[ROOM_HELP_LABEL:ROOM_HELP_LABEL+ROOM_HELP_LABEL_COUNT]
   # name size 100% is the former 80% (2026-11-08): room and marker names draw at 1/5 of their raster, the legend at 1/4
   assert (w,h)==(((sw+2)//4,(sh+2)//4) if (page,uu,vv,sw,sh) in help_rows else ((2*sw+5)//10,(2*sh+5)//10)),(w,h,sw,sh);rects.append((x,y,w,h))
   if (page,uu,vv,sw,sh) in help_rows:
    n=help_rows.index((page,uu,vv,sw,sh))
    state=call('KeyMapTestState');stage=call('KeyMapTestInteractionStage');language=call('KeyMapTestLanguage')
    selected=help_ids(state)
    assert n in selected,(n,selected)
    # Row-by-row 6/5-column legend (2026-10-26); exact layout is covered by the pre-release legend tests.
    assert 0<x and x+w<=320 and (200<=y and y+h<=240 or n>=28 and y>=1 and y+h<=17),(x,y,w,h) # legend; readout top left (2026-11-07)
    got[('help',page,uu,vv,sw,sh)]+=1
    help_rects.append((x,y,w,h,help_icon_x[n]))
    reserved.append((x,y,w,h))
    continue
   matches=[r for r in rooms if r[0]==pl and r[1]==floor and room_labels[r[5]]==(page,uu,vv,sw,sh)]
   assert matches,(page,uu,vv,sw,sh)
   # Pinned room_box placement (2026-10-26) is checked by test_label_priority.py.
   assert 1<=x and x+w<=319 and 1<=y and y+h<=239,(x,y,w,h)
   reserved.append((x,y,w,h))
  elif kind=='item':
   assert (w,h)==((2*sw+5)//10,(2*sh+5)//10),(w,h,sw,sh)
   # Queue order is stars -> names -> diamonds (2026-10-26), so a name no longer follows its own marker.
   # Placement rule (8 marker-box candidates, 0 px gap, weighted overlap) is checked by test_label_priority.py.
   last_item_marker=None;rects.append((x,y,w,h));reserved.append((x,y,w,h))
  else:assert (w,h)==((sw+1)//2,(sh+1)//2),(w,h,sw,sh);rects.append((x,y,w,h))
  got[(kind,page,uu,vv,sw,sh)]+=1
 if rank_xs:
  assert max(x+w for x,w in rank_xs)==318
 # Every legend marker sits inside its row's text box, at or right of the row's marker slot.
 assert all(any(hx+ix<=x and x+w<=hx+hw and hy<=y and y+h<=hy+hh for hx,hy,hw,hh,ix in help_rects if ix) for x,y,w,h in legend_rects),(legend_rects,help_rects)
 overlaps=sum(1 for i,a in enumerate(rects) for c in rects[i+1:] if a[0]<c[0]+c[2] and c[0]<a[0]+a[2] and a[1]<c[1]+c[3] and c[1]<a[1]+a[3])
 return got,overlaps

def fits(got,want):
 high={(i[1],i[2]) for i in oicons if i[0] in (14,15)}   # stars and combined markers are never skipped
 diamond={(i[1],i[2]) for i in oicons if i[0]==12}      # a puzzle diamond a name covers is skipped (key names win, 2026-10-26)
 names=any(k[0]=='item' for k in got)
 # set-wise (2026-11-08): at the smaller name size two markers of one device may both keep their name, the model lists it once
 return not set(got-want)-set(OPTIONAL) and all(k[0] in ('icon','atlas') and (k[2],k[3]) not in high and ((k[2],k[3]) not in diamond or names) for k in want-got)

def check(pl,floor,flags=None,bits={},seen=range(256)):
 f=(pl<<31) if flags is None else flags
 got,ov=run(pl,floor,flags,bits,seen);want=model(pl,floor,f,bits,set(seen),call('KeyMapTestState'))
 # under_high (2026-10-26): lower markers covered by a key star/name or puzzle diamond are skipped, so only
 # those may be missing; nothing unexpected may be drawn. Exact layout: test_label_priority.py.
 assert fits(got,want),(pl,floor,hex(f),bits,got-want,want-got)
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
    if it[0]!=pl or it[1]!=floor or it[6]==255:continue
    base=model(pl,floor,flags,{},set(range(256)))
    if it[5] in COMMON or it[5] in MAPS:
     icon=next(i for i in oicons if i[0]==(13 if it[5] in MAPS else 100+it[5]));key=('icon',0,icon[1],icon[2],ICON_TEX,ICON_TEX)
    else:
     l=[l for l in item_labels if l[0]==it[5]][0];key=('item',)+l[1:6]
    after,_=check(pl,floor,flags,{it[6]:{it[7]}})
    if all(((g[0]==1 and g[1]<32 and flags&(0x80000000>>g[1])!=0))==g[2] for g in guards[it[8]:it[8]+it[9]]):
     if base[key]:assert after[key]-OPTIONAL[key]<base[key],it;pickup_hidden+=1 # 0: star under the legend (RE0 rule); OPTIONAL: its lock's name
# Vacant Factory 1F sub-floors: control room 503 (seen 92) is drawn on floor 10, and on floor 11 once the Up Key
# raised the lift in scenario B (0x4faf80: bank4 bit98). Its markers exist on both sub-floor maps.
for rpl in (0,1):
 for f in (10,11):
  assert any(m[:3]==(rpl,f,92) and m[3]==6 for m in interactions),(rpl,f)  # Up Key panel
  assert {m[3] for m in markers if m[:3]==(rpl,f,92)}=={9,10},(rpl,f)       # typewriter + item box
  assert any(i[:2]==(rpl,f) and i[4]==92 for i in items),(rpl,f)
 assert any(d[:2]==(rpl,10) and d[6]==94 for d in doors) and any(d[:2]==(rpl,11) and d[6]==94 for d in doors)
# Armory (B1 corridor 211) Red Card reader: lock icon on floor 5 until bank4 bit14 (card used), both characters.
red=next(('atlas',0)+i[1:] for i in icons if i[0]==52)
for rpl in (0,1):
 assert check(rpl,5,rpl<<31)[0][red]==1 and check(rpl,5,rpl<<31,bits={4:{14}})[0][red]==0
# Kennel manhole (Manhole Opener, bank4 bit59, both) and Plug Passage shutter (chess plugs, bank4 bit58, Leon): locks, not puzzles.
manhole=next(('atlas',0)+i[1:] for i in icons if i[0]==75);plug=next(('atlas',0)+i[1:] for i in icons if i[0]==62)
for rpl in (0,1):
 # Claire's Crank star (Kennel) covers the manhole lock until it is picked up (key items are never covered).
 taken={i[6]:{i[7]} for i in items if i[0]==rpl and i[1]==5 and i[5]==67}
 assert check(rpl,5,rpl<<31,bits=taken)[0][manhole]==1 and check(rpl,5,rpl<<31,bits={**taken,4:taken.get(4,set())|{59}})[0][manhole]==0
assert check(0,6,0)[0][plug]==1 and check(0,6,0,bits={4:{58}})[0][plug]==0 and check(1,6,1<<31)[0][plug]==0
assert not any(m[3]==6 and (m[0],m[1],m[2]) in {(0,6,61),(0,5,56),(1,5,56),(0,5,47),(1,5,47)} for m in interactions)
# Lab (user 2026-10-23, Leon B): Power Room Key lock only where the native map has it (lock 22: B1 = floor 13), not on
# the Pump Room's B2 sub-floor; B3 power switch (605 event, bank4 bit145) is a device diamond until switched on;
# the Master Key (98) pickup is drawn in Leon B's Power Room upper (604, floor 13).
power=next(('atlas',0)+i[1:] for i in icons if i[0]==95);puz=next(('icon',0,i[1],i[2],ICON_TEX,ICON_TEX) for i in oicons if i[0]==12)
for rpl in (0,1):
 b=rpl<<31|0x40000000  # keys 94/95/98/99 are scenario-B locks
 assert check(rpl,13,b)[0][power]>=1 and check(rpl,14,b)[0][power]==0
 assert check(rpl,15,rpl<<31)[0][puz]>check(rpl,15,rpl<<31,bits={4:{145}})[0][puz]
# Event rewards (sentinel AOT handed out by op 0x47): 60D Main Fuse at the Fuse Case machine (key item on a puzzle
# spot -> combined sprite), Fuse Case (4-point AOT), 609 Lounge shotgun shells (user 2026-10-23).
assert any(it[:2]==(0,16) and it[5]==76 for it in items) and any(it[:2]==(0,16) and it[5]==77 for it in items)
assert sum(1 for it in items if it[:2]==(0,16) and it[5]==21 and (it[2],it[3])==(79,157))>=1
combo=next(('keyart',0)+a[1:] for a in key_art if a[0]==76) # Main Fuse has its own art (2026-11-08), which replaces the combined marker
assert check(0,16,0x40000000)[0][combo]>=1
master=('item',)+[l for l in item_labels if l[0]==98][0][1:6]
assert check(0,13,0x40000000)[0][master]==1 and check(0,13,0)[0][master]==0
# Live rank line: DLL formula equals the independent restatement at every boundary.
for secs in (0,9000,9001,12600,12601,45000,45001,99999):
 for saves in (0,1,19,20,0xfffe):
  for sprays in (0,5,6):
   for fl in (0,0x800000):
    s,r=rank_ref(secs,saves,sprays,fl);v=call('KeyMapTestRank',secs,saves,sprays,fl);assert (v&0xffff,v>>16)==(s,r),(secs,saves,sprays,fl,s,r,v)
assert rank_ref(9000,0,0,0)==(300,0) and rank_ref(9000+3600*4,7,1,0)==(210,1) and rank_ref(0,20,6,0x800000)==(50,4)
# Key 7 monsters (2026-10-22, replaces the item-box panel): off by default; on, every floor matches the model; a
# spawn hides once its global id is dead in bank 6 (stage < 3) / bank 7 (stage >= 3 or bonus 0x02000000).
assert call('KeyMapTestMonsters')==0 and not any(k[0]=='icon' and any(i[0]>=50 and i[0]<62 and (i[1],i[2])==k[2:4] for i in oicons) for k in run(0,2)[0])
call('KeyMapTestToggle',0,256);call('KeyMapTestToggle',0,0);assert call('KeyMapTestMonsters')==1
for pl in (0,1):
 for f in range(20):check(pl,f);check(pl,f,(pl<<31)|0x40000000)
zm=next(m for m in monsters if m[0]==0 and m[7]!=255 and m[8+1]==0 and m[1]<20)
zi=[i for i in oicons if i[0]==50+zm[5]][0];zk=('icon',0,zi[1],zi[2],ICON_TEX,ICON_TEX)
alive=check(0,zm[1],0,seen=[zm[4]])[0][zk];dead=check(0,zm[1],0,bits={zm[6]:{zm[7]}},seen=[zm[4]])[0][zk]
assert alive>dead,(zm,alive,dead)
ex_mon=[m for m in monsters if m[0]==2];assert ex_mon
call('KeyMapTestToggle',0,256);call('KeyMapTestToggle',0,0);assert call('KeyMapTestMonsters')==0
# Zapping: A-only gas marker hides after Z14; B shows Poison Ivy only when A set Z14; one cord use hides both cord spots.
ZAP={15,206,207,208,209}
def zap_count(pl,floor,flags,bits):
 got,_=check(pl,floor,flags,bits);return sum(v for k,v in got.items() if k[0]=='item' and k[1:] in {l[1:6] for l in item_labels if l[0] in ZAP} and k[3]!=0)
gas=next(i for i in items if i[5]==208 and i[0]==0);ivy=next(i for i in items if i[5]==209 and i[0]==0)
assert zap_count(0,gas[1],0,{})>=1 and zap_count(0,gas[1],0,{29:{14}})<zap_count(0,gas[1],0,{})
assert zap_count(0,ivy[1],0x40000000,{29:{14}})>zap_count(0,ivy[1],0x40000000,{})
cords=[i for i in items if i[5]==207 and i[0]==0];assert len(cords)==2 and cords[0][1]==cords[1][1]
assert zap_count(0,cords[0][1],0,{29:{9}})<=zap_count(0,cords[0][1],0,{})-2
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
# area maps follow [4] files & maps
call('KeyMapTestToggle',0,0);call('KeyMapTestToggle',0,16)
assert check(0,6,0x40000000)[0][treatment_map]==0
call('KeyMapTestToggle',0,0);call('KeyMapTestToggle',0,16)
assert check(0,6,0x40000000)[0][treatment_map]==1

# Weapon Box Key is found at the cable-car platform in all four scenarios;
# the separate Power Room Key at Laboratory B5 is scenario B only.
weapon_label=('item',)+[l for l in item_labels if l[0]==63][0][1:6]
weapon_lock=('atlas',0)+[i for i in icons if i[0]==63][0][1:]
for pl,scenario in ((0,0),(0,0x40000000),(1,0),(1,0x40000000)):
 got,_=check(pl,9,(pl<<31)|scenario,seen=[90]);assert got[weapon_label]==1,(pl,scenario,got.get(weapon_label,0))
 got,_=check(pl,17,(pl<<31)|scenario,seen=[120]);assert got[weapon_lock]==1,(pl,scenario,got.get(weapon_lock,0))
 got,_=check(pl,17,(pl<<31)|scenario,bits={4:{159}},seen=[120]);assert got[weapon_lock]==0,(pl,scenario,got.get(weapon_lock,0))
# Leon's Rook Plug in the 1F Interrogation Room has an exact native projection;
# it is present in both scenarios and disappears after pickup.
rook_rows=[it for it in items if it[0]==0 and it[1]==2 and it[2:5]==(176,90,44) and it[5]==60]
assert len(rook_rows)==1 and rook_rows[0][7]==56 and rook_rows[0][6]==8 and rook_rows[0][9]==0
rook_label=('item',)+[l for l in item_labels if l[0]==60][0][1:6]
for scenario in (0,0x40000000):
 got,_=check(0,2,scenario,seen=[44]);assert got[rook_label]==1,('Rook Plug',scenario,got.get(rook_label,0))
 got,_=check(0,2,scenario,bits={8:{56}},seen=[44]);assert got.get(rook_label,0)==0,('Rook Plug pickup',scenario)
assert all(it[0]!=1 or it[5]!=60 for it in items)
# Claire A/B's Eagle Stone replaces the Leon-only Rook Plug at the same shelf.
eagle_rows=[it for it in items if it[0]==1 and it[1]==2 and it[2:5]==(176,90,44) and it[5]==58]
assert len(eagle_rows)==1 and eagle_rows[0][7]==56 and eagle_rows[0][6]==8 and eagle_rows[0][9]==0
eagle_label=('item',)+[l for l in item_labels if l[0]==58][0][1:6]
for scenario in (0,0x40000000):
 got,_=check(1,2,(1<<31)|scenario,seen=[44]);assert got[eagle_label]==1,('Eagle Stone',scenario)
 got,_=check(1,2,(1<<31)|scenario,bits={8:{56}},seen=[44]);assert got.get(eagle_label,0)==0,('Eagle Stone pickup',scenario)
assert all(it[0]!=0 or it[5]!=58 for it in items)
# North Control Room B2 ammo survives the upstairs/downstairs setup branch.
for item,bit in ((21,175),(22,176)):
 north=[it for it in items if it[0]==0 and it[5]==item and it[6:8]==(8,bit)]
 assert len(north)==1 and north[0][9]==0
 it=north[0]
 icon=('icon',0)+[i for i in oicons if i[0]==100+item][0][1:]+(ICON_TEX,ICON_TEX)
 for scenario in (0,0x40000000):
  got,_=check(0,it[1],scenario,seen=[it[4]]);assert got[icon]>=1,('North Control ammo',item,scenario)
  got,_=check(0,it[1],scenario,bits={8:{bit}},seen=[it[4]]);assert got.get(icon,0)==0,('North Control taken',item,scenario)
  got,_=check(0,it[1],scenario,seen=[]);assert got.get(icon,0)==0,('North Control unvisited',item,scenario)
# All audited storey-gated pickups are present, and each disappears by its own bit.
for pl,floor,seen,expected in ((0,7,133,{(30,51),(20,173),(35,52)}), # 35: event reward (403 func 24 -> 47 14)
                              (0,8,134,{(21,175),(22,176)}),
                              (1,7,133,{(38,53),(38,173),(38,174),(20,176)}),
                              (1,8,134,{(25,51),(24,175)}),(1,7,72,{(40,186),(40,187)})):
 rs=[it for it in items if (it[0],it[1],it[4])==(pl,floor,seen)]
 assert {(it[5],it[7]) for it in rs}==expected
 for scenario in (0,0x40000000):
  flags=(pl<<31)|scenario
  before,_=check(pl,floor,flags,seen=[seen])
  for it in rs:
   icon=next(i for i in oicons if i[0]==100+it[5]);key=('icon',0,icon[1],icon[2],ICON_TEX,ICON_TEX)
   after,_=check(pl,floor,flags,bits={it[6]:{it[7]}},seen=[seen])
   assert before[key]-after[key]==1,(pl,floor,it[5],it[7],scenario)
fax=[d for d in documents if (d[0],d[1],d[2],d[4],d[7])==(0,7,133,122,192)]
assert len(fax)==1
for scenario in (0,0x40000000):
 before,_=check(0,7,scenario,seen=[133]);after,_=check(0,7,scenario,bits={8:{192}},seen=[133])
 icon=next(i for i in oicons if i[0]==11);key=('icon',0,icon[1],icon[2],ICON_TEX,ICON_TEX)
 assert before[key]-after[key]==1,('North Control fax',scenario)
# Regression for the user's North Control Room screenshot: label clears both ammo icons.
for language in (1,0):
 call('KeyMapTestToggle',0,0)
 if call('KeyMapTestLanguage')!=language:
  call('KeyMapTestToggle',0,32);call('KeyMapTestToggle',0,0)
 if language:run(0,8,0x40000000,seen=[134])
 else:
  u.mem_write(0x524e1c,struct.pack('<II',0x21000000,0x21020000));call('KeyMapTestDraw')
 end=struct.unpack('<I',u.mem_read(0x524e1c,4))[0];name_boxes=[];ammo_boxes=[]
 for pos in range(0x21000000,end,32):
  packet=bytes(u.mem_read(pos,32));tid=struct.unpack_from('<I',packet,8)[0]
  kind,page=created[tid];x,y,x1,y1=struct.unpack_from('<4h',packet,16)
  if kind=='room' and y<180:name_boxes.append((x,y,x1+1,y1+1))
  if kind=='icon' and x>240 and y<180:ammo_boxes.append((x,y,x1+1,y1+1))
 assert name_boxes and len(ammo_boxes)>=2,(language,name_boxes,ammo_boxes)
 # User rule 2026-10-26: room names may cover common items and monsters, so no non-overlap requirement here.
if call('KeyMapTestLanguage')!=1:
 call('KeyMapTestToggle',0,32);call('KeyMapTestToggle',0,0)
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
power_label=('item',)+[l for l in item_labels if l[0]==95][0][1:6]
for pl,scenario,expected in ((0,0,0),(0,0x40000000,1),(1,0,0),(1,0x40000000,1)):
 got,_=check(pl,17,(pl<<31)|scenario,seen=[120]);assert got[power_label]==expected,(pl,scenario,got.get(power_label,0))
# The C. Panel Key (U) and Platform Key are B-scenario-only pickups; the third
# Small Key is Leon B only. These assertions guard the location data as well as
# the renderer's scenario filtering.
for item,floor,seen,expected in ((94,11,96,{(0,0):0,(0,0x40000000):1,(1,0):0,(1,0x40000000):1}),
                                (99,18,127,{(0,0):0,(0,0x40000000):1,(1,0):0,(1,0x40000000):1})):
 label=('item',)+[l for l in item_labels if l[0]==item][0][1:6]
 for pl,scenario in ((0,0),(0,0x40000000),(1,0),(1,0x40000000)):
  got,_=check(pl,floor,(pl<<31)|scenario,seen=[seen]);assert got[label]==expected[pl,scenario],(item,pl,scenario,got.get(label,0))
small_key=('item',)+[l for l in item_labels if l[0]==31][0][1:6]
for pl,scenario,expected in ((0,0,0),(0,0x40000000,1),(1,0,0),(1,0x40000000,0)):
 got,_=check(pl,8,(pl<<31)|scenario,seen=[77]);assert got[small_key]==expected,(31,pl,scenario,got.get(small_key,0))
master_key=('item',)+[l for l in item_labels if l[0]==98][0][1:6]
for pl,scenario,expected in ((0,0,0),(0,0x40000000,1),(1,0,0),(1,0x40000000,1)):
 got,_=check(pl,13 if pl==0 else 16,(pl<<31)|scenario,seen=[103 if pl==0 else 107],bits={4:{92}} if pl==1 and scenario else {});assert got[master_key]==expected,(98,pl,scenario,got.get(master_key,0))
wolf_medal=('item',)+[l for l in item_labels if l[0]==73][0][1:6]
for pl,scenario,expected in ((0,0,1),(0,0x40000000,1),(1,0,0),(1,0x40000000,1)):
 got,_=check(pl,8,(pl<<31)|scenario,seen=[77]);assert got[wolf_medal]==expected,(73,pl,scenario,got.get(wolf_medal,0))
# Room labels/items only for visited rooms.
assert run(0,2,seen=())[0]==visible_help(call('KeyMapTestState'))+rank_keys(0)+legend_keys(2)
only200=[r for r in rooms if r[0]==0 and r[1]==2][0][2]
got,_=check(0,2,seen=[only200]);assert sum(v for k,v in got.items() if k[0]=='room')==1
# Spot checks from items-report.md (would fail with the raw-mask bank_bit bug: value=1 guards).
guard1=[it for it in items if any(g[2]==1 for g in guards[it[8]:it[8]+it[9]])]
assert guard1
seen_guard1=sum(1 for it in guard1 for extra in (0,0x40000000,0x02000000,0x42000000) if model(it[0],it[1],(it[0]<<31)|extra,{},set(range(256)))[('item',)+[l for l in item_labels if l[0]==it[5]][0][1:6]])
assert seen_guard1>0 # these rows are covered by the differential runs above
assert counts['LAF2']['item']>0 and counts['LAF2']['room']>0 and counts['CBF3']['item']>0
# Other characters/floors never leak: Leon data never drawn for Claire.
for f in range(20):check(1,f) # same differential rule as above (under_high skips only)
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
# Enlarged OFF/scope rows can occupy pages not requested by the default draw state.
expected_room_pages={r[0] for r in room_labels[:ROOM_HELP_LABEL]}|{k[1] for k in visible_help(call('KeyMapTestState'))}
assert {('atlas',0),('icon',0),('keyart',0)}|{('room',k) for k in expected_room_pages} <= set(created.values())
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
 # Pending pass: additive packet retextured from the native fill to the overlay's orange room-shape page.
 tint=[p for p in packets if struct.unpack_from('<I',p,4)[0]&0x200000 and struct.unpack_from('<I',p,8)[0]!=FILL]
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
    for p in tint:assert struct.unpack_from('<I',p,4)[0]==0x200024 and struct.unpack_from('<I',p,8)[0] and struct.unpack_from('<I',p,12)[0]==0
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
 assert all(struct.unpack_from('<I',p,12)[0]==0 for p in tint) # orange pass uses its own direct-colour page
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
assert 3<=sum(v for k,v in g.items() if k[0]=='icon' and k[1:] in save_uv)<=sum(1 for m in markers if m[0]==0 and m[1]==2) # under_high may hide one
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
toggle(128) # [6] common pickups off too
assert toggle(2)==29 and toggle(4)==25 and toggle(8)==17 and toggle(16)==1 # room, lock, item and document switches are independent
pz_names={k for n in {m[8] for m in interactions if m[8]} for k in item_keys(n,CAT_PUZZLE)} # puzzle names belong to the puzzle switch
g,_=check(0,2);g=Counter({k:v for k,v in g.items() if k not in pz_names});assert g==visible_help(call('KeyMapTestState'))+rank_keys(0)+legend_keys(2)+Counter({k:v for k,v in g.items() if k[0]=='icon' and k[1:] in puzzle_uv}) and not any(k[0] in ('room','atlas','item') for k in g)
assert toggle(1)==0 # master off hides every overlay except the help line
g,_=check(0,2);assert g==visible_help(call('KeyMapTestState'))+rank_keys(0)+legend_keys(2)
assert toggle(2)==2 and toggle(1)==3 # category state is retained while master is off
g,_=check(0,2);g=Counter({k:v for k,v in g.items() if k not in pz_names});assert sum(v for k,v in g.items() if k[0]=='room')>0 and sum(v for k,v in g.items() if k[0]=='icon')>0 and not any(k[0]=='atlas' for k in g) and not any(k[0]=='item' for k in g)
assert toggle(2)==1 # hiding room names also hides typewriter/item-box icons
g,_=check(0,2);assert not any(k[0]=='room' for k in g) and all(k[0]!='icon' or k[1:] in puzzle_uv for k in g)
assert toggle(2)==3
assert toggle(4)==7 and toggle(8)==15 and toggle(16)==31 # restore defaults for remaining checks
toggle(128);assert call('KeyMapTestCommon')==1
# [6] common pickups and [3] key items are independent; area maps follow [4] documents.
common_n=lambda g:sum(v for k,v in g.items() if k[0]=='icon' and next(i[0] for i in oicons if (i[1],i[2])==k[2:4]) in {100+x for x in COMMON})
map_n=lambda g:sum(v for k,v in g.items() if k[0]=='icon' and next(i[0] for i in oicons if (i[1],i[2])==k[2:4])==13)
key_n=lambda g:sum(v for k,v in g.items() if k[0] in ('keyatlas','keyart') or k[0]=='icon' and next(i[0] for i in oicons if (i[1],i[2])==k[2:4]) in (14,15)) # key stars ([H] names now cover locks/common items too)
g,_=check(0,2);assert common_n(g)>0 and key_n(g)>0
toggle(128);assert call('KeyMapTestCommon')==0
g2,_=check(0,2);assert common_n(g2)==0 and key_n(g2)==key_n(g)
toggle(128);toggle(8);g3,_=check(0,2);assert key_n(g3)==0 and common_n(g3)>=common_n(g);toggle(8) # stars off uncovers under_high pickups
# East Office safe: the police map sits beside the unsolved safe diamond, so both draw (user 2026-10-28).
mf=next(i for i in items if i[5] in MAPS and i[:4]==(0,2,220,134))
g4,_=check(mf[0],mf[1],mf[0]<<31);assert map_n(g4)==1 and g4[('icon',0)+next(o[1:] for o in oicons if o[0]==12)+(ICON_TEX,ICON_TEX)]>=1
toggle(16);g5,_=check(mf[0],mf[1],mf[0]<<31);assert map_n(g5)==0;toggle(16)
# [8] scope: 1 visited only, 2 + every room of a floor whose map bit (bank 0x98ec1c, floor-table byte +5) is set, 3 all.
assert call('KeyMapTestScope')==1
def floor_bit(pl,floor):return u.mem_read((0x53eb98 if pl else 0x53eaf8)+floor*8+5,1)[0]
everything=lambda pl,floor:model(pl,floor,pl<<31,{},set(range(256)),call('KeyMapTestState'))
nothing=lambda pl,floor:model(pl,floor,pl<<31,{},set(),call('KeyMapTestState'))
rv={33:{floor_bit(0,2)}}
assert fits(run(0,2,bits=rv,seen=())[0],nothing(0,2))                       # scope 1 ignores the map bit
toggle(4096);assert call('KeyMapTestScope')==2
revealed=lambda pl,floor:model(pl,floor,pl<<31,{},revealed_seen(pl,floor,pl<<31),call('KeyMapTestState'))
assert fits(run(0,2,bits=rv,seen=())[0],revealed(0,2))                      # revealed floor: rooms the native map draws
# Sewer B1: junction (seen 72) and south office (seen 132) carry mask 3 = never drawn before a visit.
assert {72,132}.isdisjoint(revealed_seen(0,8,0)) and {72,132}.isdisjoint(revealed_seen(0,8,0x40000000)) and len(revealed_seen(0,8,0))==9
sw={33:{u.mem_read(0x53eaf8+8*8+5,1)[0]}}
assert fits(run(0,8,bits=sw,seen=())[0],revealed(0,8)) and revealed(0,8)!=everything(0,8)
assert fits(run(0,2,seen=())[0],nothing(0,2))                               # map not taken: visited only
toggle(4096);assert call('KeyMapTestScope')==3
assert fits(run(0,2,seen=())[0],everything(0,2))                            # all rooms regardless of the map bit
# [8] cycles from ALL back to VISITED.
toggle(4096);assert call('KeyMapTestScope')==1
g,_=check(doc_case[0],doc_case[1],doc_case_flags,seen=[doc_case[2]]);assert any(k[0]=='icon' and k[1:] in doc_uv for k in g)
assert toggle(16)==15
g,_=check(doc_case[0],doc_case[1],doc_case_flags,seen=[doc_case[2]]);assert not any(k[0]=='icon' and k[1:] in doc_uv for k in g) and call('KeyMapTestState')&8
assert toggle(16)==31
assert call('KeyMapTestLanguage')==1 # English is the first-launch default.
assert toggle(32,1)==31 and call('KeyMapTestLanguage')==1 # language switch is map-only.
assert toggle(32)==31 and call('KeyMapTestLanguage')==0
english_fixture=(rooms,room_labels,item_labels,ROOM_PAGES,ITEM_PAGES,ROOM_HELP_LABEL,ROOM_HELP_LABEL_COUNT,help_icon_x)
rooms,room_labels,item_labels,help_icon_x=ko_rooms,ko_room_labels,ko_item_labels,ko_help_icon_x
ROOM_PAGES,ITEM_PAGES,ROOM_HELP_LABEL,ROOM_HELP_LABEL_COUNT=ko_room_pages,ko_item_pages,ko_help_start,ko_help_count
g,_=check(0,2);assert sum(v for k,v in g.items() if k[0]=='room')>0
assert toggle(32)==31 and call('KeyMapTestLanguage')==1
rooms,room_labels,item_labels,ROOM_PAGES,ITEM_PAGES,ROOM_HELP_LABEL,ROOM_HELP_LABEL_COUNT,help_icon_x=english_fixture
g,_=check(0,2);assert sum(v for k,v in g.items() if k[0]=='room')>0
source=(R/'re2_keymap.c').read_text()
assert 'GetPrivateProfileIntA("MapOverlay","English",1,settings_path)' in source and all(f'"{k}",0,settings_path)' in source for k in ('Locks','Items','Documents','Puzzles','CommonItems','Enemies'))
assert all(f'"{k}"' in source for k in ('ItemNames','IconSize','IconOpacity','Modifier','LockSide','Version','Scope')) # load/save/migration behaviour: test_settings.py
report={'passed':True,'revision':'6.4-bilingual-puzzle-markers','dll_sha256':__import__('hashlib').sha256(DLL.read_bytes()).hexdigest(),
 'per_map_counts':counts,'label_overlap_pairs':overlaps,'pickups_hidden_by_own_bank_bit':pickup_hidden,'guard_value1_rows_visible':seen_guard1,'texture_creates':len(created),
 'checks':['six named area-map markers share toggle 3; Treatment Pool remains visible with bank33 map-info bits set and companion-state flag variations, hides after bank8 bit137 or when unvisited','differential model vs native draw for Leon/Claire x A/B x bank1 bit6 x floors 0-19','13 common pickups use small, item-specific icons only; names are omitted; pickup bank and scenario gates are preserved','four Leon Small-Key locks visible in A/B and hidden by unlock bits','document markers visible only before their own pickup bits and behind document-only toggle 4','all projected SCE 6/7 puzzle/device markers use a flat amber diamond in the core-item marker style and map-only key 5','all non-puzzle interaction AOT markers are excluded','visited-room gating for puzzle markers','pickup bank bit hiding','guard value=1 (raw-mask bit checker)','exit modes 1-3 and floor>=20 suppressed','8192-byte buffer headroom and sentinel','per-page texture cache and device reset','quad bounds/UV/quarter-size item label geometry','room names use the same collision-aware placement in both languages','all room names try one centered line, then retry as two centered lines if the room mask rejects it; Records Room and Emergency Stairway placement assertions','0-5 overlay toggles plus map-only 9 English/Korean language switch','English first-launch default and INI-backed saved toggle state','Pretendard Medium, one-map-pixel-line-gap, two-paragraph live-status legend always drawn, including when overlays are hidden','REAL native room loop 0x4fa990 hooked vs unhooked: native packets byte-identical, pink pass only for visited non-current rooms with pending pickups','current room stays native red row','cleared rooms no tint','unvisited untouched','tint buffer headroom','save/item-box icons visited-only and room-name-toggle gated'],
 'live_gpu_verified':False,'tint_per_map':tint_counts,'tint_differential_runs':tint_checks}
(R/'native-test-results-v6.4.json').write_text(json.dumps(report,indent=1,ensure_ascii=False))
print('PASS',{k:v for k,v in report.items() if k not in ('per_map_counts',)})

# Game modes (2026-10-22): Extreme Battle (bank0 bit 7) loads ROOMA..G and draws only those rows (pl|2), gated by SCD
# vars 0x1e character / 0x1f level (guard banks 130/131); 4th Survivor/Tofu (bank0 bits 28/31) draws no markers.
def mode_run(pl,floor,sys_bits=(),var1e=0,var1f=1):
 u.mem_write(0x989e6c,struct.pack('<I',sum(0x80000000>>n for n in sys_bits)));u.mem_write(0x98eb20,struct.pack('<hh',var1e,var1f))
 mpl=4 if 28 in sys_bits else pl|2 if 7 in sys_bits else pl
 try:return run(pl,floor,bits={130:{var1e},131:{var1f}},mpl=mpl)[0]
 finally:u.mem_write(0x989e6c,bytes(4));u.mem_write(0x98eb20,bytes(4))
def kinds(got):return Counter(k[0] for k in got.elements())
def ex_rows(pl,floor,var1e=0,var1f=1):
 vals={130:var1e,131:var1f}
 return [it for it in items if it[0]==pl|2 and it[1]==floor and all(((vals[g[0]]==g[1])==bool(g[2]) if g[0] in vals else g[2]==0) for g in guards[it[8]:it[8]+it[9]])]
assert {it[0] for it in items}=={0,1,2,3} and any(it[0]==2 and it[5]==36 for it in items)
for pl in (0,1):
 normal=kinds(mode_run(pl,2));ex=kinds(mode_run(pl,2,(7,)));hunk=kinds(mode_run(pl,2,(28,)))
 key=sum(1 for it in ex_rows(pl,2) if it[5] not in COMMON and it[5] not in MAPS)
 lines=sum(len(item_keys(it[5])) for it in ex_rows(pl,2) if it[5] not in COMMON and it[5] not in MAPS)
 assert key==3 and ex['item']>=lines and normal['item']!=ex['item'],(pl,normal,ex,key)  # star icon + label (1-2 lines) per key item; [H] adds other markers' names
 assert hunk['item']==0 and hunk['icon']==0 and hunk['room']==normal['room']>0 and ex['room']==normal['room'],(hunk,normal)
 assert key_n(mode_run(pl,6,(7,)))==0<key_n(mode_run(pl,6))  # no Extreme Battle key items on floor 6 (its common pickups are named with [H])
 for var1f in (0,1,2,3):  # factory B100 bomb: exactly one row per level value
  assert sum(1 for it in ex_rows(pl,2,0,var1f) if it[5]==36 and it[7]==254)==1
 for var1e,want in ((0,{20}),(1,{24}),(2,{20}),(3,{20})):  # E030: Ada's?/Claire's grenade rounds by character
  assert {it[5] for it in ex_rows(pl,10,var1e)}==want,(var1e,ex_rows(pl,10,var1e))
for pl in (0,1):  # sewer D010 two-deck room: green herbs upper deck (floor 7), blue herbs lower deck (floor 8)
 assert sum(1 for it in ex_rows(pl,7) if it[5]==38)>=3 and sum(1 for it in ex_rows(pl,8) if it[5]==40)==2
 assert kinds(mode_run(pl,7,(7,)))['icon']>=3
# Extreme Battle opcode 0x8D pickups (2026-10-22): Under the Bridge D080 gives Leon Shotgun Shells via a goto into case 3
# once bank4 bit 29 is set, Shotgun Parts before that.
d080=[(it[5],tuple(map(tuple,guards[it[8]:it[8]+it[9]]))) for it in items if it[0]==2 and it[1]==8 and it[2:4]==(115,150)]
assert any(i==21 and (130,0,1) in g and (4,29,1) in g for i,g in d080) and any(i==34 and (130,0,1) in g for i,g in d080),d080
assert sum(1 for it in items if it[0]==2)>300
# Extreme Battle Library A120 (SAT-0 table stacks): Leon (var 0x1e != 1) gets 8 Handgun Bullets, Claire grenade rounds.
lib=[it for it in items if it[0]==2 and it[1]==3 and it[2:4]==(80,100)]
assert sum(1 for it in lib if it[5]==20 and (130,1,0) in [tuple(g) for g in guards[it[8]:it[8]+it[9]]])==8,lib
# Monsters per mode: Extreme Battle draws its own spawns; 4th Survivor keeps the real player's monster rows.
call('KeyMapTestToggle',0,256);call('KeyMapTestToggle',0,0)
mon_kinds={(i[1],i[2]) for i in oicons if 50<=i[0]<62}
mcount=lambda got:sum(v for k,v in got.items() if k[0]=='icon' and k[2:4] in mon_kinds)
exf=next(m[1] for m in monsters if m[0]==2 and m[9]==0)
assert mcount(mode_run(0,exf,(7,)))>0
hf=next(m[1] for m in monsters if m[0]==0 and m[9]==0)
assert mcount(mode_run(0,hf,(28,)))>0 and mcount(mode_run(0,hf,(28,)))==mcount(mode_run(0,hf))
call('KeyMapTestToggle',0,256);call('KeyMapTestToggle',0,0)
print('game-mode checks ok')
# LockSide (2026-11-07): 0 keeps the lock on the door; 1 puts it in the room not entered yet: the destination (door AOT
# arrival point) unless only the destination was visited, then the door's own side (AOT centre).
lock_door=next(d for d in doors if d[13]!=255 and d[4]!=d[13] and (d[9],d[10])!=(d[11],d[12]) and d[6] in {i[0] for i in icons} and d[7]==0 and d[8]==255)
lpl,lfl,lx,ly,lseen,_,lkey,_,_,lx1,ly1,lx2,ly2,lseen2=lock_door
lic=next(i for i in icons if i[0]==lkey)
def lock_at(seen,side):
 call('KeyMapTestLockSide',side);got=[]
 items_were_on=bool(call('KeyMapTestState')&8)
 if items_were_on:toggle(8) # isolate door icons from pickups reusing the same atlas art
 run(lpl,lfl,lpl<<31,seen=seen)
 if items_were_on:toggle(8)
 end=struct.unpack('<I',u.mem_read(0x524e1c,4))[0]
 for p in range(0x21000000,end,32):
  q=u.mem_read(p,32);x0,y0,x1,y1=struct.unpack_from('<4h',q,16)
  if created.get(struct.unpack_from('<I',q,8)[0])==('atlas',0) and (q[24],q[25])==lic[1:3]:got.append(((x0+x1+1)//2,(y0+y1+1)//2))
 call('KeyMapTestLockSide',0);return got
def room_centre(pl,floor,seen):
 ptr,count=struct.unpack('<IB',u.mem_read((0x53eb98 if pl&1 else 0x53eaf8)+floor*8,5))
 for k in range(count):
  q=bytes(u.mem_read(ptr+k*16,16))
  if q[12]==seen:return struct.unpack_from('<h',q,4)[0]+q[2]//2,struct.unpack_from('<h',q,6)[0]+q[3]//2
def beside(seen,w,h):
 # 2026-11-13: beside the native 8x8 door bar (at the door's x,y), on the side of the room not entered yet: out from the bar centre along the axis
 # towards that room's centre, half the bar + half the marker + 1 px; pan (4,6)
 rx,ry=room_centre(lpl,lfl,seen);cx,cy=lx+4,ly+4;vx,vy=rx-cx,ry-cy
 if abs(vx)>=abs(vy):return (cx+4+(-1 if vx<0 else 1)*(4+w//2+1),cy+6)
 return (cx+4,cy+6+(-1 if vy<0 else 1)*(4+h//2+1))
m_=max(lic[3],lic[4]);lw,lh=((lic[3]*LOCK_TENTHS*100*100//10000+m_*5)//(m_*10),(lic[4]*LOCK_TENTHS*100*100//10000+m_*5)//(m_*10))
assert lock_at([lseen],0)==[(lx+4,ly+6)] # pan (4,6)
assert lock_at([lseen],1)==[beside(lseen2,lw,lh)] and lock_at([lseen,lseen2],1)==[beside(lseen2,lw,lh)]
toggle(4096);toggle(4096);assert call('KeyMapTestScope')==3 # all rooms: the door shows before its own room is visited
assert lock_at([lseen2],1)==[beside(lseen,lw,lh)]
toggle(4096);assert call('KeyMapTestScope')==1
print('lock side ok')
# [H] names every marker that has a name (2026-11-07, RE0): with key items off, lock-key, area-map and common-item names
# still appear on their markers; [H] off removes every name. Documents and puzzles have no name data in RE2.
rev={('item',)+l[1:6]:l[0] for l in item_labels}
if not call('KeyMapTestCommon'):toggle(128)
assert call('KeyMapTestState')&31==31 and call('KeyMapTestIcons')>>16&1
toggle(8) # key items off: no stars, no key names
named=set()
for f in range(20):
 for k in run(0,f,0)[0]:
  if k[0]=='item':named.add(rev[k])
assert named&COMMON and named&MAPS and named&{d[6] for d in doors},named
# [H] has three states (user 2026-11-08): all -> no common items -> off -> all.
def names_by_state():
 out=set()
 for f in range(20):
  for k in run(0,f,0)[0]:
   if k[0]=='item':out.add(rev[k])
 return out
assert call('KeyMapTestIcons')>>19&3==1
toggle(16384);assert call('KeyMapTestIcons')>>19&3==2
no_common=names_by_state()
assert not no_common&COMMON and no_common&MAPS and no_common&{d[6] for d in doors},no_common # everything but common items
toggle(16384);assert call('KeyMapTestIcons')>>19&3==0 and not any(k[0]=='item' for f in (2,3,5) for k in run(0,f,0)[0])
toggle(16384);assert call('KeyMapTestIcons')>>19&3==1 and names_by_state()&COMMON
toggle(8)
# key items back on: their names stay in the no-common state and go in the off state
toggle(8);key_names=lambda:{k for f in range(20) for k in run(0,f,0)[0] if k[0]=='item' and rev[k] not in COMMON|MAPS and rev[k] not in {d[6] for d in doors}}
toggle(16384);assert key_names();toggle(16384);assert not key_names();toggle(16384);assert key_names()
toggle(8)
# Events (2026-11-08): a purple '?' diamond at a story scene's trigger (extract_overlay: FMV cutscene started by an event AOT),
# shown only with [6] on and hidden once the scene's progress flag (FG_COMMON bank 4) is set.
ev_rows=[m for m in interactions if m[3]==20];assert len(ev_rows)>=10 and {m[0] for m in ev_rows}=={0,1}
# scenes the room script starts at once (Rooftop, Art Storage, Main Hall) sit at the room's centre (2026-11-08, candidate 10); scenes without a persistent flag or in boss rooms have none
assert {m[1] for m in ev_rows if m[0]==0}>={2,3,7},{m[1] for m in ev_rows}
ev_icon=next(i for i in oicons if i[0]==16);ev_key=('icon',0,ev_icon[1],ev_icon[2],32,32)
assert call('KeyMapTestEvents')==0
for m in ev_rows:assert run(m[0],m[1],m[0]<<31)[0][ev_key]==0 # default off
# Event marks have no names (RE0 rule, user 2026-11-08): the same item-name labels are drawn with events off and on, in every
# [H] state, so no name raster is placed for an event diamond.
def label_keys(pl,floor):return {k for k in run(pl,floor,pl<<31)[0] if k[0]=='item'}
floors_with_events={(m[0],m[1]) for m in ev_rows}
off_names={f:label_keys(*f) for f in floors_with_events}
for mode in (1,2,0):
 while call('KeyMapTestIcons')>>19&3!=mode:toggle(16384)
 off_names={f:label_keys(*f) for f in floors_with_events}
 toggle(131072)
 assert {f:label_keys(*f) for f in floors_with_events}==off_names,('an event mark got a name',mode)
 toggle(131072)
while call('KeyMapTestIcons')>>19&3!=1:toggle(16384)
toggle(131072);assert call('KeyMapTestEvents')==1
for m in ev_rows:
 bank,bit,value=interaction_guards[m[6]:m[6]+m[7]][-1];assert (bank,value)==(4,0)
# One marker per floor (2026-11-10): the next pending scene, first by ascending done flag (play order); when it is done the next
# one appears; none once all are done; none while that scene's own room is unvisited (the later scenes wait for it).
for f in sorted(floors_with_events):
 rows=sorted((r for r in ev_rows if r[:2]==f),key=lambda r:interaction_guards[r[6]:r[6]+r[7]][-1][1])
 bits=[]
 for r in rows:
  b=interaction_guards[r[6]:r[6]+r[7]][-1][1]
  if b not in bits:bits.append(b)
 for k in range(len(bits)+1):
  got=run(f[0],f[1],f[0]<<31,{4:set(bits[:k])})[0][ev_key]
  assert got==(1 if k<len(bits) else 0),(f,k,bits,got)               # exactly one while any is pending, none when all are done
  if k<len(bits):
   nxt=next(r for r in rows if interaction_guards[r[6]:r[6]+r[7]][-1][1]==bits[k])
   assert run(f[0],f[1],f[0]<<31,{4:set(bits[:k])},seen=[x for x in range(256) if x!=nxt[2]])[0][ev_key]==0,(f,k) # its room is unvisited: none
 assert run(f[0],f[1],f[0]<<31,{},seen=())[0][ev_key]==0,f             # an unvisited floor shows none
toggle(131072);assert call('KeyMapTestEvents')==0 and all(run(m[0],m[1],m[0]<<31)[0][ev_key]==0 for m in ev_rows)
print('marker names ok',sorted(named))
