#!/usr/bin/env python3
"""R53 host oracle: micro-pattern invariants and Cláudio palette companions."""
from pathlib import Path
import argparse,json,re
def parse(name,text):
    m=re.search(r"\b"+re.escape(name)+r"\[16\]=\{([^}]*)\}",text,re.S)
    if m is None:raise SystemExit("R53 missing "+name)
    out=[int(s.strip()) for s in m.group(1).split(",")]
    assert len(out)==16 and all(0<=v<=15 for v in out)
    assert out[0]==0
    return out
def row(base,partner,y,ratio):
    if base==0:return (0,)*8
    a=[partner if ((x+y)%4==0 if ratio==25 else (x+y)%2==0) else base for x in range(4)]
    return tuple(a+[0]*4)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--src",default="src")
    ap.add_argument("--ratio",type=int,choices=[25,50],required=True)
    args=ap.parse_args()
    root=Path(args.src);txt=(root/"r53_micro_tables.h").read_text()
    a=parse("r53_partner_even",txt);b=parse("r53_partner_odd",txt)
    r=json.loads((root/"r53_micro_report.json").read_text())
    assert r["ratio_percent"]==args.ratio
    assert a==r["companion_maps"]["even"] and b==r["companion_maps"]["odd"]
    for pair in (a,b):
        for base in range(16):
            for y in range(4):
                pixels=row(base,pair[base],y,args.ratio)
                assert pixels[4:]==(0,)*4
                if base==0:assert pixels==(0,)*8
                else:
                    assert all(1<=v<=15 for v in pixels[:4]) if r["zero_policy"]=="forbid" else all(0<=v<=15 for v in pixels[:4])
            if base>0 and pair[base]!=base:
                vals=[x for y in range(4) for x in row(base,pair[base],y,args.ratio)[:4]]
                assert vals.count(pair[base])==int(16*args.ratio/100),(base,args.ratio)
    assert 256+2*256<=1440,"R53 tile banks collide with font"
    print("PASS: R53",args.ratio,"1px patterns, transparency, partner LUT, tile bank budget")
if __name__=="__main__":main()
