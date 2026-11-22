from pathlib import Path
import argparse,json,collections
import numpy as np
p=argparse.ArgumentParser();p.add_argument('results',type=Path);a=p.parse_args()
MASTER=53693175;FRAME=3420*262
summary=[]
for folder in sorted(a.results.iterdir()):
 if not (folder/'probes.json').exists():continue
 meta=json.loads((folder/'summary.json').read_text());events=json.loads((folder/'probes.json').read_text());clock=lambda x:(x[0]-1)*FRAME+x[1]
 def phase(start,end):
  pending=None;dur=[]
  for e in events:
   if e[2]==start:pending=clock(e)
   elif e[2]==end and pending is not None:dur.append(clock(e)-pending);pending=None
  if not dur:return None
  d=np.array(dur)*1000/MASTER
  return {'count':len(d),'mean_ms':float(d.mean()),'min_ms':float(d.min()),'max_ms':float(d.max())}
 transfer=0x7e3ea if any(e[2]==0x7e3ea for e in events) else 0x7e368
 starts=[clock(e) for e in events if e[2]==transfer];d=np.diff(starts)
 # Front-buffer publication is the VRAM name-table DMA, not reg2: the base stays E000.
 dmas=json.loads((folder/'dmas.json').read_text());publ=[(x[0]-1)*FRAME+x[1] for x in dmas if x[3]==0xe100 and x[4]==1152];intervals=np.diff(publ)
 cycles=np.load(folder/'profile.npz')['cycles'];total=int(cycles.sum())
 lines=json.loads((folder/'vdp-cpu-writes-scanlines.json').read_text()) if (folder/'vdp-cpu-writes-scanlines.json').exists() else []
 row={'variant':folder.name,'video_frames':meta['video_frames'],'sram_mode':meta['sram_mode'],'publication_intervals':len(intervals),'publication_fps':float(MASTER/intervals.mean()),'frame_ms':float(intervals.mean()*1000/MASTER),'frame_ms_min':float(intervals.min()*1000/MASTER),'frame_ms_max':float(intervals.max()*1000/MASTER),'conversion_entry_fps':float(MASTER/d.mean()),'phases_inclusive':{name:phase(s,e) for name,s,e in [('visible_list',0x7e150,0x7e160),('walls',0x7e132,0x7e13e),('sprites',0x7e140,0x7e14e),('scene_total',0x86c70,0x7e45a),('cpu_vdp_convert',0x7e368,0x7e3e8),('ram_convert',0x7e3ea,0x7e444)]},'dma_words_total':sum(x[4] for x in dmas),'world_dma_count':sum(0x200000<=x[2]<0x210000 and x[5]&15==1 for x in dmas),'palette0_viewport':None,'profile_charged_percent':{'convert_direct':float(cycles[0x7e368//2:0x7e3ea//2].sum()*100/total),'convert_ram':float(cycles[0x7e3ea//2:0x7e446//2].sum()*100/total),'vblank_wait':float(cycles[0x859da//2:0x859e6//2].sum()*100/total),'dma_trigger_instruction_7f420':float(cycles[0x7f420//2]*100/total)},'cpu_vdp_long_writes':sum(lines),'cpu_vdp_long_writes_active_lines_0_223':sum(lines[:224])}
 attrs=json.loads((folder/'spawn/plane-A-attributes.json').read_text());row['palette0_viewport']=dict(collections.Counter(str((v>>13)&3) for line in attrs[2:20] for v in line[:40]))
 summary.append(row)
(a.results/'measurements.json').write_text(json.dumps(summary,indent=2)+'\n')
for row in summary:print(row['variant'],round(row['publication_fps'],4),round(row['frame_ms'],3),[(k,round(v['mean_ms'],3)) for k,v in row['phases_inclusive'].items() if v])
