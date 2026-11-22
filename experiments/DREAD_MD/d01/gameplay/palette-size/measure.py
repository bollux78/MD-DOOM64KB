from pathlib import Path
import sys,re,json,subprocess,hashlib
root=Path.cwd();tools=root/'dread-gameplay/experiments/DREAD_MD/d01/tools';sys.path.insert(0,str(tools));from pack_episode import Bank,entries,numbers,initializer,PAD
out=root/'dread-palette-size'
def measure(base):
 tex,spr=Bank(),Bank();column_tables={};columns=[];rows=[];pals=[]
 for i in range(1,10):
  path=base/f'E1M{i}';data=entries(path/'mapdata.c');pals.append(numbers(data['md_palette']));before=(len(tex.data)+len(columns)*4,len(spr.data))
  for field,blobname,bank,alignment in [('map_tex','tex_blob',tex,1),('map_sprites','spr_blob',spr,2)]:
   blob=bytes(numbers(data[blobname]));args=initializer(data[field])
   if field=='map_tex':
    for group in reversed(list(re.finditer(r'\{(\d+),(\d+),\d+,\d+,\{([\d,]+)\},\{[\d,]+\}\}',args))):
     width,h=1<<int(group[1]),1<<int(group[2]);stride=h+min(h,PAD)
     for start in map(int,group[3].split(',')):
      row=tuple(bank.add(blob[pos:pos+stride]) for pos in range(start,start+width*stride,stride))
      if row not in column_tables:column_tables[row]=len(columns);columns.extend(row)
   else:
    groups=list(re.finditer(r'\{([\d,]+)\}',args));lookup=sorted({int(v) for group in groups for v in group[1].split(',')})
    for start,end in zip(lookup,lookup[1:]+[len(blob)]):bank.add(blob[start:end],alignment)
  rows.append({'map':f'E1M{i}','texture_bank_growth':len(tex.data)+len(columns)*4-before[0],'sprite_bank_growth':len(spr.data)-before[1]})
 return {'textures':len(tex.data)+len(columns)*4,'sprites':len(spr.data),'column_count':len(columns),'rows':rows,'palettes_words':pals}
old=measure(root/'dread-gameplay-cache');new=measure(out)
# Sky must use each map's palette too. Convert to final bytes; count distinct complete blobs.
skies=[]
for n in range(1,10):
 d=out/f'E1M{n}';subprocess.run(['python3',str(tools/'gen_sky.py'),str(tools/'sky_e1doom_256x72_pal.png'),str(d/'mapdata.c'),str(d/'sky.c')],stdout=subprocess.DEVNULL,check=True)
 skies.append(bytes(numbers(entries(d/'sky.c')['sky_blob'])))
sky_old=len(skies[0]);sky_new=sum(len(x) for x in set(skies))
result={'baseline':old,'per_level':new,'delta_textures':new['textures']-old['textures'],'delta_sprites':new['sprites']-old['sprites'],'sky_baseline':sky_old,'sky_per_level':sky_new,'delta_sky':sky_new-sky_old,'palettes_baseline':32,'palettes_per_level':288,'delta_palette':256}
result['total_palette_assets_delta']=sum(result[k] for k in ['delta_textures','delta_sprites','delta_sky','delta_palette'])
(out/'size-results.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['baseline','per_level']},indent=2))
print('baseline',old['textures'],old['sprites']);print('per level',new['textures'],new['sprites'])
