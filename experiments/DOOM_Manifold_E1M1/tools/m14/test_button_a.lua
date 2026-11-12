local mem=manager.machine.devices[":maincpu"].spaces["program"]
local cpu=manager.machine.devices[":maincpu"]
local A=tonumber(os.getenv("ADDR_CF"),16)
local f=manager.machine.ioport.ports[":ctrl1:mdpad:PAD"].fields["P1 A"]
local n=0
emu.register_frame_done(function() n=n+1
 if n==300 then f:set_value(1) end
 if n==400 then f:set_value(0) end
 if n==250 or n==350 or n==500 or n==700 then print(string.format("v=%d cur_frame=%d",n,mem:read_u32(A))) end
end)
