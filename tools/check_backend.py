"""Run the backend suite and real localhost mock transport, with source hashes."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
checks = []
for args, cwd, output in [
    ([sys.executable, '-m', 'pytest', '-q'], ROOT/'backend', 'backend-pytest.txt'),
    ([sys.executable, str(ROOT/'tools/check_transport.py')], ROOT, None),
]:
    p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, encoding='utf-8', errors='replace', timeout=120)
    if output:
        (ROOT/'validation'/output).write_text(p.stdout, encoding='utf-8')
    print(p.stdout)
    checks.append({'command':args, 'exit_code':p.returncode})
    if p.returncode:
        break
paths = sorted(set((ROOT/'backend').rglob('*.py')) | set((ROOT/'backend').glob('requirements*.txt')) |
               {ROOT/'backend/pytest.ini', ROOT/'tools/check_transport.py', Path(__file__)})
report = {'passed':len(checks)==2 and all(c['exit_code']==0 for c in checks),
          'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'commands':checks, 'real_ai_inference_tested':False,
          'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
                           if not any(v.startswith('.') or v=='__pycache__' for v in p.relative_to(ROOT).parts)}}
(ROOT/'validation/backend-checks.json').write_text(json.dumps(report, indent=2)+'\n')
raise SystemExit(0 if report['passed'] else 1)
