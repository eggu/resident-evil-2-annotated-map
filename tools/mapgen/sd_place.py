"""SD room-name layout (user rules 2026-11-12): names outside their room on a leader from an edge midpoint;
straight, any-angle or one-bend leaders; labels slide, keep a 2 px gap, avoid non-enemy marks; fewest-spots first,
one or two lines whichever is closer, as close to the room as the 2 px gap allows; English only gets the refinement pass. Leader and text share one of five colours."""
# SD outside placement (numpy grids): leaders start at room edge midpoints; straight, any-angle or one bend;
# labels slide; spread by a capped crowd penalty; then a refinement pass (single re-place + pair swap).
import math, numpy as np
class Sat:
    """Summed-area table of blocked cells."""
    def __init__(self, cells, shape):
        m = np.zeros(shape, np.int32)
        for x, y in cells:
            m[y, x] = 1
        self.ii = np.pad(m.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        self.h, self.w = shape

    def sum(self, x, y, w, h):
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, self.w), min(y + h, self.h)
        if x1 <= x0 or y1 <= y0:
            return 0
        ii = self.ii
        return int(ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0])


def split(text):
    """Two lines between the words nearest the middle; None for one word."""
    parts = text.split(' ')
    if len(parts) < 2:
        return None
    at = min(range(1, len(parts)), key=lambda i: abs(len(' '.join(parts[:i])) - len(' '.join(parts[i:]))))
    return ' '.join(parts[:at]) + '\n' + ' '.join(parts[at:])

ABBR=[('S.T.A.R.S. Office','STARS Office'),('Second Floor','2F'),('Communications','Comms'),('Emergency','Emerg.'),('Maintenance','Maint.'),('Elevator','Elev.'),
      ('Treatment','Treat.'),('Monitoring','Monitor'),('Basement','Bsmt.'),('Corridor','Corr.'),('Passage','Pass.'),
      ('Storeroom','Store Rm'),('Storage','Stor.'),('Helicopter','Heli'),('Room','Rm')]
def abbr(t):
    for a,b in ABBR:t=t.replace(a,b)
    return t
GAP=2;RF=100;KMAX=200;CROWD_CAP=0   # no spreading (user 2026-11-12: the screen frame can hide far labels; stay next to the room)
OFFS=sorted(((ax,ay) for ax in range(-RF,RF+1) for ay in range(-RF,RF+1) if 9<=ax*ax+ay*ay<=RF*RF and ax and ay),key=lambda v:v[0]*v[0]+v[1]*v[1])
LC=lambda L:L+L*L/160
def raster(p,q):
    (x0,y0),(x1,y1)=p,q;n=max(abs(x1-x0),abs(y1-y0))
    return [(x0+round((x1-x0)*i/n),y0+round((y1-y0)*i/n)) for i in range(1,n+1)] if n else []
def place(rows,size_of,occ,outline,blocked,W,H,edge_mids,refine=True,fixed=(),other=()):
    """fixed: labels already placed on this floor by another pass, as (box, leader cells); other: cells of rooms shown
    on this floor but laid out elsewhere (a leader crossing one counts as crossing a room)."""
    owner=np.full((H+2,W+2),-1,np.int32);keys={r['key']:i for i,r in enumerate(rows)}
    for x,y in other:
        if 0<=x<W and 0<=y<H:owner[y,x]=1<<20
    for c,k in occ.items():
        if 0<=c[0]<W and 0<=c[1]<H:owner[c[1],c[0]]=keys[k]
    ol=np.zeros((H+2,W+2),bool)
    for x,y in outline:
        if 0<=x<W and 0<=y<H:ol[y,x]=True
    used=np.zeros((H+2,W+2),np.int16);lab=np.zeros((H+2,W+2),np.int16);core=np.zeros((H+2,W+2),np.int16);S={};R={r['key']:r for r in rows};starts=[]
    def mark(v,s):
        (_,b,poly,cells),_t=v;x,y,w,h=b
        lab[max(0,y-GAP):y+h+GAP,max(0,x-GAP):x+w+GAP]+=s;core[y:y+h,x:x+w]+=s
        cs=np.asarray(cells).reshape(-1,2);used[cs[:,1],cs[:,0]]+=s
    SB=np.array([[1 if blocked.sum(x,y,1,1) else 0 for x in range(W)] for y in range(H)],np.int32)
    II=[None]
    def refresh():
        g=SB.copy();g|=(lab[:H,:W]>0)
        u=used[:H,:W]>0;d=u.copy();d[1:]|=u[:-1];d[:-1]|=u[1:];d[:,1:]|=u[:,:-1];d[:,:-1]|=u[:,1:]
        d[1:,1:]|=u[:-1,:-1];d[:-1,:-1]|=u[1:,1:];d[1:,:-1]|=u[:-1,1:];d[:-1,1:]|=u[1:,:-1]
        g|=d;I=np.zeros((H+1,W+1),np.int32);I[1:,1:]=g.cumsum(0).cumsum(1);II[0]=I
    def box_fast(b):
        x,y,w,h=b
        if x<0 or y<0 or x+w>W or y+h>H:return False
        I=II[0];return I[y+h,x+w]-I[y,x+w]-I[y+h,x]+I[y,x]==0
    bstat={}
    def box_free(b):
        x,y,w,h=b
        if b not in bstat:bstat[b]=not(x<0 or y<0 or x+w>W or y+h>H or blocked.sum(x,y,w,h))
        if not bstat[b]:return False
        if lab[y:y+h,x:x+w].any():return False
        return not used[max(0,y-1):y+h+1,max(0,x-1):x+w+1].any()
    cache={}
    def path(sx,sy,pts):
        key=None
        if True:
            cells=[];prev=(sx,sy)
            for p in pts:cells+=raster(prev,p);prev=p
            a=np.array(cells) if cells else np.zeros((0,2),int)
            ok=(a[:,0]>=0).all() and (a[:,1]>=0).all() and (a[:,0]<W).all() and (a[:,1]<H).all()
            if ok:
                o=ol[a[:,1],a[:,0]].astype(int);run=np.convolve(o,np.ones(3,int),'valid')
                ok=not (run>=3).any()
            return (cells,a,ok)
    def path_ok(a,own,cross):
        if not cross:
            ow=owner[a[:,1],a[:,0]]
            if ((ow>=0)&(ow!=own)).any():return False
        return not used[a[:,1],a[:,0]].any() and not lab[a[:,1],a[:,0]].any()
    def dyn_ok(a,relax=False):
        return not used[a[:,1],a[:,0]].any() and not (core if relax else lab)[a[:,1],a[:,0]].any()
    stat_cache={}
    def static_cands(sx,sy,dx,dy,own,cross):
        k=(sx,sy,dx,dy,own,cross)
        if k not in stat_cache:
            res=[]
            for pts,d,cost in cands(sx,sy,dx,dy):
                cells,a,ok=path(sx,sy,pts)
                if not ok:continue
                if not cross:
                    ow=owner[a[:,1],a[:,0]]
                    if ((ow>=0)&(ow!=own)).any():continue
                res.append((pts,d,cost,cells,a))
            stat_cache[k]=res
        return stat_cache[k]
    def attach(end,d,lw,lh):
        ex,ey=end;dx,dy=d
        rng=range(-(lw//2)+1,lw//2) if dy else range(-(lh//2)+1,lh//2)
        for sh in sorted(rng,key=abs):
            # 1 px between the leader's end and the name (user 2026-11-12: they touched)
            yield ((ex-lw//2+sh,ey-lh if dy<0 else ey+1,lw,lh) if dy else (ex-lw if dx<0 else ex+1,ey-lh//2+sh,lw,lh)),abs(sh)
    REL={}
    def rel(dx,dy):
        if (dx,dy) not in REL:
            perp=[(dy,dx),(-dy,-dx)]
            c=[(((dx*L,dy*L),),(dx,dy),LC(L)) for L in range(3,KMAX)]
            c+=[(((dx*a,dy*a),(dx*a+px*b,dy*a+py*b)),(px,py),LC(a+b)+4) for px,py in perp for a in range(3,30,2) for b in range(3,KMAX-a)]
            c+=[(((ax,ay),),((1 if ax>0 else -1,0) if abs(ax)>=abs(ay) else (0,1 if ay>0 else -1)),LC(math.hypot(ax,ay))+1) for ax,ay in OFFS if ax*dx+ay*dy>0.35*math.hypot(ax,ay)]
            c.sort(key=lambda t:t[2]);REL[(dx,dy)]=c
        return REL[(dx,dy)]
    RC={}
    def relcells(dx,dy,i,rp):
        k=(dx,dy,i)
        if k not in RC:
            c=[];prev=(0,0)
            for p in rp:c+=raster(prev,p);prev=p
            RC[k]=np.array(c,np.int32).reshape(-1,2)
        return RC[k]
    smemo={}
    def static_iter(sx,sy,dx,dy,own,cross):
        # Valid candidates are kept compact per start; failures are skipped once and never revisited.
        k=(sx,sy,dx,dy,own,cross)
        st=smemo.get(k)
        if st is None:st=smemo[k]=[[],0]
        R_=rel(dx,dy);i=0
        while True:
            if i<len(st[0]):yield st[0][i];i+=1;continue
            if st[1]>=len(R_):return
            rp,d,cost=R_[st[1]];st[1]+=1
            pts=tuple((sx+x,sy+y) for x,y in rp);ra=relcells(dx,dy,st[1]-1,rp);a=ra+(sx,sy)
            ok=(a[:,0]>=0).all() and (a[:,1]>=0).all() and (a[:,0]<W).all() and (a[:,1]<H).all()
            if ok:
                o=(ol[a[:,1],a[:,0]]&(owner[a[:,1],a[:,0]]!=own)).astype(np.int8)   # its own outline may be crossed (leaders start inside)
                ok=not (len(o)>=3 and (o[:-2]&o[1:-1]&o[2:]).any())
            cells=a
            if ok and not cross:
                ow=owner[a[:,1],a[:,0]];ok=not ((ow>=0)&(ow!=own)).any()
            if ok:st[0].append((pts,d,cost,cells,a))
    cands_cache={}
    def cands(sx,sy,dx,dy):
        k=(sx,sy,dx,dy)
        if k not in cands_cache:
            perp=[(dy,dx),(-dy,-dx)]
            c=[(((sx+dx*L,sy+dy*L),),(dx,dy),LC(L)) for L in range(3,KMAX)]
            c+=[(((sx+dx*a,sy+dy*a),(sx+dx*a+px*b,sy+dy*a+py*b)),(px,py),LC(a+b)+4) for px,py in perp for a in range(3,30,2) for b in range(3,KMAX-a)]
            c+=[(((sx+ax,sy+ay),),((1 if ax>0 else -1,0) if abs(ax)>=abs(ay) else (0,1 if ay>0 else -1)),LC(math.hypot(ax,ay))+1) for ax,ay in OFFS if ax*dx+ay*dy>0.35*math.hypot(ax,ay)]
            c.sort(key=lambda t:t[2]);cands_cache[k]=c
        return cands_cache[k]
    def crowd(b):
        return min(CROWD_CAP,sum(max(0,24-max(a-(b[0]+b[2]),b[0]-(a+c),bb-(b[1]+b[3]),b[1]-(bb+d)))*2.0 for (_,(a,bb,c,d),_,_),_t in [v for v in S.values() if v]))
    def search(r,relax=False):
        refresh();own=keys[r['key']];pick=None
        texts=[r['name']]+([split(r['name'])] if ' ' in r['name'] else [])
        for text in texts:
            lw,lh=size_of(text);best=None
            for cross in (0,1):
                for (sx,sy),(dx,dy) in edge_mids(r['cells']):
                    if not relax and any(abs(sx-a)+abs(sy-b)<4 for a,b in starts):continue
                    for pts,d,cost,cells,a in static_iter(sx,sy,dx,dy,own,cross):
                        cost=cost+cross*40
                        if best and cost>=best[0]:break
                        if not dyn_ok(a,relax):continue
                        for b,sh in attach(pts[-1],d,lw,lh):
                            if best and cost+sh*.2>=best[0]:break
                            if box_fast(b):
                                t=cost+sh*.2+crowd(b)
                                if not best or t<best[0]:best=(t,b,[(sx,sy)]+list(pts),cells)
                                break
                if best:break
            if best and (not pick or best[0]<pick[0][0]):pick=(best,text)
        if not pick and not relax:return search(r,True)
        return pick
    def put(k,v):
        if S.get(k):mark(S[k],-1)
        S[k]=v
        if v:mark(v,1);starts.append(v[0][2][0])
    def take(k):
        v=S.get(k)
        if v:mark(v,-1);starts.remove(v[0][2][0])
        S[k]=None;return v
    def nspots(r):
        lw,lh=size_of(r['name']);n=0
        for (sx,sy),(dx,dy) in edge_mids(r['cells']):
            for L in range(3,60,3):
                cells,a,ok=path(sx,sy,((sx+dx*L,sy+dy*L),))
                if not ok or not path_ok(a,keys[r['key']],0):break
                n+=sum(1 for i,(b,_) in enumerate(attach((sx+dx*L,sy+dy*L),(dx,dy),lw,lh)) if i%4==0 and box_free(b))
        return n
    cost=lambda k:S[k][0][0] if S.get(k) else 999
    for b,cells in fixed:   # earlier passes: never covered, never crossed
        x,y,w,h=b;lab[max(0,y-GAP):y+h+GAP,max(0,x-GAP):x+w+GAP]+=1;core[y:y+h,x:x+w]+=1
        cs=np.asarray(cells).reshape(-1,2)
        if len(cs):used[cs[:,1],cs[:,0]]+=1
    for r in sorted(rows,key=nspots):put(r['key'],search(r))
    for _ in range(2 if refine else 0):
        for k in sorted(S,key=cost,reverse=True):
            old=take(k);p=search(R[k])
            put(k,p if p and (not old or p[0][0]<old[0][0]-1) else old)
    for k in (sorted(S,key=cost,reverse=True) if refine else []):
        if cost(k)<25 or not S[k]:continue
        cs=R[k]['cells'];x0=min(c[0] for c in cs)-40;x1=max(c[0] for c in cs)+40;y0=min(c[1] for c in cs)-40;y1=max(c[1] for c in cs)+40
        for n in [n for n in S if n!=k and S[n] and not(S[n][0][1][0]>x1 or S[n][0][1][0]+S[n][0][1][2]<x0 or S[n][0][1][1]>y1 or S[n][0][1][1]+S[n][0][1][3]<y0)]:
            ck=cost(k);before=ck+cost(n);ok_,on=take(k),take(n);pa=search(R[k])
            if pa:
                put(k,pa);pb=search(R[n])
                if pb and pa[0][0]+pb[0][0]<before-2:put(n,pb);continue
                take(k)
            put(k,ok_);put(n,on)
    out={}
    for r in rows:
        v=S.get(r['key'])
        if v:
            (_,b,poly,_c),text=v;out[r['key']]=dict(text=text,x=b[0]+b[2]/2,y=b[1]+b[3]/2,poly=poly,box=b,cells=list(_c))
        else:
            cs=sorted(r['cells']);out[r['key']]=dict(text=r['name'],x=sum(c[0] for c in cs)/len(cs),y=sum(c[1] for c in cs)/len(cs),poly=None,forced=True)
    return out
PAL=[(255,240,200),(120,220,255),(255,150,200),(170,240,110),(255,180,80)]
def colour(out):
    from collections import Counter
    cnt=Counter();done=[]
    def bb(o):
        pts=(o.get('poly') or [])+[(o['x'],o['y'])];return min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)
    for k,o in sorted(out.items(),key=lambda t:(t[1]['y'],t[1]['x'])):
        a=bb(o);near={c for b,c in done if not(a[2]+30<b[0] or b[2]+30<a[0] or a[3]+20<b[1] or b[3]+20<a[1])}
        ok=[c for c in PAL if c not in near] or PAL
        o['col']=min(ok,key=lambda c:(cnt[c],PAL.index(c)));cnt[o['col']]+=1;done.append((a,o['col']))
