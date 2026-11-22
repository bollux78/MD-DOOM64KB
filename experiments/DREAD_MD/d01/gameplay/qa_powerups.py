from qa_support import *
g=fixture(0);out=[]
for name,val,tint in [('invuln',1800,3),('suit',3600,4),('berserk_red',1200,5),('berserk_red',700,6),('berserk_red',300,7),('bright',7200,0),('invisible',3600,0)]:
 for n in ['invuln','suit','berserk_red','bright','invisible']:g.put(n,0)
 g.put(name,val);g.e.step(110,capture=True);actual=g.rd('displayed_tint',1);row={'power':name,'input_vblanks':val,'remaining':g.rd(name),'tint':actual,'expected':tint,'fullbright':g.rd('r_fullbright'),'weapon_fuzz':g.rd('weapon_fuzz')};out.append(row);g.shot(name+'-'+str(val));assert actual==tint,row
 if name=='bright':assert g.rd('r_fullbright')
 if name=='invisible':assert g.rd('weapon_fuzz')==1
for name in ['invuln','suit','berserk_red','bright','invisible']:g.put(name,1)
g.e.step(110,capture=True);out.append({'expired_tint':g.rd('displayed_tint',1),'expired_fuzz':g.rd('weapon_fuzz'),'fullbright':g.rd('r_fullbright')});assert g.rd('displayed_tint',1)==0 and g.rd('weapon_fuzz')==0 and g.rd('r_fullbright')==0
g.shot('powers-expired');g.e.close();print(json.dumps(out,indent=2))
# Actual invisibility pickup in E1M3, including its timer initialization.
g=fixture(2);warp(g,256,-2752);g.e.step(60,capture=True);print('actual E1M3 invis pickup',g.rd('invisible'),g.rd('weapon_fuzz'));assert g.rd('invisible')>3400 and g.rd('weapon_fuzz')==1;g.shot('invisibility-pickup');g.e.close()
