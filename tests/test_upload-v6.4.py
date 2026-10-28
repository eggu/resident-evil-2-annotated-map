import os
from pathlib import Path
exec((Path(__file__).resolve().parent/'test_native-v6.4.py').read_text().replace('count=1000000','count=30000000').split('# ---- harness end')[0])
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_INVALID
from unicorn.x86_const import UC_X86_REG_EIP
u.mem_map(0x22000000,0x900000);u.mem_map(0x23000000,0x1000000)
u.mem_write(0x6805b8,struct.pack('<I',0x22000000));u.mem_write(0x228c8338,struct.pack('<I',1));u.mem_write(0x228c8334,struct.pack('<I',16));u.mem_write(0x228c83f4,struct.pack('<I',0x2000));u.mem_write(0x228c834e,bytes([10,31,5,5,31,5,0,31,5,15,1,1]));u.mem_write(0x2200183c,struct.pack('<I',0x5173b0))
# Stub the resource-ID allocator and heap, retaining native texture allocation/copy routines.
u.mem_write(0x416c40,bytes.fromhex('b801000000c20400'));u.mem_write(0x50aa00,b'\xc3');u.mem_write(0x50aa10,b'\xc3');heap=0x23000000

def malloc(u,a,n,_):
 global heap
 size=struct.unpack('<I',u.mem_read(u.reg_read(UC_X86_REG_ESP)+4,4))[0];u.reg_write(UC_X86_REG_EAX,heap);heap+=(size+15)&~15
u.hook_add(UC_HOOK_CODE,malloc,begin=0x50aa00,end=0x50aa00)
trace=[]
def tracing(u,a,n,_):
 trace.append(a)
 if len(trace)>12:trace.pop(0)

def bad(u,a,p,n,v,_):print('BAD',hex(p),hex(u.reg_read(UC_X86_REG_EIP)),[hex(x) for x in trace]);return False
u.hook_add(UC_HOOK_MEM_INVALID,bad)
u.mem_map(0x24000000,0x10000)
gi,go,gb=parse(GAME.read_bytes(),0x400000);rv=struct.unpack_from('<I',gb,go+96+8)[0];p=rv;api={};count=0
sizes={'SetRect':5,'IntersectRect':3,'IsRectEmpty':1,'SetRectEmpty':1,'CopyRect':2,'OffsetRect':3}
while struct.unpack_from('<I',gi,p+12)[0]:
 lookup,_,_,name,iat=struct.unpack_from('<5I',gi,p);i=0
 while (v:=struct.unpack_from('<I',gi,lookup+i*4)[0]):
  if v<0x80000000:
   name=bytes(gi[v+2:gi.index(0,v+2)]).decode()
   if name in sizes:
    stub=0x24000000+count*16;count+=1;api[stub]=name;u.mem_write(0x400000+iat+i*4,struct.pack('<I',stub));u.mem_write(stub,b'\xc2'+struct.pack('<H',sizes[name]*4))
  i+=1
 p+=20
def winrect(u,a,n,_):
 if a not in api:return
 name=api[a];args=struct.unpack('<'+'I'*sizes[name],u.mem_read(u.reg_read(UC_X86_REG_ESP)+4,sizes[name]*4));out=args[0];value=1
 if name=='SetRect':u.mem_write(out,struct.pack('<4I',*args[1:]))
 elif name=='SetRectEmpty':u.mem_write(out,bytes(16))
 elif name=='CopyRect':u.mem_write(out,bytes(u.mem_read(args[1],16)))
 elif name=='IntersectRect':
  aa=struct.unpack('<4i',u.mem_read(args[1],16));bb=struct.unpack('<4i',u.mem_read(args[2],16));q=(max(aa[0],bb[0]),max(aa[1],bb[1]),min(aa[2],bb[2]),min(aa[3],bb[3]));value=int(q[0]<q[2] and q[1]<q[3]);u.mem_write(out,struct.pack('<4i',*q) if value else bytes(16))
 elif name=='IsRectEmpty':
  q=struct.unpack('<4i',u.mem_read(out,16));value=int(q[0]>=q[2] or q[1]>=q[3])
 elif name=='OffsetRect':
  q=struct.unpack('<4I',u.mem_read(out,16));u.mem_write(out,struct.pack('<4I',*((q[i]+args[1+i%2])&0xffffffff for i in range(4))))
 u.reg_write(UC_X86_REG_EAX,value)
u.hook_add(UC_HOOK_CODE,winrect,begin=0x24000000,end=0x24010000)
import re
def source(path,name,page):
 body=(R/path).read_text().split(name,1)[1].split('={',1)[1].split(';',1)[0]
 return [int(v,0) for v in re.findall(r'0x[0-9a-fA-F]+|\d+',body)][page*65536:(page+1)*65536]
ROOM_PAGES=int(re.search(r'ROOM_LABEL_PAGE_COUNT (\d+)',(R/'room_labels.h').read_text())[1])
ITEM_PAGES=int(re.search(r'ITEM_LABEL_PAGE_COUNT (\d+)',(R/'item_labels.h').read_text())[1])
def verify_pages(pages,language):
 results=[]
 for i,(path,name,page) in enumerate(pages):
  call('KeyMapTestUploadPage',i);assert u.reg_read(UC_X86_REG_EAX)==1,(language,i)
  surface=bytes(u.mem_read(0x2200183c,64));ptr=struct.unpack_from('<I',surface,4)[0];w,h,pitch=struct.unpack_from('<hhh',surface,0x1a);assert (w,h,pitch)==(256,256,512)
  pixels=bytes(u.mem_read(ptr,256*512));src=source(path,name,page);assert len(src)==65536
  expected=struct.pack('<65536H',*((((c&31)<<10)|(c&992)|((c>>10)&31)|(0x8000 if c else 0)) for c in src))
  assert pixels==expected,f'{language}:{name}[{page}] native conversion mismatch'
  results.append({'language':language,'page':f'{name}[{page}]','opaque_texels':sum(1 for c in src if c),'pixels_match':True});print('PASS',results[-1])
 call('KeyMapTestUploadPage',len(pages));assert u.reg_read(UC_X86_REG_EAX)==0
 return results
call('KeyMapTestInit',0x400000)
pages_en=[('atlas.h','atlas_pixels',0)]+[('room_labels.h','room_label_pixels',k) for k in range(ROOM_PAGES)]+[('item_labels.h','item_label_pixels',k) for k in range(ITEM_PAGES)]+[('overlay_icons.h','overlay_icon_pixels',0)]
results=verify_pages(pages_en,'English')
call('KeyMapTestToggle',0,0);call('KeyMapTestToggle',0,32);assert call('KeyMapTestLanguage')==0
ko=Path('korean-assets')
KR=int(re.search(r'ROOM_LABEL_PAGE_COUNT (\d+)',(R/ko/'room_labels.h').read_text())[1])
KI=int(re.search(r'ITEM_LABEL_PAGE_COUNT (\d+)',(R/ko/'item_labels.h').read_text())[1])
pages_ko=[('atlas.h','atlas_pixels',0)]+[(ko/'room_labels.h','room_label_pixels',k) for k in range(KR)]+[(ko/'item_labels.h','item_label_pixels',k) for k in range(KI)]+[('overlay_icons.h','overlay_icon_pixels',0)]
results+=verify_pages(pages_ko,'Korean')
(R/'texture-upload-test-v6.2.json').write_text(json.dumps({'passed':True,'revision':'6.4-bilingual-documents','native_texture_allocator_and_pixel_copy':True,'gpu_tested':False,'size':[256,256],'pitch':512,'pages':results},indent=1))
print('PASS native texture upload CPU path, all English/Korean pages')
