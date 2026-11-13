"""Generate reciprocal scale and eight-row texture sample offsets."""
import sys
from pathlib import Path

lines = ["static const uint32_t depth_step[8193] = {"]
values = [0] + [(2**32 - 1) // (i * 32768) for i in range(1, 8193)]
for start in range(0, len(values), 16):
    lines.append("    " + ", ".join(map(str, values[start:start + 16])) + ",")
lines.extend(["};", "static const uint8_t row_offsets[65][8][8] = {"])
for step in range(65):
    patterns = ["{" + ", ".join(str((phase + y * step) // 8) for y in range(8)) + "}"
                for phase in range(8)]
    lines.append("    {" + ", ".join(patterns) + "},")
lines.append("};")
Path(sys.argv[1]).write_text("\n".join(lines) + "\n")
