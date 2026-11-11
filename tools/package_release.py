"""Validate evidence against current files, then create a source release archive.

Does not run tools, execute firmware, publish, upload, or claim physical validation.
Regenerate changed-area reports before packaging. No third-party binary cache is shipped.
"""
import datetime
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
V = ROOT/'validation'
checks = []

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(name, condition):
    if not condition:
        raise RuntimeError(name)
    checks.append(name)

def read(relative):
    return json.loads((ROOT/relative).read_text(encoding='utf-8'))

def hashes(mapping, base=ROOT):
    for relative, expected in mapping.items():
        path = base/relative
        require('Current hash: '+path.relative_to(ROOT).as_posix(), path.is_file() and sha(path)==expected)

def main():
    fab = read('hardware/fabrication/manifest.json')
    hashes(fab['source_sha256'])
    hashes(fab['files_sha256'], ROOT/'hardware/fabrication')
    require('Fabrication guards', all(fab[k]==0 for k in ['erc_violations','drc_violations','unconnected','schematic_parity_violations']))
    for file in ['erc.json','wiring-erc.json']:
        require('ERC clean: '+file, all(not s['violations'] for s in read('validation/'+file)['sheets']))
    drc = read('validation/drc.json')
    require('DRC and parity clean', all(not drc[k] for k in ['violations','unconnected_items','schematic_parity']))
    wire = read('validation/wiring-connectivity.json')
    require('Six harness connections checked', wire['passed'] and len(wire['connections'])==6)
    hashes({'hardware/wiring.kicad_sch':wire['schematic_sha256'], 'hardware/wiring-netlist.xml':wire['netlist_sha256']})
    with zipfile.ZipFile(ROOT/'hardware/mesa-voice-r1-fabrication.zip') as archive:
        expected = set(fab['files_sha256']) | {'manifest.json'}
        require('Fabrication ZIP inventory', set(archive.namelist())==expected)
        require('Fabrication ZIP CRC', archive.testzip() is None)
        for name in expected:
            require('Fabrication ZIP matches: '+name, archive.read(name)==(ROOT/'hardware/fabrication'/name).read_bytes())

    interfaces = read('validation/interfaces.json')
    require('Interfaces passed', interfaces['passed'] and all(c['passed'] for c in interfaces['checks']))
    hashes(interfaces['files_sha256'])
    mechanical = read('validation/mechanical-meshes.json')
    require('Mechanical checks passed', mechanical['passed'] and mechanical['nominal_component_fit']['passed'])
    hashes({'mechanical/enclosure.scad':mechanical['source_sha256']})
    for name, part in mechanical['parts'].items():
        require('Mesh checks: '+name, all(part['checks'].values()))
        hashes({f'mechanical/stl/{name}.stl':part['sha256']})

    backend = read('validation/backend-checks.json')
    require('Backend suite and transport passed', backend['passed'] and all(c['exit_code']==0 for c in backend['commands']))
    hashes(backend['source_sha256'])
    transport = read('validation/transport.json')
    require('Localhost mock WAV contract', transport['passed'] and transport['mode']=='mock' and transport['canonical_wav'])
    require('Pytest evidence', re.search(r'\b41 passed\b', (V/'backend-pytest.txt').read_text(encoding='utf-8')) is not None)
    host = read('validation/firmware-host.json')
    require('Host C++ test passed', host['passed'] and host['test_exit_code']==0)
    hashes(host['source_sha256'])
    hashes({'validation/firmware-host-test.txt':host['log_sha256']})
    firmware = read('validation/firmware-build.json')
    require('Full firmware build passed', firmware['passed'] and firmware['environment']=='validation' and firmware['exit_code']==0)
    hashes(firmware['source_sha256'])
    image = read('validation/firmware-image.json')
    require('Xtensa image inspected', image['passed'] and image['machine']=='EM_XTENSA')
    hashes(image['source_sha256'])
    hashes({'validation/firmware-build.json':image['build_report_sha256']})
    require('Image matches build artifacts', image['artifacts']==firmware['artifacts'])
    # The source release deliberately omits .pio artifacts; verify them when present.
    for name, evidence in firmware['artifacts'].items():
        artifact = ROOT/'firmware/.pio/build/validation'/name
        if artifact.exists():
            require('Local build artifact: '+name, sha(artifact)==evidence['sha256'])
    refs = read('hardware/references/manifest.json')
    hashes({name:details['sha256'] for name,details in refs['files'].items()},ROOT/'hardware/references')

    files = release_files()
    for file in files:
        if file.suffix=='.md':
            for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',file.read_text(encoding='utf-8')):
                if '://' in target or target.startswith('#'):
                    continue
                path = file.parent/target.split('#')[0].strip('<>')
                require(f'Local link in {file.relative_to(ROOT)}: {target}',path.exists())
    report = {'passed':True,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'status':'experimental_first_article_design', 'physical_hardware_tested':False,
              'real_ai_inference_tested':False, 'checks':checks,
              'evidence_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in sorted(V.iterdir())
                                 if f.is_file() and f.name!='release.json'}}
    (V/'release.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    files = release_files()
    (ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha(f)}  {f.relative_to(ROOT).as_posix()}\n' for f in files),encoding='utf-8')
    files.append(ROOT/'SHA256SUMS.txt')
    archive = ROOT.parent/'mesa-voice-r1-source.zip'
    temporary = archive.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(files):
            z.write(f, 'mesa-voice/'+f.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(temporary) as z:
        if z.testzip() is not None or len(z.namelist())!=len(files):
            raise RuntimeError('Source ZIP integrity check failed')
        for f in files:
            if hashlib.sha256(z.read('mesa-voice/'+f.relative_to(ROOT).as_posix())).hexdigest()!=sha(f):
                raise RuntimeError('Source ZIP content mismatch: '+str(f))
    temporary.replace(archive)
    archive.with_suffix('.zip.sha256').write_text(f'{sha(archive)}  {archive.name}\n',encoding='utf-8')
    print(json.dumps({'passed':True,'checks':len(checks),'files':len(files),'archive':str(archive),
                      'bytes':archive.stat().st_size,'sha256':sha(archive)},indent=2))

def release_files():
    excluded = {'.git','.pio','.pio-core','.pytest_cache','.venv','__pycache__','models','work'}
    names = {'secrets.h','.env','compile_commands.json','SHA256SUMS.txt'}
    result = []
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(p in excluded or p.endswith('-backups') for p in rel.parts):
            continue
        if path.name in names or path.suffix in {'.pyc','.pyo','.kicad_prl','.lck','.obj','.exe'}:
            continue
        if path.name.startswith('~') or path.name== 'test_audio_protocol':
            continue
        result.append(path)
    return sorted(result)

if __name__=='__main__':
    main()
