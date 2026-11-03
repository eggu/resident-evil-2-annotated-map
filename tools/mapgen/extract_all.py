from pathlib import Path
import os,re,struct,json,collections
R=Path(__file__).resolve().parent
G=Path(os.environ['RE2_GAME'])
sizes=json.loads((R/'opcode-sizes.json').read_text())['sizes']
a=[]
for pl in (0,1):
 for p in sorted((G/f'Pl{pl}/Rdt').glob('*.RDT')):
  b=p.read_bytes();offs=struct.unpack_from('<23I',b,8)
  event_aots=[]
  for idx in (16,17):
   st=offs[idx]
   if not st:continue
   end=min([x for x in offs if x>st] or [len(b)]);first=struct.unpack_from('<H',b,st)[0]
   if not 0<first<end-st or first%2:continue
   funcs=[st+x for x in struct.unpack_from('<'+'H'*(first//2),b,st)]+[end]
   parsed={}
   for fn in range(len(funcs)-1):
    parsed[fn]=[]
    pos=funcs[fn]
    while pos<funcs[fn+1]:
     op=b[pos];sz=sizes[op] if op<len(sizes) else 0
     if not sz or pos+sz>funcs[fn+1]:break
     q=b[pos:pos+sz];parsed[fn].append((op,q,pos))
     if op==59 and q[2]==1 and q[29]>=128 and q[30] not in (0,254,255):
      a.append(dict(pl=pl,room=p.name,offset=pos,key_id=q[29],item=q[30],kind='door',raw=q.hex()))
     if op==44 and q[2]==13:
      a.append(dict(pl=pl,room=p.name,offset=pos,key_id=struct.unpack_from('<H',q,12)[0],item=48 if pl else 31,kind='drawer',raw=q.hex(),aot_id=struct.unpack_from('<H',q,16)[0]))
     if op==44 and q[2]==5 and q[16]==24:event_aots.append((pos,q))
     pos+=sz
   # Scripted key uses are reachable from their map interaction trigger.
   def reach(fn,seen=None):
    seen=set() if seen is None else seen
    if fn in seen:return []
    seen.add(fn);ops=list(parsed.get(fn,[]))
    for op,q,_ in list(ops):
     if op==24:ops+=reach(q[1],seen)
    return ops
   if idx==17:
    for pos,q in event_aots:
     ops=reach(q[17]);extra={('503',8 if pl else 9):94,('504',3):93}.get((p.name[4:7],q[17]))
     if extra:ops=[v for fn_ops in parsed.values() for v in fn_ops]
     items={v[1][1] for v in ops if v[0]==98 and v[1][1] in (63,83,93,94)}
     if extra:items={extra}
     for item in items:
      done={63:159,83:175,93:101,94:98}[item]
      assert any(op==34 and v[1:]==bytes([4,done,1]) for op,v,_ in ops),(p,item)
      a.append(dict(pl=pl,room=p.name,offset=pos,key_id=done,item=item,kind='event',raw=q.hex(),bank=4))
(R/'all-locks.json').write_text(json.dumps(a,indent=2));print(collections.Counter((x['pl'],x['kind'],x['item']) for x in a));print([x for x in a if x['kind']=='drawer'])
