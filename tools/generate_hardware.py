"""Generate Mesa Voice R1 with KiCad 9 pcbnew. No external symbol libraries.

The carrier intentionally uses manufacturer assembled RF/microphone/amplifier
modules. Pin mapping and physical pad geometry are explicit and auditable.
Run using KiCad's bundled Python, from any working directory.
"""
from pathlib import Path
import json, uuid, heapq, math, csv
import numpy as np
import pcbnew as p

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / 'hardware'
HW.mkdir(exist_ok=True)
LIB = HW / 'Mesa.pretty'
LIB.mkdir(exist_ok=True)
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL, 'mesa-voice-r1/' + s))
def mm(x): return p.FromMM(float(x))
def pt(x,y): return p.VECTOR2I(mm(x),mm(y))
def q(s): return json.dumps(str(s),ensure_ascii=False)
def layers(*ids):
    s=p.LSET()
    for i in ids:s.AddLayer(i)
    return s

# pad tuple: number, relative x/y, size x/y, drill (0=SMD), logical pin name/type
def pad(n,x,y,sx=1.8,sy=1.8,d=1.0,name='',typ='passive'):
    return dict(n=str(n),x=x,y=y,sx=sx,sy=sy,d=d,name=name or str(n),typ=typ)
components=[]
def comp(ref,value,xy,sch,pads,nets,body,mpn,desc):
    c=dict(ref=ref,value=value,xy=xy,sch=sch,pads=pads,nets={str(k):v for k,v in nets.items()},body=body,mpn=mpn,desc=desc,uuid=uid(ref),fp='Mesa:'+ref)
    components.append(c); return c

# Official XIAO side header pitch 2.54 mm; row spacing 15.24 mm.
# Viewed from TOP, USB points towards the NORTH (negative Y).
xp=[]
left=['D0_GPIO1','D1_GPIO2','D2_GPIO3','D3_GPIO4','D4_GPIO5','D5_GPIO6','D6_GPIO43']
right=['D7_GPIO44','D8_GPIO7','D9_GPIO8','D10_GPIO9','3V3','GND','5V_USB']
for i,n in enumerate(left): xp.append(pad(i+1,-7.62,-7.62+2.54*i,name=n,typ='bidirectional'))
for i,n in enumerate(right): xp.append(pad(i+8,7.62,7.62-2.54*i,name=n,typ='power_out' if i in (4,6) else 'passive' if i==5 else 'bidirectional'))
comp('U1','XIAO ESP32S3 Sense',(15,9),(58,52),xp,{1:'PTT',2:'LED_GPIO',4:'MUTE',5:'BCLK_SRC',6:'LRCLK_SRC',7:'DIN_SRC',12:'+3V3',13:'GND',14:'+5V_USB'},(-8.9,-10.5,8.9,10.5),'Seeed 113991115','Includes USB-C, regulator, PSRAM, PDM microphone expansion; remove camera')
# Amp header north edge; module body extends towards +Y. Correct order is
# VIN,GND,SD,GAIN,DIN,BCLK,LRC from left to right when terminal block is south.
anames=['VIN','GND','SD_MODE','GAIN','DIN','BCLK','LRC']
ap=[pad(i+1,-7.62+2.54*i,0,name=n,typ='power_in' if i==0 else 'input' if i in (2,4,5,6) else 'passive') for i,n in enumerate(anames)]
comp('U2','MAX98357A breakout',(43,22),(166,52),ap,{1:'+5V_AMP',2:'GND',3:'AMP_SD',4:'AMP_GAIN',5:'DIN',6:'BCLK',7:'LRCLK'},(-9.7,-2.54,9.7,15.3),'Adafruit 3006','BTL screw terminals directly wired to LS1; 7-pin female socket')

def r(ref,val,x,y,sx,sy,n1,n2,mpn):
    return comp(ref,val,(x,y),(sx,sy),[pad(1,-1,0,1.2,1.4,0),pad(2,1,0,1.2,1.4,0)],{1:n1,2:n2},(-1.8,-1,1.8,1),mpn,'0805 resistor 1%')
r('R1','10k',10,26,38,100,'+3V3','PTT','Yageo RC0805FR-0710KL')
r('R2','1k',19,37,80,100,'LED_GPIO','LED_A','Yageo RC0805FR-071KL')
r('R3','100k',28,17,122,100,'+3V3','MUTE','Yageo RC0805FR-07100KL')
r('R4','100k',42,15,164,100,'+5V_AMP','AMP_GAIN','Yageo RC0805FR-07100KL')
r('R5','33R',27,10,38,132,'BCLK_SRC','BCLK','Yageo RC0805FR-0733RL')
r('R6','33R',27,13,80,132,'LRCLK_SRC','LRCLK','Yageo RC0805FR-0733RL')
r('R7','33R',27,21,122,132,'DIN_SRC','DIN','Yageo RC0805FR-0733RL')
comp('Q1','BSS138',(34,16),(212,100),[pad(1,-.95,1,1.0,1.2,0,'G','input'),pad(2,.95,1,1.0,1.2,0,'S'),pad(3,0,-1,1.0,1.2,0,'D')],{1:'MUTE',2:'GND',3:'AMP_SD'},(-1.6,-1.7,1.6,1.7),'onsemi BSS138LT1G','SOT-23 open drain; HIGH GPIO4 mutes amplifier')
comp('F1','PTC 0.50A',(29,5),(218,52),[pad(1,-2.1,0,1.5,3.2,0),pad(2,2.1,0,1.5,3.2,0)],{1:'+5V_USB',2:'+5V_AMP'},(-3.2,-2,3.2,2),'Bourns MF-MSMF050-2','Resettable fuse only in amplifier branch, 1812 style 1 manufacturer land pattern')
for ref,x,y,sx,sy,n,val,mpn in [('C1',36,9,164,132,'+5V_AMP','100n','Murata GRM21BR71C104KA01L'),('C2',10,30,212,132,'PTT','100n','Murata GRM21BR71C104KA01L')]:
    comp(ref,val,(x,y),(sx,sy),[pad(1,-1,0,1.2,1.4,0),pad(2,1,0,1.2,1.4,0)],{1:n,2:'GND'},(-1.8,-1,1.8,1),mpn,'0805 X7R 16V; C2 debounce, C1 local bypass')
for ref,x,y,sx,sy,names,nets,mpn in [('J1',9,40,38,167,['PTT','GND'],{1:'PTT',2:'GND'},'JST B2B-XH-A(LF)(SN)'),('J2',20,44,92,167,['LED_A','LED_K'],{1:'LED_A',2:'GND'},'JST B2B-XH-A(LF)(SN)')]:
    comp(ref,'Panel '+('PTT' if ref=='J1' else 'LED'),(x,y),(sx,sy),[pad(1,0,0,1.8,1.8,1,name=names[0]),pad(2,2.5,0,1.8,1.8,1,name=names[1])],nets,(-2.5,-3,5,3),mpn,'2-pin JST-XH 2.50mm vertical, keyed harness')
for i,(x,y,n) in enumerate([(36,4,'+5V_AMP'),(10,22,'+3V3'),(36,40,'GND'),(56,22,'AMP_SD')],1):
    comp('TP'+str(i),n,(x,y),(135+(i-1)*36,155),[pad(1,0,0,1.5,1.5,0,name='TEST')],{1:n},(-1,-1,1,1),'PCB test pad','1.5 mm exposed test point')
for i,xy in enumerate([(3,3),(61,3),(3,51),(61,51)],1):
    comp('H'+str(i),'M3',xy,(0,0),[pad('',0,0,3.2,3.2,3.2)],{},(-2.75,-2.75,2.75,2.75),'M3 clearance','Non-plated mounting hole; M3 screw head max diameter 5.5mm')

# Schematic symbols are embedded and also stored as a project library.
schid=uid('schematic')
symbols=[]; instances=[]; wires=[]; labels=[]; ncs=[]
for c in components:
    if c['ref'].startswith('H'): continue
    ref=c['ref']; pins=c['pads']; n=len(pins); sx,sy=[round(round(v/1.27)*1.27,4) for v in c['sch']]
    wide=ref in ('U1','U2'); hw=16.51 if wide else 7.62
    rows=7 if wide else n; hh=(rows+1)*1.27
    # all pins distributed on left, except U1 pins 8..14 on right
    pin_defs=[]; locs=[]
    for idx,a in enumerate(pins):
        rightside=ref=='U1' and idx>=7
        ri=idx-7 if rightside else idx
        px=hw+5.08 if rightside else -hw-5.08
        py=(rows-1)*1.27-ri*2.54
        angle=180 if rightside else 0
        pin_defs.append(f'(pin {a["typ"]} line (at {px} {py} {angle}) (length 5.08) (name {q(a["name"])} (effects (font (size 1 1)))) (number {q(a["n"])} (effects (font (size 1 1)))))')
        locs.append((a,sx+px,sy-py,rightside))
    symbols.append(f'''(symbol "Mesa:{ref}" (pin_names (offset 0.7)) (in_bom yes) (on_board yes)
      (property "Reference" {q(ref)} (at 0 {hh+4} 0) (effects (font (size 1.27 1.27))))
      (property "Value" {q(c['value'])} (at 0 {hh+1.5} 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" {q(c['fp'])} (at 0 0 0) (effects (font (size 1 1)) hide))
      (symbol "{ref}_0_1" (rectangle (start {-hw} {hh}) (end {hw} {-hh}) (stroke (width 0.254) (type default)) (fill (type background))))
      (symbol "{ref}_1_1" {''.join(pin_defs)}))''')
    instances.append(f'''(symbol (lib_id "Mesa:{ref}") (at {sx} {sy} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {c['uuid']})
      (property "Reference" {q(ref)} (at {sx} {sy-hh-4} 0) (effects (font (size 1.27 1.27))))
      (property "Value" {q(c['value'])} (at {sx} {sy-hh-1.5} 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" {q(c['fp'])} (at {sx} {sy} 0) (effects (font (size 1 1)) hide))
      (property "MPN" {q(c['mpn'])} (at {sx} {sy} 0) (effects (font (size 1 1)) hide))
      {''.join(f'(pin {q(a["n"])} (uuid {uid(ref+"pin"+a["n"])}))' for a in pins)}
      (instances (project "mesa-voice" (path "/{schid}" (reference "{ref}") (unit 1)))))''')
    for a,x,y,rs in locs:
        net=c['nets'].get(a['n']); end=x+5.08 if rs else x-5.08
        if net:
            wires.append(f'(wire (pts (xy {x} {y}) (xy {end} {y})) (stroke (width 0) (type default)) (uuid {uid(ref+"wire"+a["n"])}))')
            labels.append(f'(label {q(net)} (at {end} {y} 0) (effects (font (size 1 1)) (justify {"left" if rs else "right"} bottom)) (uuid {uid(ref+"label"+a["n"])}))')
        else: ncs.append(f'(no_connect (at {x} {y}) (uuid {uid(ref+"nc"+a["n"])}))')
symbols.append('''(symbol "Mesa:PWR_FLAG" (power) (pin_names (offset 0) hide) (in_bom no) (on_board yes)
 (property "Reference" "#FLG" (at 0 0 0) (effects (font (size 1 1)) hide))
 (property "Value" "PWR_FLAG" (at 0 3.81 0) (effects (font (size 1 1))))
 (symbol "PWR_FLAG_0_1" (polyline (pts (xy 0 0) (xy 0 1.27) (xy -1.27 1.905) (xy 0 2.54) (xy 1.27 1.905) (xy 0 1.27)) (stroke (width 0) (type default)) (fill (type none))))
 (symbol "PWR_FLAG_1_1" (pin power_out line (at 0 0 90) (length 0) (name "pwr" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))''')
instances.append(f'''(symbol (lib_id "Mesa:PWR_FLAG") (at 246.38 52.07 0) (unit 1) (in_bom no) (on_board yes) (dnp no) (uuid {uid('flag')})
 (property "Reference" "#FLG01" (at 246.38 52.07 0) (effects (font (size 1 1)) hide))
 (property "Value" "PWR_FLAG" (at 246.38 48.26 0) (effects (font (size 1 1))))
 (instances (project "mesa-voice" (path "/{schid}" (reference "#FLG01") (unit 1)))))''')
labels.append(f'(label "+5V_AMP" (at 246.38 52.07 0) (effects (font (size 1 1)) (justify left bottom)) (uuid {uid("flag-label")}))')
notes=[(18,18,'MESA VOICE R1 | USB-C / Wi-Fi / local AI | carrier schematic'),(18,22,'U1: Seeed 113991115 Sense. Mic PDM GPIO41 DATA / GPIO42 CLK inside expansion.'),(18,26,'USB-C power enters U1 only. No battery. Camera removed; microSD unused.'),(126,74,'U2 onboard screw terminal + -> LS1 +; terminal - -> LS1 -.'),(126,78,'LS1: Visaton K40 8 ohm / 1 W. Both BTL wires float: never connect to GND.'),(18,188,'J1 harness -> normally-open panel switch. J2 pin1 -> LED anode, pin2 -> cathode.'),(18,192,'GPIO4 HIGH turns Q1 ON and silences U2. R3 defaults to mute during boot.'),(18,196,'R4 sets 3 dB gain. R5-R7 series damping. F1 protects amplifier branch only.')]
texts=''.join(f'(text {q(t)} (at {x} {y} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid {uid(t)}))' for x,y,t in notes)
(HW/'mesa-voice.kicad_sch').write_text(f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid {schid}) (paper "A4")
 (title_block (title "Mesa Voice R1 - modular carrier") (date "2026-11-09") (rev "1.0"))
 (lib_symbols {''.join(symbols)}) {''.join(wires+labels+ncs+instances)} {texts}
 (sheet_instances (path "/" (page "1"))))''',encoding='utf-8')
(HW/'Mesa.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor") '+''.join(s.replace('(symbol "Mesa:','(symbol "',1) for s in symbols)+')',encoding='utf-8')
(HW/'sym-lib-table').write_text('(sym_lib_table (lib (name "Mesa")(type "KiCad")(uri "${KIPRJMOD}/Mesa.kicad_sym")(options "")(descr "Mesa R1")))')
(HW/'fp-lib-table').write_text('(fp_lib_table (lib (name "Mesa")(type "KiCad")(uri "${KIPRJMOD}/Mesa.pretty")(options "")(descr "Mesa R1")))')

b=p.BOARD(); b.SetCopperLayerCount(2)
netnames=sorted({n for c in components for n in c['nets'].values()})
nets={}
for n in netnames:
    ni=p.NETINFO_ITEM(b,'/'+n); b.Add(ni); nets[n]=ni
netpads={n:[] for n in netnames}; obstaclepads=[]
def rect(fp,x1,y1,x2,y2,layer,width=.15):
    for a,bb in [((x1,y1),(x2,y1)),((x2,y1),(x2,y2)),((x2,y2),(x1,y2)),((x1,y2),(x1,y1))]:
        ln=p.PCB_SHAPE(fp); ln.SetShape(p.SHAPE_T_SEGMENT); ln.SetStart(pt(*a)); ln.SetEnd(pt(*bb)); ln.SetWidth(mm(width)); ln.SetLayer(layer); fp.Add(ln)
for c in components:
    fp=p.FOOTPRINT(b); fp.SetReference(c['ref']); fp.SetValue(c['value']); fp.SetFPID(p.LIB_ID('Mesa',c['ref']))
    fp.SetPath(p.KIID_PATH('/'+schid+'/'+c['uuid']))
    fp.SetAttributes(p.FP_THROUGH_HOLE if any(a['d'] for a in c['pads']) else p.FP_SMD)
    if c['ref'].startswith('H'): fp.SetAttributes(p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES|p.FP_BOARD_ONLY)
    pcbpads=c['pads'][:]
    if c['ref']=='U2':
        # Manufacturer mounting holes, referenced to the seven-pin header.
        pcbpads += [pad('',dx,13.97,2.7,2.7,2.7) for dx in (-6.35,6.35)]
    for a in pcbpads:
        pa=p.PAD(fp); pa.SetNumber(a['n']); pa.SetPosition(pt(a['x'],a['y'])); pa.SetSize(pt(a['sx'],a['sy']))
        if a['d']:
            pa.SetAttribute(p.PAD_ATTRIB_NPTH if not a['n'] else p.PAD_ATTRIB_PTH); pa.SetShape(p.PAD_SHAPE_CIRCLE if a['n']!='1' else p.PAD_SHAPE_RECT)
            pa.SetDrillSize(pt(a['d'],a['d'])); pa.SetLayerSet(p.PAD.PTHMask())
        else:
            pa.SetAttribute(p.PAD_ATTRIB_SMD); pa.SetShape(p.PAD_SHAPE_ROUNDRECT); pa.SetRoundRectRadiusRatio(.15); pa.SetLayerSet(layers(*([p.F_Cu, p.F_Mask] + ([] if c['ref'].startswith('TP') else [p.F_Paste]))))
        n=c['nets'].get(a['n'])
        if n: pa.SetNet(nets[n])
        elif a['n']:
            nc=p.NETINFO_ITEM(b,f'unconnected-({c["ref"]}-{a["name"]}-Pad{a["n"]})'); b.Add(nc); pa.SetNet(nc)
        fp.Add(pa)
    x1,y1,x2,y2=c['body']; rect(fp,x1,y1,x2,y2,p.F_Fab)
    margin=.05 if c['ref'].startswith('H') else .25
    rect(fp,x1-margin,y1-margin,x2+margin,y2+margin,p.F_CrtYd,.05)
    # Module and hole courtyards are visible in Fab; silk kept off pads.
    fp.Reference().SetPosition(pt((x1+x2)/2,y2+1.5)); fp.Reference().SetTextSize(pt(.9,.9)); fp.Reference().SetTextThickness(mm(.13)); fp.Reference().SetLayer(p.F_Fab)
    if c['ref'] in ('R1','R5','R6','R7'): fp.Reference().SetPosition(pt(3.6,0))
    if c['ref']=='R3': fp.Reference().SetPosition(pt(0,-1.6))
    if c['ref']=='Q1': fp.Reference().SetPosition(pt(4,0))
    if c['ref']=='F1': fp.Reference().SetPosition(pt(0,-3.2))
    fp.Value().SetVisible(False)
    p.PCB_IO_KICAD_SEXPR().FootprintSave(str(LIB),fp)
    fp.SetPosition(pt(*c['xy'])); b.Add(fp)
    for pa in fp.Pads():
        # NPTH holes share an empty number; recover their own size/position.
        a=next(a for a in pcbpads if a['n']==pa.GetNumber())
        x,y=p.ToMM(pa.GetPosition().x),p.ToMM(pa.GetPosition().y); n=c['nets'].get(a['n'])
        obstaclepads.append((x,y,a['sx'],a['sy'],a['d'],n))
        if n: netpads[n].append((x,y,0, bool(a['d'])))
for a,bb in [((0,0),(64,0)),((64,0),(64,54)),((64,54),(0,54)),((0,54),(0,0))]:
    ln=p.PCB_SHAPE(b); ln.SetShape(p.SHAPE_T_SEGMENT); ln.SetStart(pt(*a)); ln.SetEnd(pt(*bb)); ln.SetWidth(mm(.05)); ln.SetLayer(p.Edge_Cuts); b.Add(ln)
for s,x,y,size in [('MESA VOICE R1',43,45,1.3),('USB-C / SENSE',17,24,.8),('PTT',10,46,.9),('LED + -',21,49,.9),('8 OHM BTL: NO GND',43,49,.8)]:
    t=p.PCB_TEXT(b); t.SetText(s); t.SetPosition(pt(x,y)); t.SetTextSize(pt(size,size)); t.SetTextThickness(mm(.13)); t.SetLayer(p.F_SilkS); b.Add(t)

# Deterministic two-layer grid routing. Conservative inflated rectangles for
# pads, 0.25-mm signal / 0.6-mm supply traces; vias 0.7/0.3 mm. KiCad DRC is
# the release authority, not the grid router.
step=.2; nx=321; ny=271; copper=[]; vias=[]; route_report=[]
X,Y=np.meshgrid(np.arange(nx)*step,np.arange(ny)*step,indexing='ij')
def blocked(net,width,via=False):
    out=np.zeros((2,nx,ny),bool); rr=(.35 if via else width/2)+.2+.045
    edge=.3+(.35 if via else width/2)
    base=(X<edge)|(X>64-edge)|(Y<edge)|(Y>54-edge); out[:]=base
    for x,y,sx,sy,d,n in obstaclepads:
        if n==net: continue
        mask=(abs(X-x)<=sx/2+rr)&(abs(Y-y)<=sy/2+rr)
        out[0]|=mask
        if d: out[1]|=mask
    for x1,y1,x2,y2,lay,w,n in copper:
        if n==net: continue
        dx=x2-x1;dy=y2-y1; length=dx*dx+dy*dy
        t=np.clip(((X-x1)*dx+(Y-y1)*dy)/max(length,1e-12),0,1)
        mask=(X-x1-t*dx)**2+(Y-y1-t*dy)**2 <= (rr+w/2)**2
        out[lay]|=mask
    for x,y,n in vias:
        if n==net:
            if via:
                d2=(X-x)**2+(Y-y)**2
                out[:]|=(d2>.001)&(d2<.56**2)
            continue
        out[:]|=((X-x)**2+(Y-y)**2 <= (rr+.35)**2)
    return out
def route(a,z,net,width):
    obs=blocked(net,width); vobs=blocked(net,width,True)
    start=(round(a[0]/step),round(a[1]/step),0); goal=(round(z[0]/step),round(z[1]/step),0)
    goals={goal,(goal[0],goal[1],1)} if z[3] else {goal}
    starts=[start,(start[0],start[1],1)] if a[3] else [start]
    def h(t): return abs(t[0]-goal[0])+abs(t[1]-goal[1])
    dist={s:0 for s in starts}; prev={}; heap=[(h(s),0,s) for s in starts]; heapq.heapify(heap)
    found=None
    while heap:
        _,g,s=heapq.heappop(heap)
        if g!=dist.get(s): continue
        if s in goals: found=s;break
        x,y,l=s
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            xx=x+dx;yy=y+dy
            if xx<0 or xx>=nx or yy<0 or yy>=ny or obs[l,xx,yy]:continue
            ns=(xx,yy,l); ng=g+1
            if ng<dist.get(ns,1e20): dist[ns]=ng;prev[ns]=s;heapq.heappush(heap,(ng+h(ns),ng,ns))
        if not vobs[:,x,y].any():
            ns=(x,y,1-l);ng=g+18
            if ng<dist.get(ns,1e20):dist[ns]=ng;prev[ns]=s;heapq.heappush(heap,(ng+h(ns),ng,ns))
    if found is None:raise RuntimeError(f'No route {net} {a}->{z}')
    path=[found]
    while path[-1] in prev:path.append(prev[path[-1]])
    path.reverse()
    pts=[(a[0],a[1],path[0][2])]+[(x*step,y*step,l) for x,y,l in path]+[(z[0],z[1],path[-1][2])]
    compact=[]
    for v in pts:
        if compact and v==compact[-1]:continue
        if len(compact)>=2:
            a0,a1=compact[-2:]
            if a0[2]==a1[2]==v[2] and abs((a1[0]-a0[0])*(v[1]-a1[1])-(a1[1]-a0[1])*(v[0]-a1[0]))<1e-8:compact.pop()
        compact.append(v)
    for a0,a1 in zip(compact,compact[1:]):
        if a0[2]!=a1[2]:
            if (a0[0],a0[1],net) not in vias:
                v=p.PCB_VIA(b);v.SetPosition(pt(a0[0],a0[1]));v.SetWidth(mm(.7));v.SetDrill(mm(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(nets[net]);b.Add(v);vias.append((a0[0],a0[1],net))
        else:
            tr=p.PCB_TRACK(b);tr.SetStart(pt(a0[0],a0[1]));tr.SetEnd(pt(a1[0],a1[1]));tr.SetWidth(mm(width));tr.SetLayer(p.F_Cu if a0[2]==0 else p.B_Cu);tr.SetNet(nets[net]);b.Add(tr);copper.append((*a0[:2],*a1[:2],a0[2],width,net))
    route_report.append(dict(net=net,start=a[:2],end=z[:2],segments=len(compact)-1))

# Route critical clocks first, ground last. Nearest spanning tree for fanout.
order=['GND','BCLK_SRC','LRCLK_SRC','DIN_SRC','BCLK','LRCLK','DIN','+5V_USB','+5V_AMP','AMP_GAIN','AMP_SD','MUTE','+3V3','LED_GPIO','LED_A','PTT']
for net in order:
    points=netpads[net][:]; done=[points.pop(0)]
    while points:
        _,i,j=min((math.dist(a[:2],z[:2]),i,j) for i,a in enumerate(done) for j,z in enumerate(points))
        z=points.pop(j); route(done[i],z,net,.6 if net.startswith('+5V') else .4 if net in ('+3V3','GND') else .25);done.append(z)
    print('Routed',net,flush=True)
# A bottom GND plane supplies a continuous return where other tracks allow it.
zone=p.ZONE(b);zone.SetLayer(p.B_Cu);zone.SetNet(nets['GND']);zone.SetLocalClearance(mm(.25));zone.SetThermalReliefGap(mm(.25));zone.SetThermalReliefSpokeWidth(mm(.3));zone.SetPadConnection(p.ZONE_CONNECTION_FULL)
poly=zone.Outline();poly.NewOutline()
for x,y in [(0.6,.6),(63.4,.6),(63.4,53.4),(.6,53.4)]:poly.Append(mm(x),mm(y))
b.Add(zone)
b.GetDesignSettings().SetCopperLayerCount(2)
print('Saving routed board before fill',flush=True)
p.PCB_IO_KICAD_SEXPR().SaveBoard(str(HW/'mesa-voice.kicad_pcb'),b)
print('Ground plane filled after project settings are saved',flush=True)
project={'meta':{'filename':'mesa-voice.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':.2,'min_track_width':.25,'min_via_diameter':.7,'min_through_hole_diameter':.3,'min_via_annular_width':.15,'min_copper_edge_clearance':.3,'min_hole_clearance':.25},'rule_severities':{}}},'net_settings':{'classes':[{'name':'Default','clearance':.2,'track_width':.25,'via_diameter':.7,'via_drill':.3,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.25,'diff_pair_gap':.2,'diff_pair_via_gap':.25,'pcb_color':'rgba(0, 0, 0, 0.000)','schematic_color':'rgba(0, 0, 0, 0.000)','wire_width':6,'bus_width':12,'line_style':0}],'meta':{'version':3}}}
(HW/'mesa-voice.kicad_pro').write_text(json.dumps(project,indent=2))
b=p.LoadBoard(str(HW/'mesa-voice.kicad_pcb'))
p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(str(HW/'mesa-voice.kicad_pcb'),b)
(HW/'design.json').write_text(json.dumps({'board_mm':[64,54,1.6],'components':components,'nets':netnames,'routes':route_report},indent=2))
(ROOT/'validation'/'routing.json').write_text(json.dumps({'router':'deterministic two-layer A*','routed_connections':len(route_report),'track_segments':len(copper),'vias':len(vias),'route_order':order,'note':'Must pass KiCad DRC and independent netlist parity before fabrication.'},indent=2))
with (HW/'bom-carrier.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['Reference','Value','Quantity','MPN','Footprint','Description'])
    for c in components:w.writerow([c['ref'],c['value'],1,c['mpn'],c['fp'],c['desc']])
print('Generated',HW)
