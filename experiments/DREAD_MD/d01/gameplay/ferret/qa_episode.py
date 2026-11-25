from qa_support import *
rows=[]
for mapid in range(9):
 g=v.Game(VARIANT);g.play(mapid);g.put('cheat_god',1);g.put('fcap',0)
 before=g.rd('vints');g.e.step(180,capture=True);assert g.rd('vints')!=before
 assert g.rd('r_vh')==72
 assert g.rd('r_vw') in [80,160]
 img=g.e.screenshot();assert len(img.getcolors(320*224) or [])>=8,'black/blank output'
 g.shot('map-'+str(mapid+1));rows.append({'map':mapid+1,'width':g.rd('r_vw'),'height':g.rd('r_vh'),'pass':True});g.e.close()
(v.ROOT/'episode-nine-maps.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
