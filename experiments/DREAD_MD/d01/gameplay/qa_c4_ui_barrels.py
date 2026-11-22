from qa_support import *
# Title and menu look.
g=v.Game(VARIANT);g.shot('opening');g.press(3);g.shot('opening-menu');g.e.close()
g=v.Game(VARIANT);g.play();g.press(3);g.shot('pause')
for _ in range(5):g.press(5)
g.press(1);g.shot('cheats-off');g.press(1);print('god',g.rd('cheat_god'));g.press(5);g.press(1);g.shot('cheats-on');print('kfa',g.rd('cheat_kfa'),'weapons',g.rd('owned_weapons'),'keys',g.rd('player_keys'));g.press(1);print('kfa off',g.rd('cheat_kfa'),'weapons',g.rd('owned_weapons'));g.press(0);g.press(3);g.shot('after-menu');g.e.close()
# Explode first E1M1 barrel using actual weapon inputs; inspect the sparse state.
g=fixture(0);b=g.raw('barrels');n=g.rd('nbarrels');ti=int.from_bytes(b[:2],'big');rom=(v.ROOT/VARIANT/'EPISODE.bin').read_bytes();
# WAD first barrel poses found by enumerating map things and the converter's sorted table.
bar=next(t for t in things(0) if t[3]==2035 and t[4]&2 and not t[4]&16);x,y=bar[:2]
warp(g,x-80,y,0);g.e.step(60);print('barrels',n,'before',g.raw('barrels')[:8].hex());g.e.step(180,1);g.put('bench_req',0);g.e.step(45,capture=True);g.shot('barrel-explosion');print('barrels after',g.raw('barrels')[:48].hex());g.e.step(100);g.shot('barrel-gone');g.e.close()
