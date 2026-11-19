-- bench_auto.lua: drives the in-ROM benchmark (MANIFOLD_BENCH=1) inside MAME.
-- env: BADDR (hex address of manifold_dbg), BNP (points), BOUT (result file).  Snapshot after each point = last frame measured.
local n=0 local m=manager.machine local mem=m.devices[":maincpu"].spaces["program"] local q=m.ioport.ports[":ctrl1:mdpad:PAD"]
local A=tonumber(os.getenv("BADDR"),16) local NP=tonumber(os.getenv("BNP")) local OUT=os.getenv("BOUT")
local lasti=-1 local done=false
emu.register_frame_done(function() n=n+1
 q.fields["P1 Start"]:set_value(((n>=100 and n<110) or (n>=150 and n<160) or (n>=200 and n<210) or (n>=250 and n<260)) and 1 or 0)
 local st=mem:read_u8(A) local i=mem:read_u8(A+1)
 local k=mem:read_u8(A+2) -- frames since the jump; 13 = last held frame (SETTLE 3 + NF 8 + HOLD 3 - 1)
 if st==0 and k==13 and i~=lasti then m.video:snapshot() lasti=i end
 if st==2 and not done then done=true
  local r={} for k=0,NP-1 do r[#r+1]=mem:read_u8(A+6+k)*2 end
  local f=io.open(OUT,"w") f:write(table.concat(r," ").."\n") f:close()
  m.video:snapshot() m:exit() end
end)
