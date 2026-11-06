#!/usr/bin/env python3
from pathlib import Path
import sys
src=Path(sys.argv[1]).read_bytes()
if len(src) % 2: src+=b'\0'
out=Path(sys.argv[2]); out.parent.mkdir(parents=True,exist_ok=True)
lines=['/* generated - do not edit */','#ifndef SUB_PROGRAM_H','#define SUB_PROGRAM_H',f'#define SUB_PROGRAM_WORDS {len(src)//2}','static const unsigned short sub_program[SUB_PROGRAM_WORDS] = {']
for i in range(0,len(src),24):
    part=src[i:i+24]
    lines.append('    '+', '.join('0x%04X'%((part[j]<<8)|part[j+1]) for j in range(0,len(part),2))+',')
lines+=['};','#endif']
out.write_text('\n'.join(lines)+'\n')
print('Sub-CPU payload:',len(src),'bytes')
