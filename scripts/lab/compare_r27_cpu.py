from pathlib import Path
import json,re,subprocess,argparse,sys
root=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('dist',type=Path);p.add_argument('--harness',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);summary={}
for variant in ['base','group','fixed']:
 out=a.out/variant
 cmd=[sys.executable,str(root/'scripts/lab/run_r23_cpu_probe.py'),str(a.dist/('doom-md-r27-cpu-'+variant+'.elf')),'--harness',str(a.harness),'--out',str(out)]
 result=subprocess.run(cmd,capture_output=True,text=True)
 if result.returncode:
  print(result.stdout[-2500:]);print(result.stderr[-1200:]);raise SystemExit(result.returncode)
 d=json.loads((out/'report.json').read_text());assert d['symbols']['r24_cpu_error']==0
 items=[(int(a),int(b)) for a,b in re.findall(r'tag (\d+) cycles (\d+)',d['output'])]
 frames=[]
 for i,(tag,cycles) in enumerate(items):
  if 0x7000<=tag<0x7000+36 and len(frames)<36 and tag==0x7000+len(frames):
   frames.append(dict(index=tag-0x7000,hash=(items[i+1][0]<<16)|items[i+2][0],cycles=cycles))
 assert len(frames)==36,(variant,len(frames))
 bank,switches,reads,writes,romreads=map(int,re.search(r'mapper=(\d+) switches=(\d+) SRAM reads=(\d+) writes=(\d+) upper-ROM reads=(\d+)',d['output']).groups())
 assert bank==(variant=='fixed')
 summary[variant]=dict(frames=frames,frame_cycles=sum(f['cycles'] for f in frames),mapper_switches=switches,sram_reads=reads,sram_writes=writes,upper_rom_reads=romreads,final_mapper=bank)
 print(variant,'PASS',summary[variant]['frame_cycles'],'frame cycles',switches,'mapper writes')
assert [x['hash'] for x in summary['base']['frames']]==[x['hash'] for x in summary['group']['frames']]==[x['hash'] for x in summary['fixed']['frames']]
(a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('PASS all 36 frame hashes identical across baseline, grouped and fixed SRAM')
