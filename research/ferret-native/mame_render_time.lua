-- Exact render time per pose: time between mailbox stage 3 (render start) and 4 (render end), MAME machine time.
-- Usage: mame genesis -cart ROM -autoboot_script mame_render_time.lua  -> prints RENDER_TIMES (seconds) for the 12 poses.
local cpu=manager.machine.devices[":maincpu"]
local mem=cpu.spaces["program"]
local t0=nil;local res={};local n=0
tap=mem:install_write_tap(0xfff008,0xfff00b,"stage",function(offset,data,mask)
  if offset==0xfff00a or offset==0xfff008 then
    local v=data&0xffff
    local now=manager.machine.time:as_double()
    if v==3 then t0=now elseif v==4 and t0 then res[#res+1]=now-t0 t0=nil end
  end
end)
emu.register_frame_done(function()
  if #res>=12 then
    local s=0 local t={}
    for i=1,12 do s=s+res[i] t[#t+1]=string.format("%.3f",res[i]) end
    print("RENDER_TIMES "..table.concat(t," ").." TOTAL "..string.format("%.3f",s))
    manager.machine:exit()
  end
end)
