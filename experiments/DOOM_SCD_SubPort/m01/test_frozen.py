#!/usr/bin/env python3
"""24 frozen spawn frames through native state and the CD proxy renderer.
Numerical timing comparison, no requirement for identical gameplay trajectories.
"""
import json,os,struct,sys
from pathlib import Path
from r64a_rsp_capture import RSP,symbols
rom,elf=map(Path,sys.argv[1:]);syms=symbols(elf)
def sym(n):
    vals=[v for k,v in syms.items() if k==n or k.startswith(n+'.')]
    assert len(vals)==1,(n,vals)
    return vals[0]&0xffffff
reports={}
for mode,name in ((1,'native'),(2,'cd'),(3,'native_legacy_text'),(4,'cd_legacy_text')):
    g=RSP(os.environ['BLASTEM'],rom,16000,600)
    try:
        g.req('qSupported')
        for n in ('s1b_complete','S2F_M0FrameDone','I_Error'):assert g.req('Z0,%x,2'%sym(n))=='OK'
        rows=[]
        for _ in range(25):
            g.cont();pc=int(g.req('g')[136:144],16)&0xffffff
            if pc==sym('s1b_complete'):
                assert g.req('M%x,1:%02x'%(sym('s2d_test_exit'),mode<<4))=='OK'
                assert g.req('z0,%x,2'%pc)=='OK';continue
            assert pc==sym('S2F_M0FrameDone'),('benchmark failed',name,hex(pc))
            row=list(struct.unpack('>7I',g.readmem(0x61b1c0,28)))
            assert row[0]==len(rows);rows.append(row)
        assert len(rows)==24
        reports[name]={'frames':24,'raster_stopwatch_units':sum(r[1] for r in rows),'conversion_stopwatch_units':sum(r[2] for r in rows),'extra_wait_stopwatch_units':sum(r[3] for r in rows),'total_stopwatch_units':sum(r[4] for r in rows),'dma_stopwatch_units':sum(r[5] for r in rows),'text_stopwatch_units':sum(r[6] for r in rows),'rows':rows}
        print('M0 frozen',name,reports[name],flush=True)
    finally:g.close()
reports['cd_over_native']=reports['cd']['total_stopwatch_units']/reports['native']['total_stopwatch_units']
(rom.parent/'m0_frozen_report.json').write_text(json.dumps(reports,indent=2))
print('M0 24 frozen frames measured; CD/native cost ratio',reports['cd_over_native'],flush=True)
