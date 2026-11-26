"""Fail if the linked ELF contains anything a 68000 cannot execute (68020+ opcodes/addressing).
Usage: check_isa.py ELF [objdump]. Checks the disassembly of every code symbol, including libgcc members."""
import re,subprocess,sys
elf=sys.argv[1];od=sys.argv[2] if len(sys.argv)>2 else "m68k-linux-gnu-objdump"
txt=subprocess.run([od,"-d","-M","68000",elf],check=True,capture_output=True,text=True).stdout
bad=[];fn=""
pat=re.compile(r"\b(mulsl|mulul|divsl|divul|divsll|divull|extbl|bfext[us]|bfins|bfset|bfclr|bfchg|bftst|bfffo|cas[lwb]?|cas2[lw]|chk2|cmp2|callm|rtm|pack|unpk|trap(?:cc|[a-z]{1,2})[wl]?|linkl|moveb2?c|movec|bkpt|cpush|cpull)\b")
for l in txt.splitlines():
    m=re.match(r"^[0-9a-f]+ <(.+)>:",l)
    if m:fn=m.group(1);continue
    f=l.split("\t")
    if len(f)<3:continue
    op=f[1].split()
    # 61ff/60ff/6xff: Bcc/BSR with 0xFF displacement = 32-bit displacement (68020+); odd target on a 68000
    if op and re.fullmatch(r"6[0-9a-f]ff",op[0]):bad.append((fn,l.strip(),"32-bit branch displacement (68020+)"))
    elif pat.search(f[2]):bad.append((fn,l.strip(),"68020+ mnemonic"))
    elif re.search(r":[wl]:[248]\)",f[2]) or re.search(r"@\((?:[^)]*,)?%?(?:za|zd)",f[2]) or re.search(r"\[|\]",f[2]):bad.append((fn,l.strip(),"scaled/memory-indirect 68020 addressing"))
    elif ".short" in f[2]:bad.append((fn,l.strip(),"undecodable word in code"))
for b in bad:print("ISA FAIL",*b)
if bad:sys.exit(1)
print("ISA OK: no 68020+ instruction found in",elf)
