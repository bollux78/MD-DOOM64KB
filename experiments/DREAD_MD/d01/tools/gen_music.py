#!/usr/bin/env python3
"""Music for DREAD-MD D01: the YM2612 arrangements of Doom's E1M1 and title (Intro) tracks
(d32xr ZGM payload pinned in assets/r25-music.json, same as R25/R29) -> VGM files + music.res
for SGDK rescomp (XGM2).   usage: gen_music.py RESDIR"""
import base64, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts/lab"))
from prepare_r25_music import decode, validate

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
payload = json.loads((ROOT / "assets/r25-music.json").read_text())
want = {"E1M1": "bgm_e1m1", "Intro": "bgm_intro"}
if sys.argv[2:] == ["--episode"]:
    want.update({f"E1M{i}": f"bgm_e1m{i}" for i in range(2, 10)})
res = []
for t in payload["tracks"]:
    if t["name"] not in want: continue
    packed = base64.b64decode(t["zgm"], validate=True)
    assert hashlib.sha256(packed).hexdigest() == t["sha256_zgm"]
    raw = decode(packed); validate(raw)
    fn = "d01-" + t["name"].lower() + ".vgm"
    (out / fn).write_bytes(raw)
    res.append('XGM2 %s "%s"' % (want[t["name"]], fn))
(out / "music.res").write_text("\n".join(res) + "\n")
print("music: %s" % ", ".join(r.split()[1] for r in res))
