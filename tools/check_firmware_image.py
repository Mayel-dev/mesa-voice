"""Verify the successful validation build and the linked Xtensa image.

Run after tools/build_firmware.py, with pyelftools==0.33 installed.
This inspects files only; it does not execute firmware or test hardware.
"""
import hashlib
import json
from pathlib import Path
from elftools.elf.elffile import ELFFile

ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT/'validation/firmware-build.json').read_text())
if not report['passed'] or report['environment'] != 'validation':
    raise RuntimeError('A successful validation build is required')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

for name, sha in report['source_sha256'].items():
    if digest(ROOT/name) != sha:
        raise RuntimeError(f'Build source changed: {name}')
build = ROOT/'firmware/.pio/build/validation'
for name, evidence in report['artifacts'].items():
    if digest(build/name) != evidence['sha256']:
        raise RuntimeError(f'Build artifact changed: {name}')

required = ['_Z5setupv', '_Z4loopv', 'esp_wifi_connect', 'i2s_read', 'i2s_write',
            '_ZN10WiFiClient7connectEPKcti', '_ZN10WiFiClient5writeEPKhj',
            '_ZN10WiFiClient4readEPhj']
with (build/'firmware.elf').open('rb') as f:
    elf = ELFFile(f)
    symbols = {s.name: int(s.entry.st_size) for s in elf.get_section_by_name('.symtab').iter_symbols()
               if s.entry.st_shndx != 'SHN_UNDEF' and s.entry.st_size > 0}
    machine = elf.header.e_machine
    found = {name: symbols.get(name, 0) for name in required}

result = {'passed': machine == 'EM_XTENSA' and all(found.values()),
          'machine': machine, 'required_linked_symbols_bytes': found,
          'source_sha256': report['source_sha256'],
          'artifacts': report['artifacts'],
          'build_report_sha256': digest(ROOT/'validation/firmware-build.json'),
          'hardware_tested': False,
          'scope': 'ELF structure, linked routines and hashes; not execution or runtime correctness'}
(ROOT/'validation/firmware-image.json').write_text(json.dumps(result, indent=2)+'\n')
print(f'Xtensa image verified: {result["passed"]}; {len(found)} required linked symbols')
raise SystemExit(0 if result['passed'] else 1)
