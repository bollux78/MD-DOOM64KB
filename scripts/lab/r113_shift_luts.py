#!/usr/bin/env python3
"""R113 build step: append a pre-shifted twin (v<<4) to every composed LUT X_comp_even/odd[34][256]
in src/r59_color_tables.h, so X_comp[k] + 8704 holds the high-nibble value. ROM only."""
import re, sys
from pathlib import Path
p = Path(sys.argv[1]); t = p.read_text(); n = 0
out = []; pos = 0
for m in re.finditer(r'static const uint8_t (\w+_comp_(?:even|odd))\[34\]\[256\]\s*=\s*\{', t):
    i = m.end(); depth = 1; j = i
    while depth:
        c = t[j]; depth += c == '{'; depth -= c == '}'; j += 1
    nums = [int(x, 0) for x in re.findall(r'0x[0-9a-fA-F]+|\d+', t[i:j - 1])]
    assert len(nums) == 8704 and max(nums) <= 15, (m.group(1), len(nums), max(nums))
    rows = [nums[k:k + 256] for k in range(0, 8704, 256)]
    rows += [[(v << 4) & 255 for v in r] for r in rows]
    body = ',\n'.join('{' + ','.join(map(str, r)) + '}' for r in rows)
    out.append(t[pos:m.start()]); out.append('static const uint8_t %s[68][256]={\n%s}' % (m.group(1), body)); pos = j; n += 1
out.append(t[pos:]); t = ''.join(out)
assert n == 6 or (n == 0 and t.count('_comp_even[68][256]') == 3), n
p.write_text(t); print('R113 shifted LUT twins:', n)
