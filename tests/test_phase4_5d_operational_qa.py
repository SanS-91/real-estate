from pathlib import Path
import json, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
def main():
 tmp=Path(tempfile.mkdtemp(prefix='p45d-'))/'qa.json'
 cp=subprocess.run([sys.executable,str(ROOT/'scripts/phase45_operational_qa.py'),'--output',str(tmp)],cwd=ROOT,capture_output=True,text=True)
 assert cp.returncode==0,cp.stdout+'\n'+cp.stderr
 out=json.loads(tmp.read_text(encoding='utf-8')); assert out['status']=='pass'; assert out['record_count']==18
 wf=(ROOT/'.github/workflows/data-freshness-check.yml').read_text(encoding='utf-8'); assert 'phase45_operational_qa.py' in wf
 print('Phase 4.5D operational QA tests PASS')
if __name__=='__main__': main()
