"""Compare actual MAME screenshots with expected 320x144 host tile output.
Search only small border offsets. No rescaling or arbitrary color matching.
"""
import json,pathlib,re,sys
from PIL import Image
P=pathlib.Path
def main():
    out,report=map(P,sys.argv[1:])
    from test_demo import host
    exp=host(out)
    m=re.search(r"sc_palette\[\d+\]\s*=\s*\{([^}]+)\}",(out/"scene.h").read_text())
    assert m
    pal=[int(s) for s in re.findall(r"\d+",m.group(1))]
    # CRAM 3-bit components; MAME DAC may use a slightly different transfer curve.
    rgb=[((v>>1&7)*255//7,(v>>5&7)*255//7,(v>>9&7)*255//7) for v in pal]
    rows=[]
    for i in range(len(exp)):
        p=out/f"pose-{i}.png"
        if not p.exists():
            rows.append({"pose":i,"error":"missing actual emulator screenshot","pass":False});continue
        im=Image.open(p).convert("RGB");w,h=im.size
        tile=(out/f"expected-tiles-{i}.bin").read_bytes()
        expected=[]
        for y in range(144):
            for x in range(320):
                tx,px=divmod(x,8);ty,py=divmod(y,8)
                b=tile[(ty*40+tx)*32+py*4+px//2]
                expected.append(rgb[(b>>4) if px%2==0 else (b&15)])
        if w<320 or h<144:
            rows.append({"pose":i,"size":[w,h],"error":"unexpected screenshot dimensions","pass":False});continue
        pix=im.load()
        # locate crop near expected centered area only, using sparse samples
        best=None
        for oy in range(max(0,(h-144)//2-12),min(h-144,(h-144)//2+12)+1):
            for ox in range(max(0,(w-320)//2-12),min(w-320,(w-320)//2+12)+1):
                score=sum(sum(abs(a-b) for a,b in zip(pix[x+ox,y+oy],expected[y*320+x])) for y in range(0,144,12) for x in range(0,320,16))
                if best is None or score<best[0]:best=(score,ox,oy)
        _,ox,oy=best
        errors=[max(abs(a-b) for a,b in zip(pix[x+ox,y+oy],expected[y*320+x])) for y in range(144) for x in range(320)]
        match=sum(e<=36 for e in errors)
        rows.append({"pose":i,"size":[w,h],"crop":[ox,oy],"matched":match,"pixels":46080,"fraction":match/46080,"mean_max_channel_error":sum(errors)/46080,"pass":match>=.99*46080})
    result={"poses":rows,"pass":all(x["pass"] for x in rows),"scope":"actual emulator screenshot versus host tile buffer, fixed 3-bit CRAM RGB with tolerance 36"}
    report.write_text(json.dumps(result,indent=2));print("SCREEN VERIFY "+json.dumps(result),flush=True)
    if not result["pass"]:sys.exit(2)
if __name__=="__main__":main()
