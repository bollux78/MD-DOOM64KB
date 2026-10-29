#!/usr/bin/env python3
"""Align immutable ROM linedefs; preserve every original field byte."""
from pathlib import Path
import sys
from convert_r24_episode import read_wad,write_wad
def align(blob):
 lumps=read_wad(blob,True);out=[];count=0
 for name,data in lumps:
  if name=='LINEDEFS':
   assert len(data)%31==0
   rows=[data[i:i+31] for i in range(0,len(data),31)]
   data=b''.join(r+b'\0' for r in rows);count+=1
   assert all(data[i*32:i*32+31]==r for i,r in enumerate(rows))
  out.append((name,data))
 assert count==9,count
 return write_wad(out)
if __name__=='__main__':
 p=Path(sys.argv[1]);old=p.read_bytes();new=align(old);p.write_bytes(new);print('R89 aligned linedefs:',len(new)-len(old),'extra ROM bytes')
