"""Native packet check: factory floor arrows reflect visited floors, including gaps."""
import struct
from pathlib import Path
R=Path(__file__).resolve().parent
exec((R/'test_native-v6.4.py').read_text().split('# ---- harness end')[0])
u.mem_write(0x4021c0,bytes.fromhex('c20800'))
u.mem_map(0x22000000,0x900000)
u.mem_write(0x6805b8,struct.pack('<I',0x22000000));u.mem_write(0x228c8338,struct.pack('<I',1))
u.mem_write(0x405ec0,bytes.fromhex('c20800'))
def create(u,a,n,_):u.reg_write(UC_X86_REG_EAX,123)
u.hook_add(UC_HOOK_CODE,create,begin=0x405ec0,end=0x405ec0)
call('KeyMapTestInit',0x400000)
for floor,visited,want in [(9,[9,12],{196}),(12,[9,12],{18}),(10,[9,10,12],{18,196}),(10,[10],set()),(2,[2,3,4],set())]:
 u.mem_write(0x691f7a,bytes([floor]));u.mem_write(0x98ec00,struct.pack('<I',sum(0x80000000>>f for f in visited)))
 u.mem_write(0x524e1c,struct.pack('<II',0x21000000,0x21020000));call('KeyMapTestNavArrows')
 end=struct.unpack('<I',u.mem_read(0x524e1c,4))[0]
 got={struct.unpack('<h',u.mem_read(p+18,2))[0] for p in range(0x21000000,end,32)}
 got-={114} # existing left/right area arrows
 assert got==want,(floor,visited,got,want)
ptr=call('KeyMapTestNavPixels');px=struct.unpack('<65536H',u.mem_read(ptr,131072))
assert all(px[(128+x)*256+y]==px[y*256+x] for x in range(72) for y in range(96))
print('PASS factory visited-floor arrows and rotated pixels')
