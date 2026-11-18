"""Conservative source-cell visibility and render-only simplification.

No point samples: every source rectangle and every expanded target rectangle
must satisfy all half-plane tests before a segment can be rejected.
"""
from pathlib import Path
import struct,json,math,time
import numpy as np

def cross(a,b):return a[0]*b[1]-a[1]*b[0]

def merge(a,b):
    # Same original line/side/sectors and contiguous texture parameterization.
    # Other collinear walls are deliberately retained: offset rounding can differ.
    ax,ay,bx,by,off=struct.unpack_from('>5h',a)
    cx,cy,dx,dy,off2=struct.unpack_from('>5h',b)
    if (bx,by)!=(cx,cy) or a[10:]!=b[10:]:return None
    if cross((bx-ax,by-ay),(dx-cx,dy-cy)):return None
    if (bx-ax)*(dx-cx)+(by-ay)*(dy-cy)<=0:return None
    length=math.hypot(bx-ax,by-ay)
    if abs(length-round(length))>1e-8 or off2!=off+round(length):return None
    return a[:4]+b[4:8]+a[8:]

def emitseg(raw):
    v=struct.unpack('>hhhhhHHHBBhbbbBBB6B',raw)
    group=lambda q:'{'+','.join(map(str,q))+'}'
    return '{'+group(v[:2])+','+group(v[2:4])+','+','.join(map(str,v[4:17]))+','+group(v[17:])+'}'

def apply(lumps,edit,report,pvs,slim):
    started=time.monotonic()
    by={n:d for n,d in lumps if d}
    # Chunk compiler already emitted these records once. Parse its typed source
    # indirectly from the original transformed pages to retain LOS unchanged.
    pages=json.loads(Path('src/rvis_input.json').read_text())
    records=[bytes.fromhex(r) for leaf in pages for r in leaf]
    render=[];directory=[];removed=merged=0
    for leaf in pages:
        output=[]
        for h in leaf:
            raw=bytes.fromhex(h)
            if slim and raw[26]==8:removed+=1;continue
            combined=merge(output[-1],raw) if slim and output else None
            if combined is not None:output[-1]=combined;merged+=1
            else:output.append(raw)
        directory.append((len(render),len(output)));render.extend(output)
    assert render
    # 128-world-unit source grid. Bounds enclose all render geometry; out-of-grid
    # viewpoints disable the table instead of clamping to an unrelated row.
    points=[struct.unpack_from('>4h',r) for r in records]
    xmin=math.floor(min(min(p[0],p[2]) for p in points)/128)*128-128
    ymin=math.floor(min(min(p[1],p[3]) for p in points)/128)*128-128
    xmax=max(max(p[0],p[2]) for p in points)+128
    ymax=max(max(p[1],p[3]) for p in points)+128
    nx=(xmax-xmin)//128+1;ny=(ymax-ymin)//128+1
    rows=[];rowids=[];dedup={};rejected=0
    nbits=len(render)+len(directory);stride=(nbits+7)//8
    occluders=[]
    for pos in range(0,len(by['LINEDEFS']),32):
        line=struct.unpack_from('>hhhhHhhHHhhhhhBbb',by['LINEDEFS'],pos)
        if not line[14]&4 and line[:2]!=line[2:4]:occluders.append(line[:4])
    if pvs:
        bounds=[]
        for r in render:
            ax,ay,bx,by=struct.unpack_from('>4h',r)
            bounds.append((min(ax,bx)-8,max(ax,bx)+8,min(ay,by)-8,max(ay,by)+8))
        boxes=np.array(bounds,dtype=np.float64)
        tx=boxes[:,[0,0,1,1]];ty=boxes[:,[2,3,2,3]]
        for gy in range(ny):
            for gx in range(nx):
                x=xmin+gx*128;y=ymin+gy*128
                sources=((x,y),(x+128,y),(x+128,y+128),(x,y+128))
                hidden=np.zeros(len(render),dtype=bool)
                # Backface rejection valid for the complete source cell.
                for i,r in enumerate(render):
                    ax,ay,bx,by=struct.unpack_from('>4h',r)
                    dx,dy=bx-ax,by-ay
                    if all(dx*(sy-ay)-dy*(sx-ax)>8*math.hypot(dx,dy) for sx,sy in sources):hidden[i]=True
                for ax,ay,bx,by in occluders:
                    dx,dy=bx-ax,by-ay
                    sides=[dx*(sy-ay)-dy*(sx-ax) for sx,sy in sources]
                    margin=8*math.hypot(dx,dy)
                    if min(sides)>margin:sgn=1
                    elif max(sides)<-margin:sgn=-1
                    else:continue
                    shadow=np.all(sgn*(dx*(ty-ay)-dy*(tx-ax)) < -margin,axis=1)
                    if not np.any(shadow & ~hidden):continue
                    for sx,sy in sources:
                        ux,uy=ax-sx,ay-sy;vx,vy=bx-sx,by-sy
                        direction=1 if ux*vy-uy*vx>0 else -1
                        # Strict interiors and expanded targets leave a safety band.
                        shadow &= np.all(direction*(ux*(ty-sy)-uy*(tx-sx))>8*math.hypot(ux,uy),axis=1)
                        shadow &= np.all(direction*((tx-sx)*vy-(ty-sy)*vx)>8*math.hypot(vx,vy),axis=1)
                        if not np.any(shadow & ~hidden):break
                    hidden|=shadow
                visible=~hidden
                leafvisible=[bool(np.any(visible[start:start+count])) for start,count in directory]
                packed=np.packbits(np.concatenate((visible,leafvisible)),bitorder='little').tobytes()
                rejected+=int(np.sum(hidden))
                if packed not in dedup:dedup[packed]=len(rows);rows.append(packed)
                rowids.append(dedup[packed])
    definitions=['#include "rchunk_data.h"',
       'typedef struct {uint16_t first,count;} RVisLeaf;',
       'static const RVisLeaf rvis_leaves[]={'+','.join('{%d,%d}'%d for d in directory)+'};',
       'static const seg_t rvis_segs[]={'+','.join(emitseg(r) for r in render)+'};']
    if pvs:
        definitions+=['static const uint8_t rvis_bits[]={' + ','.join(str(v) for row in rows for v in row)+'};',
          'static const uint16_t rvis_cells[]={'+','.join(map(str,rowids))+'};',
          'static const uint8_t *rvis_row;',
          '''static void RVis_Setup(void){
    int32_t gx=((viewx>>FRACBITS)-(%d))>>7;
    int32_t gy=((viewy>>FRACBITS)-(%d))>>7;
    rvis_row=NULL;
    if(gx>=0 && gy>=0 && gx<%d && gy<%d)
        rvis_row=rvis_bits+(uint32_t)rvis_cells[gy*%d+gx]*%du;
}
static uint8_t RVis_Test(uint16_t bit){return !rvis_row || (rvis_row[bit>>3] & (1u<<(bit&7)));}'''%(xmin,ymin,nx,ny,nx,stride)]
    Path('src/rvis_data.h').write_text('\n'.join(definitions)+'\n')
    edit('src/r_draw.c','#include "rchunk_data.h"','#include "rchunk_data.h"\n#include "rvis_data.h"')
    if pvs:edit('src/r_draw.c','    R_SetupFrame (player);','    R_SetupFrame (player);\n    RVis_Setup();')
    source=Path('src/r_draw.c').read_text()
    start=source.index('    uint16_t page_index=leaf->first;',source.index('static void R_Subsector(int16_t num)'))
    end=source.index('\n}\n',start)
    new=''
    if pvs:new+='    if(!RVis_Test((uint16_t)(%du+num)))return;\n'%len(render)
    new+='''    const RVisLeaf *geometry=&rvis_leaves[num];
    uint16_t stop=geometry->first+geometry->count;
    for(uint16_t index=geometry->first;index<stop;index++){
'''
    if pvs:new+='        if(!RVis_Test(index))continue;\n'
    new+='''        const seg_t *seg=&rvis_segs[index];
        rchunk_saved_seg=seg;
        R37_HIT(R37_SEGS);
        R7_VOID(9,R_AddLine(seg));
        curline=NULL;
    }'''
    edit('src/r_draw.c',source[start:end],new)
    report.update(render_segments=len(render),render_ignored_removed=removed,render_collinear_merges=merged,
        pvs_enabled=pvs,slim_enabled=slim,pvs_cells=nx*ny if pvs else 0,pvs_unique_rows=len(rows),
        pvs_bytes=len(rows)*stride+len(rowids)*2,pvs_rejected_fraction=rejected/(nx*ny*len(render)) if pvs else 0,
        pvs_source_cell_units=128,pvs_target_safety_units=8,pvs_occluders=len(occluders),
        pvs_build_seconds=round(time.monotonic()-started,3),pvs_consumers=['render_geometry'],
        pvs_sprites='original BSP visits preserved',render_geometry_bytes=len(render)*32+len(directory)*4)
    Path('src/rvis_input.json').unlink()
    return report
