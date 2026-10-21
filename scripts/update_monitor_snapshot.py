"""Publish public monitor fallback data using the workflow's temporary token."""
import datetime,json,os,urllib.request
from pathlib import Path
root='https://api.github.com/repos/'+os.environ.get('GITHUB_REPOSITORY','bollux78/MD-DOOM64KB')
def get(path):
 req=urllib.request.Request(root+path,headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'doom-md-development-monitor'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
runs=get('/actions/runs?per_page=35');commits=get('/commits?sha=fullscreen&per_page=8');branches=get('/branches?per_page=100');artifacts=get('/actions/artifacts?per_page=100')
data=dict(generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),runs=runs,commits=commits,branches=branches,artifacts=artifacts)
Path('docs/monitor/data.json').write_text(json.dumps(data),encoding='utf-8')
print('Public snapshot generated:',len(runs.get('workflow_runs',[])),'runs')
