"""Compile the ESP32 validation image and record actual tool output, without secrets.

Use this Python interpreter's PlatformIO installation. No upload or hardware access.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import datetime

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--core-dir', type=Path)
    args = parser.parse_args()
    env = os.environ.copy()
    if args.core_dir:
        env['PLATFORMIO_CORE_DIR'] = str(args.core_dir.resolve())
    report_dir = ROOT / 'validation'
    report_dir.mkdir(exist_ok=True)
    cmd = [sys.executable, '-m', 'platformio', 'run', '-d', str(ROOT / 'firmware'), '-e', 'validation']
    with (report_dir / 'firmware-build.log').open('w', encoding='utf-8') as log:
        if args.core_dir and os.name == 'nt':
            tc = args.core_dir.resolve()/'packages/toolchain-xtensa-esp32s3'
            env['PATH'] = str(tc/'bin') + os.pathsep + env['PATH']
            for rel, flags in [('bin/xtensa-esp32s3-elf-g++.exe', ['-print-prog-name=cc1plus']),
                               ('libexec/gcc/xtensa-esp32s3-elf/8.4.0/cc1plus.exe', ['--version']),
                               ('bin/xtensa-esp32s3-elf-as.exe', ['--version'])]:
                try:
                    probe = subprocess.run([str(tc/rel), *flags], env=env, capture_output=True,
                                           text=True, encoding='utf-8', errors='replace', timeout=15)
                    note = f'Preflight {rel}: exit={probe.returncode}\n{probe.stdout}{probe.stderr}\n'
                except OSError as exc:
                    note = f'Preflight {rel}: {exc}\n'
                log.write(note)
                print(note, flush=True)
        process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace')
        for line in process.stdout:
            print(line, end='', flush=True)
            log.write(line)
        code = process.wait()
    sources = [ROOT/'firmware/platformio.ini', *sorted((ROOT/'firmware/src').glob('*.cpp')),
               ROOT/'firmware/include/audio_protocol.h', ROOT/'firmware/include/config.example.h',
               ROOT/'firmware/include/config.validation.h']
    artifacts = {}
    if code == 0:
        build = ROOT/'firmware/.pio/build/validation'
        for name in ['firmware.bin', 'firmware.elf', 'bootloader.bin', 'partitions.bin']:
            p = build/name
            if not p.is_file():
                raise RuntimeError(f'Build reported success but missing {name}')
            artifacts[name] = {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    report = {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'passed': code == 0, 'exit_code': code, 'environment': 'validation',
              'credentials_included': False, 'hardware_tested': False,
              'source_sha256': {str(p.relative_to(ROOT)).replace('\\','/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
              'artifacts': artifacts}
    (report_dir/'firmware-build.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return code

if __name__ == '__main__':
    raise SystemExit(main())
