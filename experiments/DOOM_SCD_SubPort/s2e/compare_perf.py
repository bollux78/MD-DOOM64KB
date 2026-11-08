#!/usr/bin/env python3
"""Compare emulated hardware VBlank phases; debugger/wall time excluded."""
import json,statistics,sys
from pathlib import Path
base,fast=map(Path,sys.argv[1:]);reports=[json.loads(p.read_text()) for p in (base,fast)]
labels=('wait_cd_swap','check_copy_backup','apply_world','apply_actors_player','render_dma','total')
def summarize(r):
    rows=r['rows'][2:96]
    assert all(len(x['profile_vblanks'])==6 and sum(x['profile_vblanks'][:5])==x['profile_vblanks'][5] for x in rows)
    total=sum(x['profile_vblanks'][5] for x in rows);assert total>0
    return dict(samples=len(rows),vblanks=total,emulated_fps=60*len(rows)/total,
                mean_phase_vblanks={name:statistics.mean(x['profile_vblanks'][i] for x in rows) for i,name in enumerate(labels)},
                mean_packet_bytes=statistics.mean(256+x['world_bytes']+x['actor_bytes'] for x in rows))
a,b=map(summarize,reports)
deep=json.loads((fast.parent/'live_deep_report.json').read_text())
assert all(x['checked'] for x in deep['rows'])
assert any(not x['checked'] for x in reports[1]['rows'])
assert all(x['checked']==(x['tic']%32==0) for x in reports[1]['rows'])
fields=('tic','x','y','angle','health','ammo','actors','world_bytes','actor_bytes')
assert [[x[k] for k in fields] for x in deep['rows']]==[[x[k] for k in fields] for x in reports[1]['rows']],'deep/production state trajectory diverged'
assert [x.get('frame_sha256') for x in deep['rows']]==[x.get('frame_sha256') for x in reports[1]['rows']],'deep/production rendered frames differ'

result=dict(baseline=a,optimized=b,speedup=a['vblanks']/b['vblanks'],bytes_reduction=1-b['mean_packet_bytes']/a['mean_packet_bytes'],
            scope='NTSC VBlank counter inside ROM. Emulator CPU-divider7; not debugger wall time, not measured console FPS or guaranteed35Hz.')
print('S2e PERFORMANCE',json.dumps(result,sort_keys=True),flush=True)
assert b['mean_packet_bytes']<a['mean_packet_bytes']*.6,'packet reduction missing'
assert b['vblanks']<a['vblanks']*.9,'less than10 percent emulated time improvement'
(fast.parent/'performance_comparison.json').write_text(json.dumps(result,indent=2))
