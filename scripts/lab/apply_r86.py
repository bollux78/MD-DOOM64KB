#!/usr/bin/env python3
"""R86 kernels and selective compiler optimization on R85 all."""
from pathlib import Path
import os

def unroll(s,factor):
 a=s.index('3:\n');b=s.index('4:\n',a)
 original=s[a+3:b];pair=original[:original.index(' dbra')]
 body=pair.replace(' lea 152(%a0),%a0\n','')
 groups=[]
 for i in range(factor):
  groups.append(body.replace('move.b %d5,(%a0)',f'move.b %d5,{152*i}(%a0)'))
 setup=f''' move.w %d2,%d3
 and.w #{factor-1},%d3
 swap %d2
 move.w %d3,%d2
 swap %d2
 lsr.w #{1 if factor==2 else 2},%d2
 moveq #0,%d3
 subq.w #1,%d2
 bmi.w 6f
5:
'''
 # Replace count decrement originally immediately before label 3.
 prefix=s[:a];assert prefix.endswith(' subq.w #1,%d2\n bmi.s 4f\n')
 prefix=prefix[:-len(' subq.w #1,%d2\n bmi.s 4f\n')]
 middle=setup+''.join(groups)+f' lea {152*factor}(%a0),%a0\n dbra %d2,5b\n6:\n swap %d2\n subq.w #1,%d2\n bmi.w 4f\n3:\n'+original
 out=prefix+middle+s[b:]
 return out.replace('beq.s','beq.w').replace('bmi.s','bmi.w')

def attribute(path,signatures):
 p=Path(path);s=p.read_text()
 for sig in signatures:
  assert s.count(sig)==1,(path,sig,s.count(sig))
  s=s.replace(sig,'__attribute__((optimize("O3"))) '+sig)
 p.write_text(s)

def main():
 mode=os.environ['R86_CANDIDATE'];assert mode in ('control','u4','u8','geo-o3','logic-o3')
 if mode in ('u4','u8'):
  p=Path('src/r60_pair_wall.s');p.write_text(unroll(p.read_text(),2 if mode=='u4' else 4))
 if mode=='geo-o3':
  attribute('src/r_draw.c',['static angle16_t R_PointToAngle16(int16_t x, int16_t y)','static CONSTFUNC int16_t R_PointToDist(int16_t x, int16_t y)','static fixed_t R_ScaleFromGlobalAngle(int16_t x)'])
 if mode=='logic-o3':
  attribute('src/p_maputl.c',['static int16_t PUREFUNC P_PointOnDivlineSide(fixed_t x, fixed_t y, const divline_t *line)','static fixed_t PUREFUNC P_InterceptVector3(const divline_t *v2, const divline_t *v1)'])
 p=Path('scripts/lab/build_r71a12mul_hud.py');s=p.read_text();assert "'r85-'" in s and "('all',0)" in s
 p.write_text(s.replace("'r85-'","'r86-'").replace("('all',0)","('%s',0)"%mode))
 print('R86',mode,'on R85 all')
if __name__=='__main__':main()
