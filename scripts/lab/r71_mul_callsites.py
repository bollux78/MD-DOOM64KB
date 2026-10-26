#!/usr/bin/env python3
"""R71 Rodada 0: enumerate actual call sites to libgcc __mulsi3 in linked R_Subsector.
Static call counts are NOT dynamic invocation counts.
Usage: r71_mul_callsites.py OBJDUMP OUTPUT.md r66=ELF r70a12=ELF
"""
import pathlib,re,subprocess,sys

objdump,out,*args=sys.argv[1:]
lines=["# R71-MUL Rodada 0 — static call sites (not measured frequencies)","",
       "Each entry lists up to eight instructions before the jsr/bsr into __mulsi3 in the linked LTO R_Subsector.",""]
for arg in args:
    label,path=arg.split("=",1)
    result=subprocess.run([objdump,"-d","-z",path],capture_output=True,text=True)
    if result.returncode: raise RuntimeError("objdump "+label+": "+result.stderr)
    listing=result.stdout.splitlines()
    start=next((i for i,l in enumerate(listing) if re.search(r"<R_Subsector(?:\.lto_priv\.\d+)?>:$",l)),None)
    if start is None: raise RuntimeError("R_Subsector not found: "+label)
    end=next((i for i in range(start+1,len(listing)) if re.match(r"^[0-9a-fA-F]+ <[^>]+>:$",listing[i])),len(listing))
    instr=[l for l in listing[start+1:end] if re.search(r"^\s*[0-9a-fA-F]+:\s",l)]
    callsites=[i for i,l in enumerate(instr) if "__mulsi3" in l and re.search(r"\b(?:jsr|bsr|bsrw|bsrs)\b",l)]
    allcalls=[i for i,l in enumerate(instr) if re.search(r"\b(?:jsr|bsr|bsrw|bsrs)\b",l)]
    lines.extend([f"## {label}: {len(callsites)} direct call sites to __mulsi3, {len(allcalls)} total jsr/bsr", ""])
    for idx,i in enumerate(callsites):
        lines.extend([f"### Call site {idx+1}", "~~~m68k"])
        lines.extend(instr[max(0,i-8):i+1]);lines.extend(["~~~",""])
    if not callsites: lines.append("No direct __mulsi3 call within R_Subsector (check compiler inlining/aliases).")
pathlib.Path(out).parent.mkdir(parents=True,exist_ok=True)
pathlib.Path(out).write_text("\n".join(lines)+"\n")
print("\n".join([x for x in lines if x.startswith("## ") or x.startswith("# R71-MUL")]))
