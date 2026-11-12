"""INI settings on the real ASI under unicorn (2026-11-07, RE0 HD map mod rules): defaults, Version migration that keeps
values and comments, atomic save (copy -> write the copy -> replace; a failed replace keeps the old file), value
clamping, the Shift/Ctrl modifier, the H/[/] keys and the 350 ms toggle rest period. kernel32/user32 calls are served
by a small in-memory file system. Run from build/ with RE2_GAME_EXE set."""
import struct
from pathlib import Path
R=Path(__file__).resolve().parent
exec((R/'test_native-v6.4.py').read_text().split('# ---- harness end')[0])
from unicorn import UC_HOOK_CODE
files={};calls=[];clock={'on':False,'ms':0};keys=set();fail={'move':False}
def cstr(a):
 out=b''
 while (c:=bytes(u.mem_read(a,1)))!=b'\0':out+=c;a+=1
 return out.decode()
def put(a,text):u.mem_write(a,text.encode()+b'\0')
def ini(path):
 sec=None;out={}
 for line in files.get(path,'').splitlines():
  line=line.strip()
  if line.startswith('['):sec=line[1:-1]
  elif '=' in line and not line.startswith(';'):k,v=line.split('=',1);out[(sec,k.strip().lower())]=v.strip()
 return out
def write_key(path,sec,key,value):
 lines=files.get(path,'').splitlines();head=f'[{sec}]'
 if head not in lines:lines+=[head]
 i=lines.index(head)+1
 while i<len(lines) and not lines[i].startswith('['):
  if '=' in lines[i] and not lines[i].startswith(';') and lines[i].split('=')[0].strip().lower()==key.lower():lines[i]=f'{key}={value}';break
  i+=1
 else:lines.insert(i,f'{key}={value}')
 files[path]='\n'.join(lines)+'\n'
def api(name,a):
 calls.append(name)
 if name=='GetPrivateProfileIntA':
  v=ini(cstr(a[3])).get((cstr(a[0]),cstr(a[1]).lower()))
  try:return int(v)&0xffffffff
  except (TypeError,ValueError):return a[2]
 if name=='GetPrivateProfileStringA':
  v=ini(cstr(a[5])).get((cstr(a[0]),cstr(a[1]).lower()),cstr(a[2]))[:a[4]-1];put(a[3],v);return len(v)
 if name=='WritePrivateProfileStringA':write_key(cstr(a[3]),cstr(a[0]),cstr(a[1]),cstr(a[2]));return 1
 if name=='CopyFileA':
  src,dst=cstr(a[0]),cstr(a[1])
  if src not in files:return 0
  files[dst]=files[src];return 1
 if name=='MoveFileExA':
  src,dst=cstr(a[0]),cstr(a[1])
  if fail['move'] or src not in files:return 0
  files[dst]=files.pop(src);return 1
 if name=='DeleteFileA':files.pop(cstr(a[0]),None);return 1
 if name in ('QueryPerformanceFrequency','QueryPerformanceCounter'):
  if clock['on']:u.mem_write(a[0],struct.pack('<q',1000 if name=='QueryPerformanceFrequency' else clock['ms']))
  else:u.mem_write(a[0],bytes(8))
  return 1
 if name=='GetAsyncKeyState':return 0x8000 if a[0] in keys else 0
 if name=='lstrcpyA':put(a[0],cstr(a[1]));return a[0]
 if name=='lstrcatA':put(a[0],cstr(a[0])+cstr(a[1]));return a[0]
 if name=='lstrlenA':return len(cstr(a[0]))
 if name=='lstrcmpiA':x,y=cstr(a[0]).lower(),cstr(a[1]).lower();return (x>y)-(x<y)&0xffffffff
 if name=='wsprintfA':
  fmt=cstr(a[1]);assert fmt=='%u',fmt;put(a[0],str(a[2]));return len(str(a[2]))
 return 0
ARGS={'GetPrivateProfileIntA':4,'GetPrivateProfileStringA':6,'WritePrivateProfileStringA':4,'CopyFileA':3,'MoveFileExA':3,'DeleteFileA':1,
      'QueryPerformanceFrequency':1,'QueryPerformanceCounter':1,'GetAsyncKeyState':1,'lstrcpyA':2,'lstrcatA':2,'lstrlenA':1,'lstrcmpiA':2,'wsprintfA':0}
stubs={};imp_p=struct.unpack_from('<I',b,o+96+8)[0];u.mem_map(0x26000000,0x1000)
while struct.unpack_from('<I',di,imp_p+12)[0]:
 lookup,_,_,_,iat=struct.unpack_from('<5I',di,imp_p);i=0
 while (e:=struct.unpack_from('<I',di,lookup+i*4)[0]):
  name=bytes(di[e+2:di.index(0,e+2)]).decode() if not e&0x80000000 else ''
  if name in ARGS:
   at=0x26000000+len(stubs)*16;stubs[at]=name;u.mem_write(0x10000000+iat+i*4,struct.pack('<I',at))
   u.mem_write(at,b'\xc2'+struct.pack('<H',ARGS[name]*4) if ARGS[name] else b'\xc3') # wsprintfA is cdecl
  i+=1
 imp_p+=20
assert set(stubs.values())==set(ARGS),set(ARGS)-set(stubs.values())
def serve(uc,addr,size,_):
 n=ARGS[stubs[addr]];sp=uc.reg_read(UC_X86_REG_ESP);count=n or 3
 uc.reg_write(UC_X86_REG_EAX,api(stubs[addr],struct.unpack('<'+'I'*count,uc.mem_read(sp+4,4*count))))
u.hook_add(UC_HOOK_CODE,serve,begin=0x26000000,end=0x26000fff)
u.mem_map(0x27000000,0x1000);PATH=0x27000000;put(PATH,'C:\\g\\RE2.AnnotatedMap.ini');INI='C:\\g\\RE2.AnnotatedMap.ini';TMP=INI+'.tmp'
def load():return call('KeyMapTestSettings',PATH,0)
def save():calls.clear();return call('KeyMapTestSettings',PATH,1)
def toggle(bits):call('KeyMapTestToggle',0,bits);call('KeyMapTestToggle',0,0)
call('KeyMapTestInit',0x400000)
# A missing INI gives the defaults: icons 100/80, item names off, Shift, lock beside the door in the room not entered yet; it counts as old (migrate once).
assert load()==1 and call('KeyMapTestIcons')>>18&1==1 and call('KeyMapTestIcons')&0xffff==100|80<<8 and call('KeyMapTestSize')==100 and call('KeyMapTestOpacity')==70
# LockSide (2026-11-13): default 1; a file older than version 5 stored 0 as its default and is switched once; version 5 keeps a chosen 0.
def lock_side():return call('KeyMapTestIcons')>>18&1
files[INI]='[MapOverlay]\nVersion=4\nLockSide=0\n';assert load()==1 and lock_side()==1
files[INI]='[MapOverlay]\nVersion=5\nLockSide=0\n';assert load()==0 and lock_side()==0
files[INI]='[MapOverlay]\nVersion=5\n';assert load()==0 and lock_side()==1
# A 1.1.0 INI (no Version): values and comments survive; one save writes Version=2 and the new keys through a copy.
files[INI]='[MapOverlay]\n; Room and key-item name size\nNameSize=70\nNameOpacity=40\nLegend=0\nEnglish=0\nIconSize=500\nIconOpacity=3\n'
assert load()==1 and call('KeyMapTestSize')==90 and call('KeyMapTestOpacity')==40 and call('KeyMapTestLegend')==0 and call('KeyMapTestLanguage')==0
assert call('KeyMapTestIcons')&0xffff==200|10<<8 # clamped on read
assert save()==1 and TMP not in files and calls.index('CopyFileA')<calls.index('WritePrivateProfileStringA')<calls.index('MoveFileExA')
v=ini(INI);assert v[('MapOverlay','version')]=='5' and v[('MapOverlay','namesize')]=='90' and v[('MapOverlay','iconsize')]=='200' and v[('MapOverlay','modifier')]=='Shift'
assert v[('MapOverlay','itemnames')]=='0' and v[('MapOverlay','lockside')]=='1' and '; Room and key-item name size' in files[INI]
assert load()==0 # migrated: no second rewrite
# A failed replace keeps the previous file and removes the copy.
old=files[INI];fail['move']=True;toggle(16384);fail['move']=False
assert files[INI]==old and TMP not in files and call('KeyMapTestIcons')>>16&1 # the toggle itself still applied
toggle(16384);assert ini(INI)[('MapOverlay','itemnames')]=='2' # all -> no common
toggle(16384);assert ini(INI)[('MapOverlay','itemnames')]=='0' # -> off
toggle(16384);assert ini(INI)[('MapOverlay','itemnames')]=='1' # -> all; [H] saves each state
# One-time migration of the old on/off ItemNames (2026-11-08): old on -> all, old off -> hidden, 2 -> all but common items.
def names_mode():return call('KeyMapTestIcons')>>19&3
for old,mode in (('1',1),('0',0),('2',2),('7',1)):
 files[INI]='[MapOverlay]\nVersion=2\nItemNames='+old+'\n'
 assert load()==1 and names_mode()==mode,(old,names_mode()) # Version 2 file: rewritten once
 assert save()==1 and ini(INI)[('MapOverlay','version')]=='5' and ini(INI)[('MapOverlay','itemnames')]==str(mode) and load()==0
files[INI]='[MapOverlay]\nItemNames=1\n';assert load()==1 and names_mode()==1 # 1.1.0 file without Version: on stays all
# Name size re-base (2026-11-08): the old 80% is the new 100%, so a saved NameSize of an older file is converted once
# (old v -> v x 100 / 80, rounded to 10) and the visible size stays; no saved value gives the new default 100.
def name_size():return call('KeyMapTestSize')
for old,new in (('100',130),('80',100),('60',80),('120',150),('150',190)):
 files[INI]='[MapOverlay]\nVersion=3\nNameSize='+old+'\n'
 assert load()==1 and name_size()==new,(old,name_size())
 assert save()==1 and ini(INI)[('MapOverlay','namesize')]==str(new) and load()==0 and name_size()==new # no second conversion
files[INI]='[MapOverlay]\nVersion=3\n';assert load()==1 and name_size()==100
files[INI]='[MapOverlay]\nVersion=5\nNameSize=70\n';assert load()==0 and name_size()==70
# Events toggle: new key, saved by name (numbers on the keyboard changed, stored toggles did not).
files[INI]='[MapOverlay]\nVersion=3\nCommonItems=1\nEnemies=1\nPuzzles=1\n';assert load()==1 and call('KeyMapTestEvents')==0 and call('KeyMapTestCommon')==1 and call('KeyMapTestMonsters')==1
toggle(131072);assert call('KeyMapTestEvents')==1 and ini(INI)[('MapOverlay','events')]=='1' and ini(INI)[('MapOverlay','commonitems')]=='1' and ini(INI)[('MapOverlay','enemies')]=='1'
toggle(131072);assert call('KeyMapTestEvents')==0 and ini(INI)[('MapOverlay','events')]=='0'
# User-edited [Colors] and comments survive every save.
files[INI]='; my note\n[MapOverlay]\nVersion=3\n[Colors]\n; mine\nCommon=#112233\n'
assert load()==1 and save()==1 and '[Colors]' in files[INI] and 'Common=#112233' in files[INI] and '; mine' in files[INI] and '; my note' in files[INI]
# Keys follow the legend numbers (2026-11-08): 5 puzzles, 6 events, 7 common items, 8 enemies, 9 scope, backslash language.
for key,bits in ((0x35,64),(0x36,131072),(0x37,128),(0x38,256),(0x39,4096),(0xdc,32)): # 0xdc = VK_OEM_5, the won sign on Korean keyboards
 keys.clear();keys.update({key});assert call('KeyMapTestKeys')==bits,(hex(key),call('KeyMapTestKeys'))
keys.clear()
# Modifier: Shift by default, Ctrl from the INI (the game binds Ctrl, config.ini KeyDef 0x11).
keys.clear();keys.update({0x10});assert call('KeyMapTestKeys')==2048
keys.clear();keys.update({0x11});assert call('KeyMapTestKeys')==0
write_key(INI,'MapOverlay','Modifier','ctrl');load();assert call('KeyMapTestIcons')>>17&1 and call('KeyMapTestKeys')==2048
keys.clear();keys.update({0x10});assert call('KeyMapTestKeys')==0
keys.clear();keys.update({0x48,0xdb,0xdd});assert call('KeyMapTestKeys')==16384|32768|65536 # H, [, ]
assert save()==1 and ini(INI)[('MapOverlay','modifier')]=='Ctrl'
# Rest period: a second press of the same key within 350 ms is ignored, another key is not.
clock['on']=True;state=call('KeyMapTestState')
clock['ms']=1000;toggle(2);assert call('KeyMapTestState')==state^2
clock['ms']=1200;toggle(2);assert call('KeyMapTestState')==state^2 # bounced
clock['ms']=1250;toggle(4);assert call('KeyMapTestState')==state^2^4 # other key
clock['ms']=1400;toggle(2);assert call('KeyMapTestState')==state^4 # 400 ms later
clock['on']=False
print('PASS settings: defaults, migration, atomic save, clamp, modifier, keys, rest period')
