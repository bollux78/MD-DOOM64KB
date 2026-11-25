#!/usr/bin/env python3
"""Generate Ferret-derived direct MOVE scalers from arithmetic, without ROM data."""
from pathlib import Path
import argparse

def offsets(q):
    inv=max(1,q*32+16)
    return [max(-32768,min(32767,((y-36)*8192)//inv)) for y in range(72)]

def main():
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--asm',dest='assembly',type=Path);a=p.parse_args()
    unique={};indices=[]
    for q in range(2048):
        row=tuple(offsets(q))
        if row not in unique:unique[row]=len(unique)
        indices.append(unique[row])
    with a.output.open('w') as f:
        f.write('#include "mapdata.h"\n#if !defined(__m68k__) && !defined(__mc68000__)\n')
        for row,idx in unique.items():f.write('static const int16_t fr_offsets_%d[72]={%s};\n'%(idx,','.join(map(str,row))))
        f.write('const int16_t *const ferret_sample_offsets[2048]={'+','.join('fr_offsets_%d'%i for i in indices)+'};\n#endif\n')
    if a.assembly:
        with a.assembly.open('w') as f:
            f.write('.text\n.align 2\n')
            for name in ['byte','pair']:
                for row,idx in unique.items():
                    if name=='pair' and any(not -16384<=v<=16383 for v in row):continue
                    f.write('fr_%s_%d:\n'%(name,idx))
                    for y,off in enumerate(row):
                        # MOVE.B or MOVE.W from column+offset to tile row y.
                        words=[0x1169 if name=='byte' else 0x3169,off*(1 if name=='byte' else 2),y*4,0x51ce,2,0x4e75]
                        f.write('.word '+','.join(str(v&65535) for v in words)+'\n')
                    f.write('.word 0x4e75\n')
                f.write('.globl ferret_scalers_%s\nferret_scalers_%s:\n'%(name,name))
                refs=[]
                rows=list(unique)
                for j in indices:
                    refs.append('0' if name=='pair' and any(not -16384<=v<=16383 for v in rows[j]) else 'fr_%s_%d'%(name,j))
                for i in range(0,2048,16):f.write('.long '+','.join(refs[i:i+16])+'\n')
    print('Ferret scalers:',len(unique),'unique rows; 2048 selectors; 72 rows')
if __name__=='__main__':main()
