"""Build 128-byte spatial pages, a local directory and a compact mutable overlay."""
from pathlib import Path
import struct,json

def apply(lumps,mode,edit,mutable,side_rows):
    by_name={name:data for name,data in lumps if data}
    segs=[by_name['SEGS'][i:i+32] for i in range(0,len(by_name['SEGS']),32)]
    native_nodes=bytearray()
    for offset in range(0,len(by_name['NODES']),28):
        raw=by_name['NODES'][offset:offset+28]
        x,y,dx,dy=struct.unpack_from('>4h',raw)
        kind=0 if dx==0 else (1 if dy==0 else 2)
        le=(dy>0) if kind==0 else ((dx<0) if kind==1 else False)
        gt=(dy<0) if kind==0 else ((dx>0) if kind==1 else False)
        native_nodes.extend(raw+struct.pack('>HBB',kind,le,gt))
    edit('src/doomdata.h','  uint16_t children[2];\n} mapnode_t;',
         '  uint16_t children[2];\n  uint16_t chunk_kind;\n  uint8_t chunk_le,chunk_gt;\n} mapnode_t;')
    edit('src/doomdata.h','assertMapnodeSize[sizeof(mapnode_t) == 28','assertMapnodeSize[sizeof(mapnode_t) == 32')
    edit('src/r_draw.c', '''\tif (!node->dx)
\t\treturn ix <= node->x ? node->dy > 0 : node->dy < 0;''',
         '''    if(node->chunk_kind==0u)
        return ix<=node->x ? node->chunk_le : node->chunk_gt;''')
    edit('src/r_draw.c', '''\tif (!node->dy)
\t\treturn iy <= node->y ? node->dx < 0 : node->dx > 0;''',
         '''    if(node->chunk_kind==1u)
        return iy<=node->y ? node->chunk_le : node->chunk_gt;''')

    leaves=list(struct.iter_unpack('>HH',by_name['SSECTORS']))
    slots={side:i+1 for i,side in enumerate(sorted(mutable))}
    maplines=[struct.unpack_from('>hhhhHhhHHhhhhhBbb',by_name['LINEDEFS'],i)
              for i in range(0,len(by_name['LINEDEFS']),32)]
    sectors=list(struct.iter_unpack('>hhhhBbh',by_name['SECTORS']))
    dynamic_sectors={i for i,sec in enumerate(sectors) if sec[5] or sec[6]}
    for line in maplines:
        if line[13] or line[16]:
            dynamic_sectors.update(side_rows[side][5] for side in line[7:9] if side!=65535)
    fixed_flags=[]
    for raw in segs:
        line=maplines[struct.unpack_from('>H',raw,14)[0]]
        front,back=raw[16:18]
        side=struct.unpack_from('>H',raw,12)[0]
        top,bottom,mid=side_rows[side][2:5]
        if not line[14]&4: flag=16
        elif front in dynamic_sectors or back in dynamic_sectors or side in mutable: flag=255
        else:
            a,b=sectors[front],sectors[back]
            # Converted flat IDs use -2 for sky. Mirror R_RecalcLineFlags.
            closed=(b[1]<=a[0] or b[0]>=a[1] or
                    (b[1]<=b[0] and (b[1]>=a[1] or top) and
                     (b[0]<=a[0] or bottom) and (b[3]!=-2 or a[3]!=-2)))
            flag=16 if closed else (8 if a[:5]==b[:5] and not mid else 0)
        fixed_flags.append(flag)
    pages=[]
    directory=[]
    # A page contains a 16-byte header, three 32-byte records, and 16 spare bytes.
    # The directory resolves the first page and sector offline.
    for count,first in leaves:
        assert count and first+count<=len(segs)
        first_page=len(pages)
        sector=segs[first][16]
        for start in range(0,count,3):
            records=[]
            for raw in segs[first+start:first+min(start+3,count)]:
                raw=bytearray(raw)
                side=struct.unpack_from('>H',raw,12)[0]
                raw[24]=slots.get(side,0)
                original_index=first+start+len(records)
                raw[26]=fixed_flags[original_index]
                records.append(bytes(raw))
            points=[maplines[struct.unpack_from('>H',r,14)[0]][:4] for r in records]
            xs=[x for p in points for x in (p[0],p[2])]
            ys=[y for p in points for y in (p[1],p[3])]
            next_page=len(pages)+1 if start+3<count else 65535
            header=struct.pack('>4H4h',next_page,len(records),sector,0,min(xs),max(xs),min(ys),max(ys))
            page=header+b''.join(records)+bytes(32*(3-len(records))+16)
            assert len(page)==128
            pages.append(page)
        directory.append((first_page,sector,count,len(pages)-first_page))
    assert len(pages)<65535
    def emit(values):
        return '{'+','.join(str(v) for v in values)+'}'
    header=['#ifndef RCHUNK_DATA_H','#define RCHUNK_DATA_H','#include "r_defs.h"',
        'typedef struct { uint16_t first,sector,count,pages; } RChunkLeaf;',
        'typedef struct { uint16_t next,count,sector,flags; int16_t xmin,xmax,ymin,ymax; seg_t segs[3]; uint8_t spare[16]; } RChunkPage;',
        'typedef char RChunkSizeCheck[(sizeof(RChunkPage)==128)?1:-1];',
        f'extern const RChunkLeaf rchunk_leaves[{len(directory)}];',
        f'extern const RChunkPage rchunk_pages[{len(pages)}];',
        '#define RCHUNK_PAGES rchunk_pages','#endif']
    Path('src/rchunk_data.h').write_text('\n'.join(header)+'\n')
    def seg_initializer(raw):
        values=struct.unpack('>hhhhhHHHBBhbbbBBB6B',raw)
        return '{'+emit(values[:2])+','+emit(values[2:4])+','+','.join(map(str,values[4:17]))+','+emit(values[17:])+'}'
    definitions=['#include "rchunk_data.h"',
        'const RChunkLeaf rchunk_leaves[]={'+','.join(emit(d) for d in directory)+'};',
        'const RChunkPage rchunk_pages[] __attribute__((aligned(128)))={']
    for page in pages:
        prefix=','.join(map(str,struct.unpack('>4H4h',page[:16])))
        records=','.join(seg_initializer(page[16+i*32:48+i*32]) for i in range(3))
        definitions.append('{'+prefix+',{'+records+'},{0}},')
    definitions.append('};')
    Path('src/rchunk_data.c').write_text('\n'.join(definitions)+'\n')
    # A byte-coded table is the only side-token -> mutable-slot translation.
    # Every write updates the small RAM overlay, including initial loading.
    state_header=['#ifndef RCHUNK_STATE_H','#define RCHUNK_STATE_H',
                  'uint8_t RChunk_WriteSide(const void *,uint16_t,uint16_t,uint32_t);',
                  'const uint8_t *RChunk_SideBytes(const void *,uint16_t,uint16_t);',
                  'void RChunk_ReadSide(uint16_t,side_t *);','#endif']
    Path('src/rchunk_state.h').write_text('\n'.join(state_header)+'\n')
    state='''#include <stdint.h>
#include <stddef.h>
#include "r_defs.h"
#include "rchunk_state.h"
typedef struct { uint8_t bytes[6]; } RChunkSide;
static RChunkSide rchunk_sides[COUNT];
static const uint8_t rchunk_slots[]={SLOTS};
const uint8_t *RChunk_SideBytes(const void *side,uint16_t offset,uint16_t size){
    uintptr_t token=(uintptr_t)side;
    if(token<0x220000UL || token>=0x220000UL+16u*SIDECOUNT)return NULL;
    uint16_t slot=rchunk_slots[(token-0x220000UL)>>4];
    if(!slot || offset<4u || offset+size>9u)return NULL;
    return rchunk_sides[slot-1u].bytes+offset-4u;
}
uint8_t RChunk_WriteSide(const void *side,uint16_t offset,uint16_t size,uint32_t value){
    uint8_t *out=(uint8_t*)RChunk_SideBytes(side,offset,size);
    if(!out)return 0;
    for(uint16_t i=0;i<size;i++)out[i]=(uint8_t)(value>>(8u*(size-1u-i)));
    return 1;
}
void RChunk_ReadSide(uint16_t slot,side_t *out){
    const uint8_t *data=rchunk_sides[slot-1u].bytes;
    out->textureoffset=(int16_t)((uint16_t)data[0]<<8|data[1]);
    out->toptexture=(int8_t)data[2];
    out->bottomtexture=(int8_t)data[3];
    out->midtexture=(int8_t)data[4];
}
'''
    state=state.replace('SIDECOUNT',str(len(side_rows))).replace('COUNT',str(len(slots))).replace('SLOTS',','.join(str(slots.get(i,0)) for i in range(len(side_rows))))
    Path('src/rchunk_state.c').write_text(state)
    edit('src/r23_mapmem.c','uint32_t R23_MapRead(const void *p,uint16_t offset,uint16_t size){',
         '''#include "rchunk_state.h"
uint32_t R23_MapRead(const void *p,uint16_t offset,uint16_t size){
    if((uintptr_t)p>=0x220000UL && (uintptr_t)p<0x230000UL){
        const uint8_t *data=RChunk_SideBytes(p,offset,size);
        if(data){uint32_t value=0;while(size--)value=(value<<8)|*data++;return value;}
    }''')
    edit('src/r23_mapmem.c','void R23_MapWrite(void *p,uint16_t offset,uint16_t size,uint32_t value){',
         '''void R23_MapWrite(void *p,uint16_t offset,uint16_t size,uint32_t value){
    if((uintptr_t)p>=0x220000UL && (uintptr_t)p<0x230000UL &&
       RChunk_WriteSide(p,offset,size,value))return;''')
    edit('src/r23_mapmem.c','void R27_ReadBlock(const void *p,uint16_t offset,uint16_t size,void *out){',
         '''void R27_ReadBlock(const void *p,uint16_t offset,uint16_t size,void *out){
    if((uintptr_t)p>=0x220000UL && (uintptr_t)p<0x230000UL){
        const uint8_t *data=RChunk_SideBytes(p,offset,size);
        if(data){uint8_t *to=out;while(size--)*to++=*data++;return;}
    }''')
    edit('src/r_draw.c','typedef struct { int16_t x; int8_t top,bottom,mid; uint8_t pad,dynamic,row; } rmap_view_t;',
         '#include "rchunk_data.h"\n#include "rchunk_state.h"\nstatic const seg_t *rchunk_saved_seg;\ntypedef struct { int16_t x; int8_t top,bottom,mid; uint8_t pad,dynamic,row; } rmap_view_t;')
    # Static closure/ignore decisions come from offline sector analysis.
    # Dynamic doors, lifts, lights and switches retain the live classifier.
    edit('src/r_draw.c','    const uint16_t line_flags=R27_OrFlags(linedef,ML_MAPPED);',
         '''    uint16_t line_flags=R27_OrFlags(linedef,ML_MAPPED);
    if(curline->prepared_reserved[0]!=255u)
        line_flags=(line_flags&ML_MAPPED)|curline->prepared_reserved[0];''')
    edit('src/r_draw.c','    uint32_t render_info=R23_MapRead(linedef,offsetof(linedata_t,r_validcount),4);',
         '''    uint16_t prepared_flags=curline->prepared_reserved[0];
    if(prepared_flags!=255u){
        if(!(prepared_flags&RF_IGNORE))R_ClipWallSegment(x1,x2,prepared_flags&RF_CLOSED);
        return;
    }
    uint32_t render_info=R23_MapRead(linedef,offsetof(linedata_t,r_validcount),4);''')
    # A persistent drawseg must point back into ROM, never into the reused page.
    edit('src/r_draw.c','    ds_p->curline = curline;', '    ds_p->curline = rchunk_saved_seg;')
    p=Path('src/r_draw.c');s=p.read_text()
    for pointer in ('sidedef','side'):
        old=f'''    R27_ReadBlock({pointer},offsetof(side_t,textureoffset),
        offsetof(side_t,midtexture)+sizeof(side_snapshot.midtexture)-offsetof(side_t,textureoffset),
        (uint8_t*)&side_snapshot+offsetof(side_t,textureoffset));'''
        assert s.count(old)==1
        s=s.replace(old,'        RChunk_ReadSide(prepared->dynamic,&side_snapshot);')
    p.write_text(s)
    edit('src/r_draw.c', '''    frontsector = SUBSECTOR_SECTOR(sub);
    count = _g_mapsubsectors[num].numsegs;
    line = &_g_segs[_g_mapsubsectors[num].firstseg];''',
         '''    const RChunkLeaf *leaf=&rchunk_leaves[num];
    frontsector = &_g_sectors[leaf->sector];
    count = leaf->count;
    line = NULL;''')
    old='''    while (count--)
    {
        R37_HIT(R37_SEGS);
        R7_VOID(9, R_AddLine(line));
        line++;
        curline = NULL; /* cph 2001/11/18 - must clear curline now we're done with it, so R_LoadColorMap doesn't try using it for other things */
    }'''
    load='const RChunkPage *page=rom;'
    if mode=='chunk128':
        edit('src/r_draw.c','static const seg_t *rchunk_saved_seg;',
             '''static const seg_t *rchunk_saved_seg;
static RChunkPage *rchunk_window;
void RChunk_InitWindow(void){rchunk_window=Z_MallocLevel(128u,NULL);}''')
        load='memcpy(rchunk_window,rom,128u); const RChunkPage *page=rchunk_window;'
        edit('src/p_setup.c','static void P_LoadSegs (int16_t lump)\n{',
             'extern void RChunk_InitWindow(void);\nstatic void P_LoadSegs (int16_t lump)\n{\n    RChunk_InitWindow();')
    new='''    uint16_t page_index=leaf->first;
    while(page_index!=65535u){
        const RChunkPage *rom=&RCHUNK_PAGES[page_index];
        LOAD
        for(uint16_t i=0;i<page->count;i++){
            rchunk_saved_seg=&rom->segs[i];
            R37_HIT(R37_SEGS);
            R7_VOID(9,R_AddLine(&page->segs[i]));
            curline=NULL;
        }
        page_index=page->next;
    }'''.replace('LOAD',load)
    edit('src/r_draw.c',old,new)
    # Sight consumes the same spatial format, directly in ROM. Iterate in the
    # original seg order so the game's crossing/occlusion behavior is retained.
    edit('src/p_sight.c','static boolean P_CrossSubsector(int16_t num)',
         '#include "rchunk_data.h"\nstatic boolean P_CrossSubsector(int16_t num)')
    edit('src/p_sight.c',
         '    const seg_t __far* seg = _g_segs + _g_mapsubsectors[num].firstseg;',
         '''    const RChunkLeaf *leaf=&rchunk_leaves[num];
    uint16_t page_index=leaf->first,local=0;
    const RChunkPage *page=&RCHUNK_PAGES[page_index];
    const seg_t *seg;''')
    edit('src/p_sight.c','''    for (count = _g_mapsubsectors[num].numsegs; --count >= 0; seg++)
    { // check lines''','''    for (count = leaf->count; --count >= 0;)
    { // check lines
        if(local==page->count){page_index=page->next;page=&RCHUNK_PAGES[page_index];local=0;}
        if(local==0u &&
           ((fixed_t)page->xmin*FRACUNIT>los.bbox[BOXRIGHT] ||
            (fixed_t)page->xmax*FRACUNIT<los.bbox[BOXLEFT] ||
            (fixed_t)page->ymin*FRACUNIT>los.bbox[BOXTOP] ||
            (fixed_t)page->ymax*FRACUNIT<los.bbox[BOXBOTTOM])){
            count-=(int16_t)(page->count-1u);local=page->count;continue;
        }
        seg=&page->segs[local++];''')
    # All compiled consumers now resolve geometry using the chunk directory.
    # Keep the empty WAD directory entry to preserve resource IDs.
    lumps=[(n,b'' if n=='SEGS' else bytes(native_nodes) if n=='NODES' and d else d) for n,d in lumps]
    report=dict(format=mode,node_stride=32,predecoded_nodes=len(native_nodes)//32,page_bytes=128,pages=len(pages),page_geometry_bytes=len(pages)*128,
                leaves=len(directory),directory_bytes=len(directory)*8,segments=len(segs),
                mutable_sides=len(slots),preclassified_segments=sum(f!=255 for f in fixed_flags),
                dynamic_sectors=len(dynamic_sectors),dynamic_overlay_bytes=len(slots)*6,
                work_window_bytes=128 if mode=='chunk128' else 0,
                consumers=['render','line_of_sight'],dynamic_sides_storage='RAM',original_seg_payload_bytes=0)
    Path('src/rchunk_report.json').write_text(json.dumps(report,indent=2)+'\n')
    return lumps,report
