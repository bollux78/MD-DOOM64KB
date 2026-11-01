#!/usr/bin/env python3
"""Exercise each ORIGINAL R39f LUT on the PERF twin; inspect real tile-word output."""
import argparse,importlib.util,json,pathlib

def module():
    p=pathlib.Path(__file__).with_name('r64a_rsp_capture.py')
    s=importlib.util.spec_from_file_location('rsp',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def symbol(s,name):
    if name in s:return s[name]
    a=[v for k,v in s.items() if k.startswith(name+'.')];assert len(a)==1,(name,a);return a[0]

ap=argparse.ArgumentParser();ap.add_argument('--blastem',required=True);ap.add_argument('--rom',required=True)
ap.add_argument('--elf',required=True);ap.add_argument('--out',required=True);ap.add_argument('--max-emulated-frames',type=int,default=7000)
a=ap.parse_args();assert 1<=a.max_emulated_frames<=10000
rsp=module();s=rsp.symbols(a.elf);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);summaries=[]
for mode,name,mt,ct in ((0,'Off','r39d_colormap_cells_solid','r39d_colorcell_solid'),
                       (1,'Checker','doom_colormap_cells','r39d_colorcell_checker'),
                       (2,'Vertical','r39f_colormap_cells_vertical','r39f_colorcell_vertical')):
    g=rsp.RSP(a.blastem,a.rom,a.max_emulated_frames,600)
    rows=[];seen=set();palettes=set();status='break_limit';armed=False
    try:
        g.req('qSupported')
        begin=symbol(s,'R39M_BeginScene')&0xffffff
        error_pc=s.get('I_Error',0)&0xffffff
        if error_pc:assert g.req('Z0,%x,2'%error_pc)=='OK'
        def check_error():
            regs=g.req('g');pc=int(regs[17*8:18*8],16)&0xffffff
            if error_pc and pc==error_pc:
                sp=int(regs[15*8:16*8],16)&0xffffff
                stack=g.readmem(sp,32);msg_ptr=int.from_bytes(stack[4:8],'big')&0xffffff
                try:msg=g.readmem(msg_ptr,160).split(b'\0')[0].decode(errors='replace')
                except Exception:msg='unreadable'
                raise RuntimeError('ROM I_Error: '+msg+' stack='+stack.hex())
        # Startup progress printing also calls I_FinishUpdate with gametic=0.
        # Wait for the actual renderer before changing mode or counting frames.
        assert g.req('Z0,%x,2'%begin)=='OK'
        g.cont()
        check_error()
        print('First real scene',name,'tic',int.from_bytes(g.readmem(symbol(s,'_g_gametic'),4),'big'),flush=True)
        assert g.req('z0,%x,2'%begin)=='OK'
        for sym,value,size in (('r39f_dither_mode',mode,2),('r39d_active_colormap',symbol(s,mt),4),('colorcell',symbol(s,ct),4)):
            assert g.req('M%x,%x:%s'%(symbol(s,sym),size,value.to_bytes(size,'big').hex()))=='OK'
        assert g.req('Z0,%x,2'%(symbol(s,'I_FinishUpdate')&0xffffff))=='OK'
        armed=True
        for _ in range(900):
            try:g.cont();check_error()
            except RuntimeError as e:
                if 'EOF' in str(e) or 'exited' in str(e):status='emulator_ended';break
                raise
            tic=int.from_bytes(g.readmem(symbol(s,'_g_gametic'),4),'big')
            if not armed:
                for sym,value,size in (('r39f_dither_mode',mode,2),('r39d_active_colormap',symbol(s,mt),4),('colorcell',symbol(s,ct),4)):
                    assert g.req('M%x,%x:%s'%(symbol(s,sym),size,value.to_bytes(size,'big').hex()))=='OK'
                armed=True;continue
            if tic<=1:continue
            raw=g.readmem(symbol(s,'r22_fb')+4,1672)
            rect=list(g.readmem(symbol(s,'r92_rect'),4));y0,y1,x0,x1=rect
            assert 0<=x0<x1<=38 and 0<=y0<y1<=22,rect
            for y in range(y0,y1):
                for x in range(x0,x1):
                    w=int.from_bytes(raw[(y*38+x)*2:(y*38+x)*2+2],'big');tile=w&2047
                    assert not w&0x9800,(name,tic,x,y,hex(w))
                    assert 16<=tile<=241,(name,tic,x,y,hex(w))
                    if mode==0:assert tile<=31,(name,tic,hex(w))
                    if mode==1:assert tile<=136,(name,tic,hex(w))
                    if mode==2:assert tile<=31 or tile>=137,(name,tic,hex(w))
                    seen.add(w);palettes.add((w>>13)&3)
            vb=int.from_bytes(g.readmem(symbol(s,'_g_vblankCount'),4),'big');rows.append({'tic':tic,'vb':vb})
    finally:g.close()
    assert len(rows)>30,(name,'too few frames',len(rows))
    assert len(seen)>20 and len(palettes)==4,(name,'insufficient scene coverage',len(seen),palettes)
    summary=dict(mode=name,frames=len(rows),tic_range=[rows[0]['tic'],rows[-1]['tic']],status=status,
                 unique_tile_words=len(seen),palette_banks=sorted(palettes),tile_word_invariants='PASS')
    summaries.append(summary);(out/(name+'.json')).write_text(json.dumps(rows)+'\n');print(summary,flush=True)
(out/'SUMMARY.json').write_text(json.dumps(summaries,indent=2)+'\n')
