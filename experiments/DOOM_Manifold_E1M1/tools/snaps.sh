#!/bin/bash
# usage: snaps.sh ROM OUTPNG SECONDS frame1 frame2 ...
rom=$1; png=$2; secs=$3; shift 3
d=$(mktemp -d); fr="$*"
cat > $d/s.lua <<LUA
local n=0
local want={}
for f in string.gmatch("$fr","%d+") do want[tonumber(f)]=true end
emu.register_frame_done(function() n=n+1 if want[n] then manager.machine.video:snapshot() end end)
LUA
timeout 900 env SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy /usr/games/mame genesis -cart $rom -autoboot_script $d/s.lua -video none -sound none -nothrottle -seconds_to_run $secs -skip_gameinfo -snapshot_directory $d/snap >/dev/null 2>&1
python3 - $d $png <<'PY'
import sys,glob
from PIL import Image
fs=sorted(glob.glob(sys.argv[1]+'/snap/genesis/*.png'));ims=[Image.open(f) for f in fs];w,h=ims[0].size
c=min(4,len(ims));r=(len(ims)+c-1)//c
out=Image.new('RGB',(w*c,h*r))
for i,im in enumerate(ims): out.paste(im,((i%c)*w,(i//c)*h))
out.save(sys.argv[2])
PY
