#!/usr/bin/env python3
"""R55: reproduce Werk's prevalidated Flat-Safe Balanced A4/A6 palette tables.
Source: uploaded MD_DOOM_R55_FLAT_SAFE_HANDOFF ZIP; only compact CRAM,
source-index LUTs, and flat LUT are stored; COLORMAP tables rebuilt from WAD.
Avoids recomputing Werk's offline optimisation on hardware runner.
"""
import argparse, base64, json, lzma, re, runpy
from pathlib import Path

SNAPSHOTS = {
  "a4": "/Td6WFoAAATm1rRGAgAhARwAAAAQz1jM4A1VA1hdAD2IikOHtw7gD8K0Gb5SvsRyugDZwhDc0ubH4MKQMe+wWMu5QBE9Lxw/x3WAti0KdByGuEyZqL76BX/Zy3MCA7gmmVF5YK8YJsk9x0jLU+J6uVDuwTzSeXfOQCrZ5JGqGpTQNXPxmI+zUfefsQwOJk4UrebPCS/d3V20kP+5DqdZnxfyMNORpPQ//SRwvS0a+JITgTxUuNM4kmwVPF4gQVqZ27H5fDUFSU4bohkNxVYQUdQ/mADEjaXxz7h/OsHfoux7qmGYSvhHdEIfmCd09i0myVdCBfu5tx1gWqGEnspAQGHwjehHXnQYb0pFtFEymktwXwh7l9uBFOKbUyFrUBZFo3g3olVQsiWoRrYEqC7z62j+0hy5TPhZDWZvIeykyIlA9ZTA68WnRoM27iTkceTrUEkaPTWkYn+D7KJcq1FBB9LnPPtrQRufuiByBAPXSwX8IJzWEdLyfe1DCsrWKGOfXtlA8AfweMiPsO+ia3uQZlbibLNuq5LP13dnZU0aMOOzYNmTGAxXqlxI987PeFYITW8IDB42vsXRcE8ebrvjTixLvHNPUgpWU5Qo8F++MzG62O4+zFWiGZHcpflO+M20ovtCCTGgltgxzF7pQuiOHk1JXXwthe4JcwuwGjWJDS3ZsTMRrnRNe8R6sq7LxdfCUrtVAR71jNEuy9G0Hz2CP7X+OEmk3qEtxtE4wqkeubyGFvwhALl50UjDhNFBjS3eII/9nt4M24QlIgaeoN4+H4CrDXncQYWvbsk/hZGmwgG6FSiNZi8qQab54DS9HSzcZ2wHI2Ax8sVNhwJ06XNp9BwN7lmDPAD7ONdzbq49RQ9OJrE7HrOZCLTBtoRJE+HxpW7i56u7kxApDkAnoBJ/PfmBGIFIN1/HmOPFRMX+uZUn1poMr1mAoMacNoaPl1u7BaUF2b9sk6nuZ2Pgy4UP0/cuV9cDDgZvo6Mkj8p30Hrv9oZkbbwFegWE7Gj6SYqTltfewKkrF+tkJvUGxQw9TSht4LdtrHFTeDAko2rjPluZ5FfATdrWGka0a/SOsFEuzJ6LIiU2Kseh6/znmOYv9Azd1E0vgV0I7jgiJsHJrtmSxK2uyU8LVDOiwLy1jIrzAWsBSZHW79V3KNk9xOcNw4EoXWg5KCAAscd6PtbZ7PQAAfQG1hoAAJG6mNCxxGf7AgAAAAAEWVo=",
  "a6": "/Td6WFoAAATm1rRGAgAhARwAAAAQz1jM4A1NAyBdAD2IikOHtw7gD8K0Gb5SvsRyugDZwhDc0ubH4MKQMesN1NI/E+mn+zbDWLXAbzUnfZkZVCv2GrZ1YUlRjRNigja7zAg9k/JkaYL+EkjjZajA928vM4DLrLQIs5gqcAGo9VHDe+CWnz2h2th7x0WuZd1HUygN/kIVbYtqFXvgRo0Zz4xh6/lpY0rzbkDRgOhGkupPs4EXjF4zsFkehrGCbNCh5W+ER39PJDiWxdtlT5m7WMCnKYteBDxiUDOWJx7UfLLvLHtZ7fV0oOQSVkQ74jsqbVeqL5vX0NJCCPC9RdBoVVn2+C5myF1SvsibCbR3Qw+RPyNuxEwi2XvjiFEnmY09LV4OX3BM6cSs6u2yKuIxSoqlIptu2SUdlpG/xBkAz1mMWODNzClGk3id6zHfG2fIPCdqpW6C5j6IRitZBlsxRbfYSM7HYRCt6LPDX70BntUJTnHy0rptofIdwfxdGeQhDnkfYz5sMZIfZEODf83q+fiYAPhFp0IRbADg8u5d/vFnUB6Vz6i8NDGFeP/LPZp4+11lI23RGjCNIxLfjjwJI4BHg35Q/yl3kHXFRk2omF7C8DB5r8t0sozF4SWDAhx62FXZ2qdv9iAW4zhhp5xhFIJKm7Q5lo4siKDZNYNfmZYZKpcdu+mjrLwz/EJMHSR4fh+STg4dBgvyon0dvcvp3OKYHNQDE72obhAuubd073Nb3xvl0j+pNvNPGGqS3rOWxCKPdbE9yKHK8Tl7KgaCJPR1V6uZq+LND6tGqs71JzWrquPdFlnwg62uRPYZp8NdB443bpMnlu8kRzBCT65eoIKJZ4CjpviZQZfVlcYh94TLhj/BGaOqq/WIJ/ult+es/FIp/bSkdGrEDF/0cz9anhvmyfe+3ftDUrsXiMXsxfzu89b7p0uFSE50Dk1IyxhltkOuAy8v3iFQid/0qkQQYQlXXUgJ2hdN//RQq5Em6Hna+3FRA8KgzsSIJT0Yt8VUVR7g1fqe7oMEflNboz41JfXUdFBLoAu6vY3Z7hXdI3rIOWpgjp6hmXEcp6HKpCRjRfrZg5lQT1gJSuioOTmAADFZsVlXnXhDAAG8Bs4aAADgTT6mscRn+wIAAAAABFla"
}
def c_arr(name, typ, vals):
    parts = [','.join(str(n) for n in vals[i:i+32]) for i in range(0, len(vals), 32)]
    return f"static const {typ} {name}[{len(vals)}]={{\n" + ",\n".join(parts) + "\n};"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--variant",required=True,choices=("a4","a6"))
    ap.add_argument("--repo",default=".")
    ap.add_argument("--out",default="src")
    a=ap.parse_args()
    repo=Path(a.repo).resolve()
    values=json.loads(lzma.decompress(base64.b64decode(SNAPSHOTS[a.variant])))
    assert len(values["r52_pal0"])==len(values["r52_pal1"])==224
    for key in ("r52_even","r52_odd","r55_flat_even"):
        assert len(values[key])==256
    flat=values["r55_flat_even"]
    assert all(1<=x<=int(a.variant[1]) for x in flat)
    for shade in range(14):
        for slot in range(1,int(a.variant[1])+1):
            i=16*shade+slot
            assert values["r52_pal0"][i]==values["r52_pal1"][i]
    lumps=runpy.run_path(str(repo/"scripts/lab/gen_r52_claudio.py"))["wad_lumps"]((repo/"scripts/doom64.wad").read_bytes())
    cm=next(data for name,data in lumps if name=="COLORMAP")
    assert len(cm)==8704
    values["r52_comp_even"]=[values["r52_even"][x] for x in cm]
    values["r52_comp_odd"]=[values["r52_odd"][x] for x in cm]
    values["r55_flat_odd"]=flat.copy()
    path=Path(a.out)/"r52_ab_tables.h"
    s=path.read_text()
    for name,nums in values.items():
        typ="uint16_t" if name.startswith("r52_pal") else "uint8_t"
        code=c_arr(name,typ,nums)
        regex=rf"static const {typ}\s+{name}\[\d+\]=\{{.*?\}};"
        if re.search(regex,s,re.S):
            s,n=re.subn(regex,lambda _: code,s,count=1,flags=re.S)
            assert n==1
        else:
            assert name.startswith("r55_flat_")
            s=s.replace("#endif",code+"\n#endif",1)
    s=s.replace("#define R52_COLORMAP_BYTES 8704","#define R52_COLORMAP_BYTES 8704\n#define R55_FLAT_TABLES_VERSION 1",1)
    path.write_text(s)
    print(f"R55 WERK SNAPSHOT {a.variant}: checked shared slots, LUTs and 14 effects")
if __name__=="__main__": main()
