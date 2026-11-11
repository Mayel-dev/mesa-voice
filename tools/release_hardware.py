"""Fail-closed KiCad fabrication export. Python 3.11+, KiCad CLI 9.0.6.
Usage: python tools/release_hardware.py --kicad-cli /path/kicad-cli
Only exports after ERC, offboard ERC and PCB DRC including parity are clean.
"""
import argparse,hashlib,json,os,shutil,subprocess,tempfile,zipfile,datetime
import xml.etree.ElementTree as ET
from pathlib import Path
from sexpr import read,children
ROOT=Path(__file__).resolve().parents[1]; H=ROOT/'hardware'; V=ROOT/'validation'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--kicad-cli',default=shutil.which('kicad-cli'));a=ap.parse_args()
    if not a.kicad_cli:ap.error('KiCad CLI required')
    # KiCad can tolerate content following an early root close: a blank drawing
    # then passes ERC. Validate the whole tree and expected symbol/pin counts.
    for name, count in [('mesa-voice',20),('wiring',6)]:
        tree=read(H/f'{name}.kicad_sch')
        instances=children(tree,'symbol')
        if tree[0]!='kicad_sch' or len(instances)!=count:
            raise RuntimeError(f'{name}: expected {count} placed symbols; found {len(instances)}')
        if name=='wiring':
            lib=children(tree,'lib_symbols')[0]
            pin_counts=[sum(len(children(unit,'pin')) for unit in children(sym,'symbol')) for sym in children(lib,'symbol')]
            if pin_counts != [2]*6 or len(children(tree,'wire'))!=6:
                raise RuntimeError('Harness drawing must contain six two-pin symbols and six wires')
    for library in ['Mesa.kicad_sym','Harness.kicad_sym','sym-lib-table','fp-lib-table']:
        read(H/library)
    logs=[]
    def run(*args):
        p=subprocess.run([a.kicad_cli,*map(str,args)],capture_output=True,text=True,encoding='utf-8',errors='replace')
        logs.append({'args':list(map(str,args)),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        (V/'kicad-commands.json').write_text(json.dumps(logs,indent=2),encoding='utf-8')
        if p.returncode:raise RuntimeError(f'KiCad failed: {args}\n{p.stdout}\n{p.stderr}')
        return p.stdout
    for sch,report in [('mesa-voice','erc'),('wiring','wiring-erc')]:
        run('sch','erc',H/f'{sch}.kicad_sch','--format','json','-o',V/f'{report}.json','--exit-code-violations')
        assert not any(s['violations'] for s in json.loads((V/f'{report}.json').read_text())['sheets'])
    board=H/'mesa-voice.kicad_pcb'
    run('pcb','drc',board,'--schematic-parity','--format','json','-o',V/'drc.json','--exit-code-violations')
    drc=json.loads((V/'drc.json').read_text())
    assert all(not drc[k] for k in ['violations','unconnected_items','schematic_parity'])
    run('sch','export','netlist',H/'mesa-voice.kicad_sch','--format','kicadxml','-o',H/'netlist.xml')
    run('sch','export','netlist',H/'wiring.kicad_sch','--format','kicadxml','-o',H/'wiring-netlist.xml')
    harness=ET.parse(H/'wiring-netlist.xml')
    actual={frozenset((n.get('ref'),n.get('pin')) for n in net.findall('node')) for net in harness.findall('./nets/net')}
    expected={frozenset(((a,pin),(b,pin))) for a,b in [('J1','SW1'),('J2','D1'),('JSPK','LS1')] for pin in ['1','2']}
    connectivity={'passed':actual==expected and len(harness.findall('./components/comp'))==6,
                  'connections':[sorted(v) for v in sorted(actual,key=lambda n:sorted(n))],
                  'schematic_sha256':hashlib.sha256((H/'wiring.kicad_sch').read_bytes()).hexdigest(),
                  'netlist_sha256':hashlib.sha256((H/'wiring-netlist.xml').read_bytes()).hexdigest()}
    (V/'wiring-connectivity.json').write_text(json.dumps(connectivity,indent=2)+'\n')
    if not connectivity['passed']:raise RuntimeError('Offboard harness connectivity mismatch')
    dest=H/'fabrication';dest.mkdir(exist_ok=True)
    run('pcb','export','gerbers',board,'-o',str(dest)+os.sep,'-l','F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts','--subtract-soldermask')
    run('pcb','export','drill',board,'-o',str(dest)+os.sep,'--excellon-separate-th','--generate-map','--map-format','svg')
    run('pcb','export','ipc2581',board,'-o',dest/'mesa-voice-ipc2581.xml')
    P=H/'previews';P.mkdir(exist_ok=True)
    for sch in ['mesa-voice','wiring']:
        run('sch','export','svg',H/f'{sch}.kicad_sch','-o',str(P)+os.sep)
    for name,layers in [('pcb-front','F.Cu,F.SilkS,Edge.Cuts'),('pcb-back','B.Cu,B.SilkS,Edge.Cuts'),('assembly','F.Fab,Edge.Cuts')]:
        run('pcb','export','svg',board,'-l',layers,'--mode-single','--page-size-mode','2','--exclude-drawing-sheet','--sketch-pads-on-fab-layers','-o',P/f'{name}.svg')
    files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(dest.iterdir()) if f.suffix in {'.gbr','.gbrjob','.gtl','.gbl','.gts','.gbs','.gto','.gbo','.gm1','.drl','.svg','.xml'}}
    manifest={'date':datetime.datetime.now(datetime.timezone.utc).date().isoformat(),'kicad_version':drc['kicad_version'],'pcb_sha256':hashlib.sha256(board.read_bytes()).hexdigest(),'schematic_sha256':hashlib.sha256((H/'mesa-voice.kicad_sch').read_bytes()).hexdigest(),'wiring_sha256':hashlib.sha256((H/'wiring.kicad_sch').read_bytes()).hexdigest(),'erc_violations':0,'drc_violations':0,'unconnected':0,'schematic_parity_violations':0,'physical_prototype_tested':False,'files_sha256':files}
    source_files=[f for f in H.rglob('*') if f.suffix in {'.kicad_sch','.kicad_pcb','.kicad_pro','.kicad_sym','.kicad_mod'} or f.name in {'sym-lib-table','fp-lib-table'}]
    manifest['source_sha256']={f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(source_files)}
    manifest['wiring_connections_checked']=6
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2))
    with zipfile.ZipFile(H/'mesa-voice-r1-fabrication.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in [*files,'manifest.json']:z.write(dest/name,name)
    print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
