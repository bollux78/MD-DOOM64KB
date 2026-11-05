#!/usr/bin/env python3
"""R134: add pinned BSD-3-Clause Freedoom PWADs in R133 5MiB extra banks.

This first release verifies physical storage from inside Doom. It does NOT yet
mount those maps into the game engine or present them as playable levels.
DOOM remains byte-for-byte identical in the original 4MiB region.
"""
import argparse
import hashlib
import json
import struct
import urllib.request
from pathlib import Path

FREEDOOM_COMMIT = '3ac019628d70b812ffb722f7f2365771b76a9d29'
BANK = 512 * 1024
MAPS = [
    ('E1M1',8,0x1000,142093,'98d3dac0a2aaff8d1647fe6f8948742647a46de3'),
    ('E1M2',8,0x24000,261418,'aa3bfc60fffd2941e0707b485befb17906e1c507'),
    ('E1M3',9,0x1000,220329,'f62d54ea0958525ac5fceb4d20d5e0d7ecdf7ea3'),
]
REGION = 0x400000
ROM_SIZE = 5*1024*1024


def git_hash(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def check_wad(data,name):
    assert data[:4] in (b'PWAD', b'IWAD'), (name,data[:4])
    count,diroff=struct.unpack_from('<II',data,4)
    assert 0 < count < 2048 and 0 < diroff and diroff+count*16 <=len(data), (name,count,diroff)
    names=[data[diroff+i*16+8:diroff+i*16+16].rstrip(b'\0').decode('ascii','replace') for i in range(count)]
    assert name in names,(name,names[:15])
    return {'lumps':count,'map_markers':[x for x in names if len(x)==4 and x[0]=='E' and x[2]=='M']}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--report',required=True,type=Path)
    p.add_argument('--cache',type=Path,default=None)
    a=p.parse_args()
    b=bytearray(a.input.read_bytes())
    assert len(b)==ROM_SIZE and b[0x100:0x108]==b'SEGA SSF'
    rows=[]
    for name,bank,offset,size,gitsha in MAPS:
        if a.cache:
            file=a.cache/(name.lower()+'.wad')
            raw=file.read_bytes()
        else:
            url=f'https://raw.githubusercontent.com/freedoom/freedoom/{FREEDOOM_COMMIT}/levels/{name.lower()}.wad'
            with urllib.request.urlopen(url,timeout=40) as r:
                raw=r.read()
        assert len(raw)==size and git_hash(raw)==gitsha, (name,len(raw),git_hash(raw))
        meta=check_wad(raw,name)
        start=bank*BANK+offset
        end=start+len(raw)
        assert end <= (bank+1)*BANK,(name,hex(end))
        assert start >= REGION
        b[start:end]=raw
        rows.append({'map':name,'license':'BSD-3-Clause','source':'freedoom/freedoom',
                     'revision':FREEDOOM_COMMIT,'git_blob_sha1':gitsha,'sha256':hashlib.sha256(raw).hexdigest(),
                     'rom_offset':start,'page':bank,'page_offset':offset,'size':len(raw),**meta})
    # Existing R133 bank test signatures at offset 0x100 in pages 8/9 stay intact.
    assert struct.unpack_from('>I',b,8*BANK+0x100)[0]==0xa9391018
    assert struct.unpack_from('>I',b,9*BANK+0x100)[0]==0xa838121b
    b[0x18E:0x190]=struct.pack('>H',sum((b[i]<<8)|b[i+1] for i in range(0x200,len(b),2))&0xffff)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_bytes(b)
    report={'variant':'r134-freedoom-extra-banks-storage-test',
       'file':a.output.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),
       'r133_input_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),
       'maps':rows,
       'status':'storage verification on boot; maps NOT playable yet',
       'note':'Only extra ROM pages and checksum changed; original Doom gameplay remains intact'}
    a.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
