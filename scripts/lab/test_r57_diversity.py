#!/usr/bin/env python3
"""R57 invariants: frozen palettes, exact controls, flats, and C pair rows."""
from pathlib import Path
import argparse,base64,hashlib,json,lzma,re,runpy,subprocess,tempfile
import numpy as np


def arrays(text):
    out={}
    for m in re.finditer(r'\b(r56_\w+)((?:\[\d+\])+)[ \t]*=[ \t]*\{(.*?)\};',text,re.S):
        shape=[int(x) for x in re.findall(r'\d+',m[2])]
        out[m[1]]=np.array([int(x) for x in re.findall(r'\d+',m[3])]).reshape(shape)
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',default='.')
    ap.add_argument('--tables',default='dist/r57-diversity/tables');ap.add_argument('--host-c',action='store_true')
    args=ap.parse_args();repo=Path(args.repo).resolve();tables=Path(args.tables).resolve()
    frozen=runpy.run_path(str(repo/'scripts/lab/r55_werk_snapshot.py'))['SNAPSHOTS']
    old={k:json.loads(lzma.decompress(base64.b64decode(v))) for k,v in frozen.items()}
    report=json.loads((tables/'REPORT.json').read_text())
    for name,result in report['profiles'].items():
        path=tables/(name+'.h');a=arrays(path.read_text());k=result['anchors'];snap=old['a'+str(k)]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==result['header_sha256']
        subprocess.run(['python3',str(repo/'scripts/lab/test_r56_dual_color.py'),str(path)],cwd=repo,check=True)
        if name!='c56-a6':
            for plane,side in enumerate(('even','odd')):
                assert np.array_equal(a['r56_pal'+str(plane)],np.array(snap['r52_pal'+str(plane)]).reshape(14,16))
                assert np.array_equal(a['r56_flat_'+side],snap['r55_flat_even'])
            if 'objective_history' in result:
                h=np.asarray(result['objective_history']);assert np.isfinite(h).all() and (np.diff(h)<=1e-10).all()
        else:
            frozen56=runpy.run_path(str(repo/'scripts/lab/r56_claudio_snapshot.py'))
            assert hashlib.sha256(path.read_bytes()).hexdigest()==frozen56['SHA']
        if name=='c55-a6':
            for plane,side in enumerate(('even','odd')):
                assert np.array_equal(a['r56_wall_'+side],snap['r52_'+side])
                assert np.array_equal(a['r56_pairs_'+side],[[i,i] for i in range(16)])
        if args.host_c:
            video=(repo/'src/r22_video.inc').read_text()
            row=re.search(r'static inline uint32_t R56_PairRow\(.*?\n}',video,re.S).group(0)
            code='#include <stdint.h>\n#include <assert.h>\n#include "'+str(path)+'"\n'+row+'''
int main(void){
 for(int plane=0;plane<2;plane++)for(int tile=0;tile<256;tile++)for(int y=0;y<8;y++){
  const uint8_t (*pairs)[2]=plane?r56_pairs_odd:r56_pairs_even;
  int c=y<4?tile>>4:tile&15;uint32_t r=R56_PairRow(c,pairs);
  if(!c){assert(r==0);continue;}
  for(int x=0;x<8;x++)assert(((r>>(28-4*x))&15)==(x<4?pairs[c][x&1]:0));
 }
 return 0;
}
'''
            with tempfile.TemporaryDirectory(prefix='r57-host-') as t:
                src=Path(t)/'test.c';src.write_text(code);exe=Path(t)/'test'
                subprocess.run(['cc','-std=c99','-O2',str(src),'-o',str(exe)],check=True)
                subprocess.run([str(exe)],check=True)
        print('PASS R57',name,'frozen CRAM/flat controls and encoded pair rows')
    # Counterfactual equality: control55 emits the old R55 RGB for every index,
    # in every effect and both parities, including codebook decode.
    a=arrays((tables/'c55-a6.h').read_text());snap=old['a6']
    for plane,side in enumerate(('even','odd')):
        book=a['r56_pairs_'+side];codes=a['r56_wall_'+side]
        for shade in range(14):
            expected=np.array(snap['r52_pal'+str(plane)]).reshape(14,16)[shade,np.array(snap['r52_'+side])]
            got=a['r56_pal'+str(plane)][shade,book[codes]]
            assert np.array_equal(got,np.repeat(expected[:,None],2,axis=1))
    print('PASS R55 control: all 256 colours x 14 effects x two planes are identical after pair decode')


if __name__=='__main__':main()
