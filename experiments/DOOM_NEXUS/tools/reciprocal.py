"""Generate the normalized mantissa lookup for the 68000 wall sampler."""
import sys
from pathlib import Path

values = [(1 << 26) // i for i in range(2048, 4097)]
lines = ["static const uint16_t wall_reciprocal[2049] = {"]
for start in range(0, len(values), 12):
    lines.append("    " + ", ".join(map(str, values[start:start + 12])) + ",")
lines.append("};")
Path(sys.argv[1]).write_text("\n".join(lines) + "\n")
