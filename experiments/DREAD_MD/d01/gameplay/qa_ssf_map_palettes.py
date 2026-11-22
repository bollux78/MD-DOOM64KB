from qa_support import *
reports=[]
for m in range(9):
 g=v.Game(VARIANT);g.play(m);g.put('nactors',0);g.e.step(60,capture=True);view=struct.unpack('>iihH',g.raw('view',12));src=Path(os.environ.get('DREAD_TEST_PALETTE_MAPS','dread-palette-size'))/f'E1M{m+1}'/'mapdata.c';text=src.read_text();body=re.search(r'md_palette\[1\]\[16\] = \{\{([^}]+)',text)[1];expected=struct.pack('>16H',*[int(x,16) for x in body.split(',')]);actual=g.raw('scene_pal')[:32];assert actual==expected,(m,actual.hex(),expected.hex());assert g.rd('selected_map')==m;g.shot('map-'+str(m+1));reports.append({'map':m+1,'view':view,'palette_matches':True});g.e.close()
print(json.dumps(reports,indent=2))
