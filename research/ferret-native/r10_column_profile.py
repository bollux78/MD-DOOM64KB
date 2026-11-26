"""Count executed GPGX master cycles and byte stores in the R10 column kernels."""
import ctypes as ct
import json
import pathlib
import re
import subprocess
import sys

from r09_gpgx_time import run

root, elf, objdump, scene, report = sys.argv[1:]
root, scene, report = map(pathlib.Path, (root, scene, report))
asm = subprocess.check_output([objdump, "-d", elf], text=True)
table = {}
kernel = 0
for line in asm.splitlines():
    label = re.match(r"^[0-9a-f]+ <([^>]+)>:", line)
    if label:
        name = label[1]
        row = re.fullmatch(r"gs\d+_(\d+)", name)
        kernel = (1 + int(row[1]) % 2 if row else
                  {"fr_col_pair_r": 3, "fr_col_pair_rn": 4}.get(name, 0))
    ins = re.match(r"^\s*([0-9a-f]+):\s+([0-9a-f]{4})\s+(?:[0-9a-f]{4}\s+)*(\S+)\s*(.*)", line)
    if kernel and ins:
        pc, word, _, _ = ins.groups()
        opcode = int(word, 16)
        store = opcode >> 12 == 1 and (opcode >> 9) & 7 == 0 and (opcode >> 6) & 7 in (2, 5)
        table[int(pc, 16)] = kernel + 8 * store
assert set(table.values()) == {1, 2, 3, 4, 9, 10, 11, 12}, set(table.values())
source = root / "core/m68k/m68kcpu.c"
patch = source.read_text()
marker = "void m68k_run(unsigned int cycles)"
after = ("    /* Execute instruction */\n"
         "    m68ki_instruction_jump_table[REG_IR]();\n"
         "    USE_CYCLES(CYC_INSTRUCTION[REG_IR]);")
assert patch.count(marker) == patch.count(after) == 1
decl = "static const unsigned char r10_kernel[] = {\n" + "".join(
    f"[0x{pc:x}]={kind},\n" for pc, kind in sorted(table.items())) + "};\n"
decl += """
unsigned int r10_column[256][4][2];
static void r10_count(unsigned int pc, unsigned int cycles) {
    if (!retro_r09_active || retro_r09_count == 0 || retro_r09_stage != 3 ||
        pc >= sizeof(r10_kernel) || !r10_kernel[pc]) return;
    unsigned int kind = r10_kernel[pc];
    unsigned int *row = r10_column[retro_r09_count - 1][(kind & 7) - 1];
    row[0] += cycles;
    row[1] += kind >> 3;
}
"""
patch = patch.replace(marker, decl + marker).replace(
    after, after + "\n    r10_count(research_pc & 0xffffff, m68k.cycles - research_start);")
source.write_text(patch)
subprocess.run(["make", "-C", root, "-f", "Makefile.libretro", "-j3", "platform=unix"],
               check=True, stdout=subprocess.DEVNULL)
so = root / "genesis_plus_gx_libretro.so"
lib = ct.CDLL(str(so))
data = run(so, scene, 1)
assert data["actual_sram_selected"] == [0]
counts = (((ct.c_uint * 2) * 4) * 256).in_dll(lib, "r10_column")
names = ("generated_even", "generated_odd", "wrap", "no_wrap_fallback")

def metric(cycles, stores):
    return {"master_cycles": cycles, "bytes": stores,
            "cpu_cycles_per_byte": cycles / (7 * stores) if stores else None}

rows = {}
for i, camera in enumerate(data["warm_cameras"]):
    bins = counts[2*i+1]
    rows[camera["camera"]] = {name: metric(*bins[j]) for j, name in enumerate(names)}
    rows[camera["camera"]]["all"] = metric(sum(x[0] for x in bins), sum(x[1] for x in bins))
out = {"emulator": "GPGX 2499cd3 NTSC", "memory": "WRAM", "cameras": rows}
report.write_text(json.dumps(out, indent=2))
print(json.dumps(out), flush=True)
