local mem=manager.machine.devices[":maincpu"].spaces["program"]
local P=tonumber(os.getenv("AP"),16); local H=tonumber(os.getenv("AH"),16)
local n=0
emu.register_frame_done(function() n=n+1
 if n==200 then print(string.format("before ammo=%d health=%d",mem:read_i16(H+4),mem:read_i16(H))) end
 if n>=210 and n<=300 then mem:write_u32(P,2736<<10); mem:write_u32(P+4,(-4160)<<10); mem:write_u16(P+12,174) end
 if n==320 then print(string.format("after ammo=%d health=%d",mem:read_i16(H+4),mem:read_i16(H))) end
end)
