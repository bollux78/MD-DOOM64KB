import sys,json
from pathlib import Path
import validation as v
for variant in sys.argv[1:]:
 g=v.Game(variant)
 try:
  print(variant,g.route(),flush=True)
 finally:g.e.close()
