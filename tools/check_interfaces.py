"""Cross-check KiCad physical/electrical interfaces against manufacturer data,
firmware GPIO constants, enclosure parameters and BOM. Requires KiCad Python.
This supplements ERC/DRC; it cannot replace a physical assembly test.
"""
from pathlib import Path
import ast
import csv
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
import pcbnew as p

ROOT = Path(__file__).resolve().parents[1]
board = p.LoadBoard(str(ROOT/'hardware/mesa-voice.kicad_pcb'))
fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
checks = []

def check(name, good, evidence):
    checks.append({'name': name, 'passed': bool(good), 'evidence': evidence})

def xy(point):
    return (p.ToMM(point.x), p.ToMM(point.y))

def near(a, b):
    return all(abs(x-y) < 0.001 for x, y in zip(a, b))

def pad(ref, number):
    return next(v for v in fps[ref].Pads() if v.GetNumber() == str(number))

def net(ref, number):
    return pad(ref, number).GetNetname().lstrip('/')

# Seeed official XIAO-ESP32-S3-DIP footprint, viewed from top with USB north.
for n in range(1, 15):
    want = (-7.62, -7.62 + (n-1)*2.54) if n <= 7 else (7.62, 7.62 - (n-8)*2.54)
    origin = xy(fps['U1'].GetPosition())
    actual = tuple(a-b for a,b in zip(xy(pad('U1', n).GetPosition()), origin))
    check(f'XIAO pad {n} position', near(actual, want), {'actual_mm': actual, 'manufacturer_mm': want})

expected = {1:'PTT', 2:'LED_GPIO', 4:'MUTE', 5:'BCLK_SRC', 6:'LRCLK_SRC', 7:'DIN_SRC', 12:'+3V3', 13:'GND', 14:'+5V_USB'}
for n, name in expected.items():
    check(f'XIAO pad {n} net', net('U1', n) == name, net('U1', n))

# Verify amp ordering directly from the archived manufacturer Eagle board, not
# from the carrier generator. Eagle JP1 rotation R180 and Y-up -> top-view with
# header north give the same relative X positions as its unrotated pad list.
eagle = ET.parse(ROOT/'hardware/references/adafruit-3006.brd')
elements = {e.get('name'): e for e in eagle.findall('.//elements/element')}
header = elements['JP1']
pkg = next(e for e in eagle.iter('package') if e.get('name') == header.get('package'))
signal_map = {'VDD':'+5V_AMP', 'GND':'GND', 'SD_MODE':'AMP_SD', 'GAIN':'AMP_GAIN', 'DIN':'DIN', 'BCLK':'BCLK', 'LRCLK':'LRCLK'}
check('Adafruit source orientation', header.get('rot') == 'R180', header.attrib)
for s in eagle.findall('.//signals/signal'):
    for contact in s.findall('contactref'):
        if contact.get('element') == 'JP1':
            n = contact.get('pad')
            check(f'Adafruit pin {n} net', net('U2', n) == signal_map[s.get('name')], {'source':s.get('name'), 'carrier':net('U2', n)})
for a in pkg.findall('pad'):
    n = a.get('name')
    origin = xy(fps['U2'].GetPosition())
    actual = tuple(a-b for a,b in zip(xy(pad('U2', n).GetPosition()), origin))
    check(f'Adafruit pad {n} pitch', near(actual, (float(a.get('x')), 0)), actual)
holes = sorted(xy(a.GetPosition()) for a in fps['U2'].Pads() if not a.GetNumber())
origin = xy(fps['U2'].GetPosition())
source_holes = sorted((origin[0]-(float(e.get('x'))-float(header.get('x'))),
                       origin[1]+float(e.get('y'))-float(header.get('y')))
                      for e in elements.values() if e.get('package') == 'MOUNTINGHOLE_2.5_PLATED')
check('Amp mounting hole positions', len(holes)==len(source_holes)==2 and all(near(a,b) for a,b in zip(holes, source_holes)), holes)

source = (ROOT/'firmware/src/main.cpp').read_text()
for name, value in {'PTT_PIN':1, 'LED_PIN':2, 'MUTE_PIN':4, 'TX_BCLK':5, 'TX_LRCLK':6, 'TX_DATA':43, 'MIC_CLK':42, 'MIC_DATA':41}.items():
    found = re.search(r'\b'+name+r'\s*=\s*(\d+)', source)
    check(f'Firmware GPIO {name}', found and int(found[1]) == value, value)
for ref, a, b in [('R5','BCLK_SRC','BCLK'), ('R6','LRCLK_SRC','LRCLK'), ('R7','DIN_SRC','DIN'),
                  ('R3','+3V3','MUTE'), ('R4','+5V_AMP','AMP_GAIN'), ('F1','+5V_USB','+5V_AMP'),
                  ('J1','PTT','GND'), ('J2','LED_A','GND')]:
    check(f'Interface {ref}', (net(ref,1),net(ref,2)) == (a,b), [a,b])
check('Mute transistor G S D', [net('Q1',n) for n in (1,2,3)] == ['MUTE','GND','AMP_SD'], [net('Q1',n) for n in (1,2,3)])

scad = (ROOT/'mechanical/enclosure.scad').read_text()
def param(name):
    return ast.literal_eval(re.search(r'\b'+name+r'\s*=\s*([^;]+);', scad)[1])
carrier_holes = sorted(xy(fps['H'+str(n)].GetPosition()) for n in range(1,5))
check('PCB holes match enclosure bosses', carrier_holes == sorted(map(tuple,param('pcb_holes'))), carrier_holes)
check('PCB size matches enclosure', near(param('pcb_size'), (64,54)), param('pcb_size'))
check('PCB height / amp screw floor clearance', param('pcb_z')+1.6+11+1.6-18 > param('floor_t'), 'M2.5x18 tip above floor with 11 mm spacer')
button, speaker = param('button'), param('speaker')
gap = math.dist(button, speaker) - param('button_nut_d')/2 - param('speaker_clamp_outer_d')/2
check('Button nut vs speaker pocket', gap > 1, {'nominal_gap_mm':round(gap,3)})
gap = math.dist(button,param('led')) - param('button_nut_d')/2 - 1.9
check('Button nut vs LED flange', gap > 1, {'nominal_gap_mm':round(gap,3)})
for q in param('case_screws'):
    gap = math.dist(button,q) - param('button_nut_d')/2 - 4
    check('Button nut vs case boss '+str(q), gap > 1, {'nominal_gap_mm':round(gap,3)})
check('USB overmould opening clearance', param('usb_w') >= 18 and param('usb_h') >= 14, '16x12 mm plug envelope, at least 1 mm each side')

bom = list(csv.DictReader((ROOT/'BOM.csv').open(encoding='utf-8-sig')))
refs = {r['References'] for r in bom}
needed = {r for r in fps if not r.startswith(('TP','H'))}
check('Every populated carrier reference in BOM', needed <= refs, sorted(needed-refs))
check('BOM unique rows and positive quantities', len(refs)==len(bom) and all(int(r['Qty'])>0 for r in bom), len(bom))

report = {'passed':all(c['passed'] for c in checks), 'checks':checks, 'physical_fit_tested':False,
          'sources':'See docs/sources.md; Adafruit Eagle pin/hole data parsed directly',
          'files_sha256':{str(f.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in
                          [ROOT/'hardware/mesa-voice.kicad_pcb',ROOT/'mechanical/enclosure.scad',ROOT/'firmware/src/main.cpp',ROOT/'BOM.csv']}}
(ROOT/'validation/interfaces.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'{len(checks)} interface checks; passed={report["passed"]}')
for c in checks:
    if not c['passed']: print(c)
raise SystemExit(0 if report['passed'] else 1)
