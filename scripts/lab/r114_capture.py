#!/usr/bin/env python3
"""Complete DEMO3 post-pass capture; optional VBlank-PC profile in the same execution.
No ROM instrumentation. Only one-time writes to existing colour/Shadow bytes.
Windows use the game's actual counters, not the host clock or assumed 15-frame groups.
"""
import argparse, bisect, collections, hashlib, json, pathlib
from r64a_rsp_capture import RSP, symbols
from r94_pcprofile import text_symbols

PIXELS=3344

def sym(s,n):
    if n in s:return s[n]
    a=[v for k,v in s.items() if k.startswith(n+'.')]
    assert len(a)==1,(n,a)
    return a[0]

def capture(a):
    out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)
    sy=symbols(a.elf)
    names=('I_FinishUpdate','R92_AfterPass','G_CheckDemoStatus','I_Error',
           'r22_fb','_g_gametic','_g_vblankCount','_g_gamemap','r92_shadow_on','r77_color_state',
           'r89_ai_low','bench_start_vb','bench_frames','bench_windows','bench_window_vb','bench_min_x10','bench_max_x10')
    ad={n:sym(sy,n) for n in names}
    if a.stack:ad.update({n:sym(sy,n) for n in ('heapEnd','_bend')})
    pcad={n:ad[n]&0xffffff for n in ('I_FinishUpdate','R92_AfterPass','G_CheckDemoStatus','I_Error')}
    vint=int.from_bytes(pathlib.Path(a.rom).read_bytes()[0x78:0x7c],'big')&0xffffff
    def read(n,size=4):return int.from_bytes(g.readmem(ad[n],size),'big')
    def state():return dict(bench_frame=read('bench_frames'),window=read('bench_windows',2),
                           window_vb=read('bench_window_vb'),start_vb=read('bench_start_vb'))
    g=RSP(a.blastem,a.rom,a.max_emulated_frames,a.timeout)
    rows=[];samples=[];status='max_breaks';armed=False;end=None;stack=None
    try:
        g.req('qSupported')
        for n,p in pcad.items():assert g.req('Z0,%x,2'%p)=='OK'
        for _ in range(200000):
            try:g.cont()
            except (RuntimeError,TimeoutError) as e:status=str(e);break
            regs=g.req('g');pc=int(regs[17*8:18*8],16)&0xffffff
            if pc==pcad['I_Error']:raise RuntimeError('ROM stopped at I_Error')
            if not armed:
                assert pc==pcad['I_FinishUpdate'],hex(pc)
                if a.stack:
                    lo=read('heapEnd')|0xe0000000;sp=int(regs[15*8:16*8],16)|0xe0000000;hi=sp-128
                    assert (ad['_bend']|0xe0000000)<=lo<hi<0xe1000000,(hex(lo),hex(hi))
                    for off in range(lo,hi,192):
                        n=min(192,hi-off)
                        assert g.req('M%x,%x:%s'%(off&0xffffff,n,(b'\xa5'*n).hex()))=='OK'
                    stack=dict(heap_end=hex(lo),reserve_bytes=0xe1000000-lo,painted_bytes=hi-lo,tic_start=read('_g_gametic'))
                assert g.req('M%x,1:%02x'%(ad['r92_shadow_on'],a.shadow))=='OK'
                assert g.req('M%x,2:%02x01'%(ad['r77_color_state'],a.mode))=='OK'
                assert g.req('z0,%x,2'%pcad['I_FinishUpdate'])=='OK'
                if a.profile:assert g.req('Z0,%x,2'%vint)=='OK'
                armed=True;continue
            if pc==pcad['G_CheckDemoStatus']:
                end=state();end.update(vb=read('_g_vblankCount'),min_x10=read('bench_min_x10',2),max_x10=read('bench_max_x10',2))
                if stack is not None:
                    mem=g.readmem(lo&0xffffff,hi-lo)
                    first=next((i for i,b in enumerate(mem) if b!=0xa5),None)
                    assert first is not None,'stack probe untouched'
                    stack.update(peak_stack_bytes=0xe1000000-(lo+first),headroom_bytes=first,tic_end=read('_g_gametic'))
                    assert first>=128,stack
                status='demo_complete';break
            if pc==vint and a.profile:
                sp=int(regs[15*8:16*8],16)&0xffffff
                frame=g.readmem(sp,6);interrupted=int.from_bytes(frame[2:6],'big')&0xffffff
                samples.append((read('_g_gametic'),read('_g_vblankCount'),interrupted));continue
            assert pc==pcad['R92_AfterPass'],hex(pc)
            tic=read('_g_gametic');mp=read('_g_gamemap',2)
            assert mp==a.map,(mp,a.map,tic)
            st=g.readmem(ad['r77_color_state'],3)
            assert read('r89_ai_low',1)==0,'benchmark requires AI Normal'
            fb=g.readmem(ad['r22_fb']+4,PIXELS)
            r=dict(i=len(rows),tic=tic,vb=read('_g_vblankCount'),mode=st[0],palette=st[2],map=mp,
                   shadow=read('r92_shadow_on',1),sha256=hashlib.sha256(fb).hexdigest(),**state())
            rows.append(r)
            with open(out/'post.bin','ab') as f:f.write(fb)
            with open(out/'frames.jsonl','a') as f:f.write(json.dumps(r)+'\n')
    finally:g.close()
    with open(out/'samples.tsv','w') as f:
        for t,v,p in samples:f.write('%d\t%d\t%06x\n'%(t,v,p))
    result=dict(status=status,rom=a.rom,shadow=a.shadow,mode=a.mode,map=a.map,
                stack=stack,frames=len(rows),first_tic=rows[0]['tic'] if rows else None,
                last_tic=rows[-1]['tic'] if rows else None,end=end,profile_samples=len(samples))
    # Read the true window transitions, which become observable at the next post-pass stop.
    windows=[];prev_window=0;prev_frame=0;prev_vb=rows[0]['start_vb'] if rows else 0
    for r in rows+([end] if end else []):
        if r is end:r={**r,'window':r.get('window',0)}
        if r['window']>prev_window:
            assert r['window']==prev_window+1,(prev_window,r)
            nf=r['bench_frame']-prev_frame;nv=r['window_vb']-prev_vb
            windows.append(dict(index=r['window'],frame_start=prev_frame+1,frame_end=r['bench_frame'],
                                vb_start=prev_vb,vb_end=r['window_vb'],frames=nf,vblanks=nv,
                                fps=60*nf/nv,fps_x10=(nf*600+nv//2)//nv))
            prev_window=r['window'];prev_frame=r['bench_frame'];prev_vb=r['window_vb']
    worst=sorted(windows,key=lambda r:(r['fps'],r['index']))[:10]
    if a.profile:
        ts=text_symbols(a.elf);addrs=[x[0] for x in ts]
        def fun(pc):
            i=bisect.bisect_right(addrs,pc)-1
            return ts[i][1] if i>=0 else '?'
        for w in worst:
            hit=[p for t,v,p in samples if w['vb_start']<=v<w['vb_end']]
            c=collections.Counter(fun(p) for p in hit)
            w['pc_samples']=len(hit)
            w['profile']=[dict(function=f,samples=n,share=n/max(1,len(hit))) for f,n in c.most_common(15)]
        cnt=collections.Counter(fun(p) for _,_,p in samples)
        result['profile']=[dict(function=f,samples=n,share=n/max(1,len(samples))) for f,n in cnt.most_common(30)]
    result['worst_windows']=worst
    (out/'windows.json').write_text(json.dumps(windows,indent=1)+'\n')
    (out/'CAPTURE.json').write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps(result,indent=1))
    assert status=='demo_complete',status
    assert end and end['bench_frame']==2134,end
    assert len(rows)>=2100 and rows[-1]['tic']>=2100,result
    if windows:assert min(w['fps_x10'] for w in windows)==end['min_x10'],(end,sorted(windows,key=lambda w:w['fps_x10'])[:1])


def main():
    p=argparse.ArgumentParser();p.add_argument('--blastem',required=True);p.add_argument('--rom',required=True)
    p.add_argument('--elf',required=True);p.add_argument('--out',required=True)
    p.add_argument('--shadow',type=int,choices=(0,1),required=True);p.add_argument('--mode',type=int,choices=(1,2),required=True)
    p.add_argument('--map',type=int,choices=(1,7),required=True);p.add_argument('--profile',action='store_true')
    p.add_argument('--stack',action='store_true')
    p.add_argument('--max-emulated-frames',type=int,default=50000);p.add_argument('--timeout',type=float,default=600)
    a=p.parse_args();assert 1<=a.max_emulated_frames<=100000
    capture(a)
if __name__=='__main__':main()
