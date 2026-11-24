"""Conservative render-only geometry reduction, preserving the Doom source WAD and BSP."""

def reduce_segments(rows, subsectors, verts, sectors, lines, sides, mode="control"):
    assert mode in ("control","safe","merge")
    protected={i for i,s in enumerate(sectors) if s[5] or s[6]}
    adjacent=[set() for _ in sectors]
    for line in lines:
        ends={sides[sd][5] for sd in line[5:7] if sd!=65535}
        for a in ends:adjacent[a].update(ends-{a})
        if line[3]:protected.update(ends)
    pending=list(protected)
    while pending:
        a=pending.pop()
        for b in adjacent[a]:
            if b not in protected and sectors[a][2]==sectors[b][2]:
                protected.add(b);pending.append(b)
    protected|={b for a in tuple(protected) for b in adjacent[a]}
    result=[];ranges=[];removed=0;merged=0
    def invisible(r):
        fs,bs=r[2:4]
        if bs==65535 or r[4]!=255 or lines[r[10]][3]:return False
        if fs==bs:return True
        return (fs not in protected and bs not in protected and sectors[fs][:6]==sectors[bs][:6])
    def join(a,b):
        if a[1]!=b[0] or a[2:8]!=b[2:8] or a[9:11]!=b[9:11]:return None
        if lines[a[10]][3] or a[8]+a[11]!=b[8]:return None
        x,y=verts[a[0]];u,v=verts[a[1]];q,t=verts[b[1]]
        if (u-x)*(t-v)!=(v-y)*(q-u) or (u-x)*(q-u)+(v-y)*(t-v)<=0:return None
        import math
        length=round(math.hypot(q-x,t-y))
        if length!=a[11]+b[11]:return None
        return (a[0],b[1],*a[2:11],length)
    for count,first in subsectors:
        leaf=[]
        for r in rows[first:first+count]:
            if mode!="control" and invisible(r):
                removed+=1
                continue
            j=join(leaf[-1],r) if mode=="merge" and leaf else None
            if j is None:leaf.append(r)
            else:leaf[-1]=j;merged+=1
        if not leaf and count:leaf=[rows[first]]   # an empty leaf would have no PVS portals and could not be drawn
        ranges.append((len(leaf),len(result)));result.extend(leaf)
    assert sum(n for n,_ in ranges)==len(result)
    return result,ranges,dict(mode=mode,before=len(rows),after=len(result),
         removed_invisible=removed,merged_collinear=merged,
         reduction_percent=round(100*(len(rows)-len(result))/max(1,len(rows)),2),
         protected_sectors=len(protected),collision_changed=False,
         visual_validation="pending emulator and hardware comparison")

def simplify_steps(sectors,lines,sides,max_step=16):
    """GEO_STEPS ONLY: changes floor heights, so collision/gameplay may change."""
    original=[list(s) for s in sectors]
    neighbors=[set() for _ in sectors];special=set()
    for l in lines:
        ends={sides[sd][5] for sd in l[5:7] if sd!=65535}
        if l[3] or l[4]:special.update(ends)
        for a in ends:neighbors[a].update(ends-{a})
    blocked=special|{i for i,s in enumerate(sectors) if s[5] or s[6]}
    blocked|={b for a in tuple(blocked) for b in neighbors[a]}
    locked=set();changes=[]
    def valid(a,h,other):
        if sectors[a][1]-h<56:return False
        return all(not(abs(h-sectors[n][0])>24 and abs(sectors[a][0]-sectors[n][0])<=24)
                   for n in neighbors[a] if n!=other)
    for l in lines:
        if l[3] or l[4] or not l[2]&4 or 65535 in l[5:7]:continue
        rs,ls=sides[l[5]],sides[l[6]];a,b=rs[5],ls[5]
        if a==b or a in blocked|locked or b in blocked|locked:continue
        if rs[4]!='-' or ls[4]!='-':continue
        A,B=sectors[a],sectors[b]
        if A[1:]!=B[1:]:continue
        delta=abs(A[0]-B[0])
        if not 0<delta<=max_step:continue
        h=max(A[0],B[0]) if delta<=8 else min(A[0],B[0])+delta//2
        if not valid(a,h,b) or not valid(b,h,a):continue
        changes.append({"sectors":[a,b],"old":[A[0],B[0]],"new":h})
        sectors[a][0]=sectors[b][0]=h
        locked|={a,b}|neighbors[a]|neighbors[b]
    for i,s in enumerate(sectors):
        assert s[1:]==original[i][1:]
        assert abs(s[0]-original[i][0])<=8
    return changes


def merge_steps(sectors,lines,sides,max_step=24,min_clear=56,merge_flats=False):
    """GEO_STEPS ONLY (changes collision). Merge sectors that differ only by a small floor step into one floor height.

    Rules (exact integer height arithmetic, Doom map units):
      * a pair/group is merged only when every other field matches (ceiling, flats, light, special, tag) and neither the
        sectors nor their lines have a tag/special (doors, lifts, switches stay exact);
      * the merged group spans at most max_step (the 24-unit step height the player can climb);
      * the new floor is the midpoint of the group's extremes, and every member keeps >= min_clear headroom;
      * for every neighbouring sector outside the group, a step that was climbable (<=24) stays climbable and a wall
        (>24) stays a wall, so no route opens or closes."""
    n=len(sectors)
    touch=[set() for _ in range(n)];protected=set()
    for l in lines:
        ends=[sides[sd][5] for sd in l[5:7] if sd!=65535]
        for a in ends:touch[a].update(e for e in ends if e!=a)
        if l[3] or l[4]:protected.update(ends)
    for i,s in enumerate(sectors):
        if s[5] or s[6] or s[1]-s[0]<min_clear:protected.add(i)
    edges=[]
    for l in lines:
        if not l[2]&4 or 65535 in l[5:7]:continue
        rs,ls=sides[l[5]],sides[l[6]];a,b=rs[5],ls[5]
        if a==b or a in protected or b in protected:continue
        if rs[4]!='-' or ls[4]!='-':continue
        A,B=sectors[a],sectors[b]
        same=(A[1:]==B[1:]) if not merge_flats else (A[1]==B[1] and A[3:]==B[3:])
        if not same:continue
        d=abs(A[0]-B[0])
        if 0<d<=max_step:edges.append((d,a,b))
    edges.sort()
    parent=list(range(n));members={i:[i] for i in range(n)}
    floor0=[s[0] for s in sectors];cur=list(floor0)
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    changes=0
    for d,a,b in edges:
        ra,rb=find(a),find(b)
        if ra==rb:continue
        mem=members[ra]+members[rb]
        lo=min(floor0[m] for m in mem);hi=max(floor0[m] for m in mem)
        if hi-lo>max_step:continue
        h=lo+(hi-lo)//2
        if any(sectors[m][1]-h<min_clear for m in mem):continue
        ms=set(mem);ok=True
        for m in mem:
            for o in touch[m]:
                if o in ms:continue
                old=abs(floor0[m]-cur[o]) if False else abs(cur[m]-cur[o])
                new=abs(h-cur[o])
                if (old<=24)!=(new<=24):ok=False;break
            if not ok:break
        if not ok:continue
        parent[rb]=ra;members[ra]=mem
        for m in mem:cur[m]=h
    out=[]
    if merge_flats:
        from collections import Counter
        for r,mem in members.items():
            if len(mem)>1 and find(r)==r:
                pic=Counter(sectors[m][2] for m in mem).most_common(1)[0][0]
                for m in mem:
                    if sectors[m][2]!=pic:out.append({"sector":m,"floorpic":[sectors[m][2],pic]});sectors[m][2]=pic
    for i in range(n):
        if cur[i]!=floor0[i]:
            sectors[i][0]=cur[i];out.append({"sector":i,"old":floor0[i],"new":cur[i]})
    return out
