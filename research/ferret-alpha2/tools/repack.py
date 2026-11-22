"""Independent model of the observed 80 strips × 72 rows, 16-bit layout."""
from pathlib import Path
import argparse,hashlib,json

def repack(source):
 assert len(source)==11520
 assert len(set(source))>2, "Empty/incomplete source capture"
 out=bytearray()
 for ty in range(18):
  for tx in range(40):
   for row in range(4):
    y=ty*4+row
    left=(2*tx*72+y)*2;right=((2*tx+1)*72+y)*2
    line=source[left:left+2]+source[right:right+2]
    out.extend(line);out.extend(line)
 return bytes(out)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
 got=repack((a.folder/'completed_source.bin').read_bytes());expected=(a.folder/'completed_tiles.bin').read_bytes()
 d={'size':len(got),'equal':got==expected,'differing_bytes':sum(x!=y for x,y in zip(got,expected)),'model_sha256':hashlib.sha256(got).hexdigest(),'observed_sha256':hashlib.sha256(expected).hexdigest()}
 (a.folder/'repack-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(d);assert got==expected
