"""Native KiCad electrical drawing of the three off-carrier harnesses.
The amplifier screw terminals are already on the purchased module.
"""
from pathlib import Path
import uuid,json
R=Path(__file__).resolve().parents[1]; H=R/'hardware'
def u(s):return str(uuid.uuid5(uuid.NAMESPACE_DNS,'mesa-wiring/'+s))
def q(s):return json.dumps(s)
root=u('root'); lib=[]; inst=[]; ws=[]; texts=[]
def text(s,x,y,size=1.27):
    texts.append(f'(text {q(s)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left)) (uuid {u(s)}))')
def sym(ref,value,x,y,names,right,kind):
    px=12.7 if right else -12.7; angle=180 if right else 0
    pins=''.join(f'(pin passive line (at {px} {py} {angle}) (length 5.08) (name {q(name)} (effects (font (size 1 1)))) (number "{i}" (effects (font (size 1 1)))))' for i,(name,py) in enumerate(zip(names,[2.54,-2.54]),1))
    graphic='(rectangle (start -7.62 5.08) (end 7.62 -5.08) (stroke (width 0.254) (type default)) (fill (type background)))'
    lib.append(f'(symbol "Harness:{ref}" (pin_names (offset .7)) (in_bom no) (on_board no) (property "Reference" {q(ref)} (at 0 10.16 0) (effects (font (size 1.27 1.27)))) (property "Value" {q(value)} (at 0 7.62 0) (effects (font (size 1.27 1.27)))) (symbol "{ref}_0_1" {graphic}) (symbol "{ref}_1_1" {pins}))')
    inst.append(f'(symbol (lib_id "Harness:{ref}") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {u(ref)}) (property "Reference" {q(ref)} (at {x} {y-10.16} 0) (effects (font (size 1.27 1.27)))) (property "Value" {q(value)} (at {x} {y-7.62} 0) (effects (font (size 1.27 1.27)))) (instances (project "wiring" (path "/{root}" (reference {q(ref)}) (unit 1)))))')
    return [(x+px,y-2.54),(x+px,y+2.54)]
text('MESA VOICE R1 - OFFBOARD WIRING',20.32,17.78,2)
text('Carrier: mesa-voice.kicad_sch. These cables and loads are not extra carrier PCB parts.',20.32,25.4)
groups=[('J1','Carrier JST-XH J1',['PTT','GND'],'SW1','E-Switch PV6F240SS',['NO contact A','NO contact B'],55.88,'Normally open momentary switch. No electrical polarity.'),('J2','Carrier JST-XH J2',['LED_A','GND'],'D1','Kingbright WP710A10SGD',['Anode (+)','Cathode (-)'],99.06,'R2 = 1k is already on the carrier. Insulate the LED leads.'),('JSPK','U2 onboard screw terminal',['SPK+','SPK-'],'LS1','Visaton K40 8 ohm / 1W',['+ terminal','- terminal'],142.24,'BTL outputs: neither wire is ground. Twist pair, maximum 100mm.')]
for j,jv,jn,l,lv,ln,y,note in groups:
    a=sym(j,jv,76.2,y,jn,True,'terminal');b=sym(l,lv,175.26,y,ln,False,'load')
    for i,(pa,pb) in enumerate(zip(a,b)):
        ws.append(f'(wire (pts (xy {pa[0]} {pa[1]}) (xy {pb[0]} {pb[1]})) (stroke (width 0) (type default)) (uuid {u(j+str(i))}))')
    text(note,30.48,y+15.24)
text('Power: one 5V USB supply -> U1 USB-C. Antenna: A-02 -> U1 U.FL, gently aligned.',20.32,177.8)
text('Sense microphone: internal expansion connector, GPIO41 DATA / GPIO42 CLK; no extra cable.',20.32,182.88)
text('JSPK numbers on this drawing follow +/- markings, not manufacturer X1 pad numbering.',20.32,187.96)
H.joinpath('wiring.kicad_sch').write_text(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {root}) (paper "A4") (title_block (title "Mesa Voice - offboard harnesses") (date "2026-11-09") (rev "1.0")) (lib_symbols {"".join(lib)}) {"".join(inst+ws+texts)} (sheet_instances (path "/" (page "1"))))',encoding='utf-8')
H.joinpath('Harness.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor") '+''.join(s.replace('(symbol "Harness:','(symbol "',1) for s in lib)+')')
H.joinpath('sym-lib-table').write_text('(sym_lib_table (lib (name "Mesa")(type "KiCad")(uri "${KIPRJMOD}/Mesa.kicad_sym")(options "")(descr "Mesa R1")) (lib (name "Harness")(type "KiCad")(uri "${KIPRJMOD}/Harness.kicad_sym")(options "")(descr "Offboard wiring")))')
H.joinpath('wiring.kicad_pro').write_text(json.dumps({'meta':{'filename':'wiring.kicad_pro','version':1}},indent=2))
print('Generated wiring.kicad_sch')
