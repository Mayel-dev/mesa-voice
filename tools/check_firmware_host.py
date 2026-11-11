"""Compile and execute the portable audio protocol tests with an installed C++ compiler.

On Windows, run in Developer PowerShell with MSVC's environment initialized.
Otherwise uses c++; --compiler overrides selection. Does not test ESP32 hardware.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument('--compiler', default=shutil.which('cl') if os.name=='nt' else shutil.which('c++'))
args = ap.parse_args()
if not args.compiler:
    ap.error('No C++ compiler found; initialize a compiler environment or use --compiler')
msvc = Path(args.compiler).name.lower() in {'cl', 'cl.exe'}
probe = subprocess.run([args.compiler] + ([] if msvc else ['--version']), capture_output=True,
                       text=True, errors='replace', timeout=15)
version_lines = (probe.stdout + probe.stderr).strip().splitlines()
version = next((line for line in version_lines if 'Compiler Version' in line), version_lines[0])
log = version + '\n'
with tempfile.TemporaryDirectory(prefix='mesa-protocol-') as directory:
    exe = Path(directory)/('test.exe' if os.name=='nt' else 'test')
    source = ROOT/'firmware/test/test_audio_protocol.cpp'
    include = ROOT/'firmware/include'
    flags = (['/nologo','/EHsc','/W4','/WX','/std:c++17','/I'+str(include),str(source),
              '/Fo'+str(Path(directory)/'test.obj'),'/Fe'+str(exe)] if msvc else
             ['-std=c++17','-Wall','-Wextra','-Werror','-I',str(include),str(source),'-o',str(exe)])
    build = subprocess.run([args.compiler,*flags], cwd=directory, capture_output=True,
                           text=True, errors='replace', timeout=60)
    log += build.stdout + build.stderr
    run_code = None
    if build.returncode == 0:
        run = subprocess.run([str(exe)], capture_output=True, text=True, errors='replace', timeout=15)
        log += run.stdout + run.stderr
        run_code = run.returncode
passed = build.returncode==0 and run_code==0 and 'PASS:' in log
(ROOT/'validation/firmware-host-test.txt').write_text(log,encoding='utf-8')
files = [source,ROOT/'firmware/include/audio_protocol.h',Path(__file__)]
report = {'passed':passed,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'compiler':version,'compile_exit_code':build.returncode,'test_exit_code':run_code,
          'source_sha256':{f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
          'log_sha256':hashlib.sha256((ROOT/'validation/firmware-host-test.txt').read_bytes()).hexdigest(),
          'pcm_inputs_checked':65536,'hardware_tested':False}
(ROOT/'validation/firmware-host.json').write_text(json.dumps(report,indent=2)+'\n')
print(log)
raise SystemExit(0 if passed else 1)
