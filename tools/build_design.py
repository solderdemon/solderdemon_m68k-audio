from pathlib import Path
import re, uuid, json, csv, shutil, math
import pcbnew as pcb
ROOT=Path(__file__).resolve().parents[1]
LIB=Path('C:/Program Files/KiCad/10.0/share/kicad')
NAME='solderdemon_m68k-audio'
W,H=100,69  # card outline in mm; J1 sits on the bottom (bus) edge
RT,RB=4,4  # corner radii: top corners, bus-edge corners (all four the same)
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL,'rosco-m68k-audio-r1/'+s))
def q(s): return json.dumps(str(s),ensure_ascii=False)
def parse(s):
    toks=re.findall(r'"(?:\\.|[^"\\])*"|\(|\)|[^\s()]+',s); stack=[]; root=[]; cur=root
    for t in toks:
        if t=='(': n=[];cur.append(n);stack.append(cur);cur=n
        elif t==')':cur=stack.pop()
        else:cur.append(json.loads(t) if t.startswith('"') else t)
    return root[0]
def sub(a,k):return [x for x in a if isinstance(x,list) and x and x[0]==k]
def one(a,k):return next(x for x in a if isinstance(x,list) and x and x[0]==k)
def dump(a):
    if isinstance(a,list):
        tag=a[0]; result=[tag]
        for i,x in enumerate(a[1:],1):
            if isinstance(x,list): result.append(dump(x))
            elif (tag in ['symbol','name','number'] and i==1) or (tag=='property' and i<=2): result.append(q(x))
            else: result.append(str(x))
        return '('+' '.join(result)+')'
    return str(a)
def symbol(lib,name):
    a=parse((LIB/'symbols'/f'{lib}.kicad_sym').read_text(encoding='utf-8'))
    s=next(x for x in sub(a,'symbol') if x[1]==name)
    assert not sub(s,'extends'),name
    return s
symbols={};parts=[]
def standard(lib,name):
    key=f'{lib}:{name}'
    if key not in symbols:
        s=symbol(lib,name);s[1]=key;symbols[key]=s
    return key

def custom(name,left,right,fp):
    # Pin tuples: (number, label, electrical type)
    key='SolderDemonAudio:'+name; h=(max(len(left),len(right))+1)*2.54/2
    s=['symbol',key,['pin_names',['offset','0.8']],['in_bom','yes'],['on_board','yes'],['property','Reference','U',['at','0',str(h+3),'0'],['effects',['font',['size','1.27','1.27']]]],['property','Value',name,['at','0',str(h+6),'0'],['effects',['font',['size','1.27','1.27']]]],['property','Footprint',fp,['at','0','0','0'],['effects',['font',['size','1.27','1.27']],['hide','yes']]]]
    s.append(['symbol',name+'_0_1',['rectangle',['start','-12.7',str(h)],['end','12.7',str(-h)],['stroke',['width','0.254'],['type','default']],['fill',['type','background']]]])
    pins=['symbol',name+'_1_1']
    for side,arr in [(-1,left),(1,right)]:
        for i,(num,label,typ) in enumerate(arr):
            pins.append(['pin',typ,'line',['at',str(side*15.24),str(h-2.54*(i+1)),str(0 if side==-1 else 180)],['length','2.54'],['name',label,['effects',['font',['size','1','1']]]],['number',str(num),['effects',['font',['size','1','1']]]]])
    s.append(pins);symbols[key]=s;return key

def add(ref,key,value,nets,xy,pos,rot=0):
    s=symbols[key];fp=next(x[2] for x in sub(s,'property') if x[1]=='Footprint')
    parts.append(dict(ref=ref,key=key,value=value,nets={str(k):v for k,v in nets.items()},xy=xy,pos=pos,rot=rot,fp=fp,uuid=uid(ref)))

# Netlist exported from the local m68k backplane, not inferred from connector names.
import xml.etree.ElementTree as ET
r=ET.parse(ROOT/'bus-reference.xml')
bus_all={int(n.attrib['pin']):x.attrib['name'] for x in r.findall('./nets/net') for n in x.findall('node') if n.attrib['ref']=='BUS5-1'}
used=['A1']+['A'+str(i) for i in range(8,20)]+['D'+str(i) for i in range(8)]+['AS','LDS','RW','RESET','DTACK','IOSEL','VCC','GND']
bus={i: ('+5V' if n=='VCC' else n) if n in used else None for i,n in bus_all.items()}
key=custom('M68K_BUS_2x32',[(i,bus_all[i],'passive') for i in range(1,65,2)],[(i,bus_all[i],'passive') for i in range(2,65,2)],'Connector_PinSocket_2.54mm:PinSocket_2x32_P2.54mm_Horizontal')
add('J1',key,'M68K BUS / 2x32',bus,(45.72,76.2),(10.63,H-10.46),90)
# HCT comparator, exact TI CD74HCT688 pin mapping. P byte A8..A15 equals 01h.
pp=[2,4,6,8,11,13,15,17];qq=[3,5,7,9,12,14,16,18]
key=custom('CD74HCT688',[(pp[i],'P'+str(i),'input') for i in range(8)]+[(1,'~{G}','input'),(10,'GND','power_in')],[(qq[i],'Q'+str(i),'input') for i in range(8)]+[(19,'~{P=Q}','output'),(20,'VCC','power_in')],'Package_DIP:DIP-20_W7.62mm_Socket_LongPads')
n={pp[i]:'A'+str(8+i) for i in range(8)}; n.update({qq[i]:'+5V' if i==0 else 'GND' for i in range(8)});n.update({1:'GND',10:'GND',20:'+5V',19:'MATCH'})
add('U4',key,'CD74HCT688E',n,(139.7,66.04),(27.3,43.24),90)
# ATF22V10C, seven registered delay stages. Q2 clocks U2; Q3..Q5 form strobe.
ins=[(1,'CLK','input'),(2,'~{IOSEL}','input'),(3,'~{MATCH}','input'),(4,'~{AS}','input'),(5,'~{LDS}','input'),(6,'RW','input'),(7,'~{RESET}','input'),(8,'A1','input'),(9,'A16','input'),(10,'A17','input'),(11,'A18','input'),(13,'A19','input')]
outs=[(23,'S0','output'),(22,'S1','output'),(21,'CAPTURE','output'),(20,'S3','output'),(19,'S4','output'),(18,'S5','output'),(17,'DONE','output'),(16,'BDIR','output'),(15,'NREQ','output'),(14,'~{DTACK}','open_collector'),(24,'VCC','power_in'),(12,'GND','power_in')]
key=custom('AUDIO_SEQUENCER',ins,outs,'Package_DIP:DIP-24_W7.62mm_Socket_LongPads')
n={1:'LOGICCLK',2:'IOSEL',3:'MATCH',4:'AS',5:'LDS',6:'RW',7:'RESET',8:'A1',9:'A16',10:'A17',11:'A18',13:'A19',12:'GND',24:'+5V',23:None,22:None,21:'CAPTURE',20:None,19:None,18:None,17:None,16:'BDIR',15:None,14:'DTACK'}
add('U3',key,'ATF22V10C-15PU',n,(238.76,66.04),(27.3,29.62),90)
# Data latch captures well before strobe, never on the trailing CPU bus edge.
dp=[3,4,7,8,13,14,17,18];qp=[2,5,6,9,12,15,16,19]
key=custom('CD74HCT273',[(dp[i],'D'+str(i),'input') for i in range(8)]+[(11,'CP','input'),(1,'~{MR}','input'),(10,'GND','power_in')],[(qp[i],'Q'+str(i),'output') for i in range(8)]+[(20,'VCC','power_in')],'Package_DIP:DIP-20_W7.62mm_Socket_LongPads')
n={dp[i]:'D'+str(i) for i in range(8)};n.update({qp[i]:'PSGD'+str(i) for i in range(8)});n.update({1:'RESET',11:'CAPTURE',10:'GND',20:'+5V'})
add('U2',key,'CD74HCT273E',n,(340.36,66.04),(63.9,29.62),90)
key=standard('Audio','YM2149'); n={1:'GND',3:'CH_A',4:'CH_B',22:'PSGCLK',23:'RESET',24:'GND',25:'+5V',26:'+5V',27:'BDIR',28:'A1',29:'GND',40:'+5V',38:'CH_C'}
n.update({37-i:'PSGD'+str(i) for i in range(8)});n.update({i:None for i in list(range(6,22))+[2,5,39]})
add('U1',key,'YM2149F',n,(60.96,198.12),(38.5,17.8),90)
key=custom('OSC_5V_DIP8',[(1,'EN / NC','input'),(4,'GND','power_in')],[(8,'VCC','power_in'),(5,'OUT','output')],'Oscillator:Oscillator_DIP-8')
add('X1',key,'1.8432 MHz / 5V / 50ppm',{1:'+5V',4:'GND',5:'CLK_RAW',8:'+5V'},(152.4,157.48),(61.5,43.24))
R=standard('Device','R'); C=standard('Device','C'); CP=standard('Device','C_Polarized'); J=standard('Connector_Generic','Conn_01x03')
for k,fp in [(R,'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal'),(C,'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P2.50mm'),(CP,'Capacitor_THT:CP_Radial_D6.3mm_P2.50mm'),(J,'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical')]: next(p for p in sub(symbols[k],'property') if p[1]=='Footprint')[2]=fp
add('R1',R,'33',{1:'CLK_RAW',2:'PSGCLK'},(190.5,152.4),(76,35.62),270)
add('R2',R,'33',{1:'CLK_RAW',2:'LOGICCLK'},(190.5,172.72),(80.5,35.62),270)
add('R3',R,'10k',{1:'BDIR',2:'GND'},(139.7,198.12),(85,35.62),270)
add('R4',R,'10k',{1:'CAPTURE',2:'GND'},(165.1,198.12),(89.5,35.62),270)
# VCC bypass standing upright left of each chip (U1, U2, U3, U4, X1), plus entry reservoir.
for i,pos in enumerate([(34.2,8.93),(59.6,24.56),(23,24.56),(23,38.18),(55.5,38.18)],1):
    add('C'+str(i),C,'100nF',{1:'+5V',2:'GND'},(25.4+i*25.4,254),pos,270)
add('C6',CP,'47uF / 16V',{1:'+5V',2:'GND'},(200.66,254),(92,25.81))
# ABC stereo: each PSG channel loaded with 1k, B mixed at reduced level. The network sits in two
# rows under U4, next to the output capacitors; the logo and name sit beside the jack.
for i,ch in enumerate(['CH_A','CH_B','CH_C']):add('R'+str(5+i),R,'1k',{1:ch,2:'GND'},(228.6+i*35.56,157.48),(22+i*11.5,53.54))
for ref,val,a,b,xy,pos in [('R8','10k','CH_A','MIX_L',(228.6,187.96),(22,49.04)),('R9','22k','CH_B','MIX_L',(264.16,187.96),(33.5,49.04)),('R10','22k','CH_B','MIX_R',(299.72,187.96),(45,49.04)),('R11','10k','CH_C','MIX_R',(335.28,187.96),(56.5,49.04))]:add(ref,R,val,{1:a,2:b},xy,pos)
for ref,a,b,xy,pos in [('C7','MIX_L','OUT_L',(238.76,220.98),(5,31)),('C8','MIX_R','OUT_R',(309.88,220.98),(5,42))]:add(ref,CP,'10uF / 16V',{1:a,2:b},xy,pos)
for ref,a,xy,pos in [('R12','OUT_L',(264.16,220.98),(13.5,27.19)),('R13','OUT_R',(335.28,220.98),(13.5,38.19))]:add(ref,R,'100k',{1:a,2:'GND'},xy,pos)
# 5-pin square SJ1-3525N (PJ-307 style) on the left edge, nose through its own Edge.Cuts cutout; TN/RN switches unused.
key=standard('Connector_Audio','AudioJack3_SwitchTR');next(p for p in sub(symbols[key],'property') if p[1]=='Footprint')[2]='Connector_Audio:Jack_3.5mm_CUI_SJ1-3525N_Horizontal'
add('J2',key,'SJ1-3525N / LINE OUT',{'T':'OUT_L','R':'OUT_R','S':'GND','TN':None,'RN':None},(378.46,198.12),(4.5,17),270)
add('J3',J,'L / GND / R',{1:'OUT_L',2:'GND',3:'OUT_R'},(378.46,233.68),(18.5,33.96),0)
for p in parts:
    if p['ref'] in ['R12','R13']:p['rot']=270
flag=standard('power','PWR_FLAG');add('#FLG01',flag,'PWR_FLAG',{1:'+5V'},(25.4,254),(0,0));add('#FLG02',flag,'PWR_FLAG',{1:'GND'},(25.4,271.78),(0,0))

# Restore stock symbol cache to match installed libraries, keep per-instance footprints.
for k in list(symbols):
    if not k.startswith('SolderDemonAudio:'):
        lib,name=k.split(':');stock=symbol(lib,name);stock[1]=k;symbols[k]=stock

elements=[]
for p in parts:
    x,y=p['xy'];s=symbols[p['key']];u=p['uuid']
    elems=[f'(symbol (lib_id {q(p["key"])}) (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {u})']
    for name,val,dy,hidden in [('Reference',p['ref'],-7.62,False),('Value',p['value'],-5.08,False),('Footprint',p['fp'],0,True)]:
        if name in ['Reference','Value'] and p['ref'][0] in 'UJX' and p['ref'] not in ['J2','J3']:
            pinys=[float(one(pin,'at')[2]) for ss in sub(s,'symbol') for pin in sub(ss,'pin')];dy=-max(pinys)-(7.62 if name=='Reference' else 5.08)
        tx=x
        if p['ref']=='U1' and name in ['Reference','Value']:tx=x+12.7
        if p['ref'][0] in 'RC' and name in ['Reference','Value']:tx=x+5.08;dy=-1.27 if name=='Reference' else 1.27
        elems.append(f'(property {q(name)} {q(val)} (at {tx} {y+dy} 0) (effects (font (size 1.27 1.27))'+(' (hide yes)' if hidden else '')+'))')
    elems.append(f'(instances (project {q(NAME)} (path "/{uid("root")}" (reference {q(p["ref"])}) (unit 1)))) )'); elements.append(''.join(elems))
    for ss in sub(s,'symbol'):
        for pin in sub(ss,'pin'):
            num=one(pin,'number')[1];at=one(pin,'at');px=round(x+float(at[1]),4);py=round(y-float(at[2]),4);ang=int(at[3]);net=p['nets'].get(num)
            if net is None:elements.append(f'(no_connect (at {px} {py}) (uuid {uid(p["ref"]+"nc"+num)}))');continue
            dx,dy={0:(-5.08,0),180:(5.08,0),90:(0,5.08),270:(0,-5.08)}[ang];ex=round(px+dx,4);ey=round(py+dy,4)
            elements.append(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid {uid(p["ref"]+"w"+num)}))')
            just='right bottom' if ang==0 else 'left bottom'
            elements.append(f'(label {q(net)} (at {ex} {ey} 0) (effects (font (size 1 1)) (justify {just})) (uuid {uid(p["ref"]+"l"+num)}))')
for text,x,y in [('M68K SYSTEM BUS',20,19),('A8..A15 = 01h',115,19),('HARDWARE WRITE SEQUENCER',208,19),('LATCHED PSG DATA',315,19),('YM2149F / BC1 FIXED LOW',23,140),('INDEPENDENT CLOCK',122,140),('ABC STEREO / LINE LEVEL',227,140),('SUPPLY / 5V +/-5%',20,239),('F00101: register address; F00103: data. Byte writes only. A2..A7 mirrored.',110,108),('U3 requires audio_sequencer.jed. Shared DTACK is LOW or high impedance.',110,115),('U1: 100 = address, 110 = write, 000/010 = inactive. Read mode impossible.',110,122),('C7/C8 positive terminal toward mixer. Load >=10k; powered speakers / amplifier.',218,245)]:elements.append(f'(text {q(text)} (at {x} {y} 0) (effects (font (size 1.27 1.27)) (justify left)) (uuid {uid(text)}))')
content=f'(kicad_sch (version 20250114) (generator "solderdemon_audio") (uuid {uid("root")}) (paper "A3") (title_block (title "SolderDemon m68k Audio / YM2149F") (date "2026-09-29") (rev "r1-prototype") (company "SolderDemon") (comment 1 "Copyright (c) 2026 SolderDemon, CERN OHL v1.2")) (lib_symbols '+''.join(dump(s) for s in symbols.values())+')'+''.join(elements)+'(sheet_instances (path "/" (page "1"))))'
(ROOT/(NAME+'.kicad_sch')).write_text(content,encoding='utf-8')
import copy
local=[]
for k,s in symbols.items():
    if k.startswith('SolderDemonAudio:'):t=copy.deepcopy(s);t[1]=k.split(':')[1];local.append(t)
(ROOT/'SolderDemonAudio.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "solderdemon_audio")'+''.join(dump(s) for s in local)+')',encoding='utf-8')
(ROOT/'sym-lib-table').write_text('(sym_lib_table (lib (name "SolderDemonAudio") (type "KiCad") (uri "${KIPRJMOD}/SolderDemonAudio.kicad_sym") (options "") (descr "Audio card symbols")))')
b=pcb.BOARD();b.SetCopperLayerCount(2);v=lambda x,y:pcb.VECTOR2I(pcb.FromMM(x),pcb.FromMM(y))
netnames=sorted({n for p in parts for n in p['nets'].values() if n});nets={}
for i,n in enumerate(netnames,1):ni=pcb.NETINFO_ITEM(b,'/'+n,i);b.Add(ni);nets[n]=ni
for p in parts:
    if p['ref'].startswith('#'):continue
    lib,name=p['fp'].split(':');f=pcb.FootprintLoad(str(LIB/'footprints'/(lib+'.pretty')),name);assert f,p['fp']
    f.SetReference(p['ref']);f.SetValue(p['value']);f.SetPath(pcb.KIID_PATH('/'+uid('root')+'/'+p['uuid']));f.SetOrientationDegrees(p['rot']);f.SetPosition(v(*p['pos']));b.Add(f)
    for pad in f.Pads():
        n=p['nets'].get(pad.GetNumber())
        if n:pad.SetNet(nets[n])
    f.Value().SetVisible(False);f.Reference().SetTextSize(v(1,1));f.Reference().SetTextThickness(pcb.FromMM(.15));f.Reference().SetTextAngle(pcb.EDA_ANGLE(0,pcb.DEGREES_T))
    rx,ry=p['pos']
    if p['ref'].startswith('U'):rx+=10;ry-=3.81
    elif p['ref'].startswith('R'):rx+=3.81;ry-=2.5
    elif p['ref'].startswith('C'):ry-=4.4
    elif p['ref']=='J1':rx=5;ry=H-10
    elif p['ref']=='J2':rx=8;ry=9.7
    elif p['ref']=='J3':ry-=2.4
    elif p['ref']=='X1':rx+=3.81;ry-=4
    f.Reference().SetPosition(v(rx,ry))
    # J1/J2 overhang the outline; move their silkscreen beyond the board edge to a drawing layer.
    if p['ref'] in ['J1','J2']:
        for g in [g for g in f.GraphicalItems() if isinstance(g,pcb.PCB_SHAPE) and g.GetLayer()==pcb.F_SilkS]:
            if any(not(.25<=pcb.ToMM(c)<=lim-.25) for pt in (g.GetStart(),g.GetEnd()) for c,lim in ((pt.x,W),(pt.y,H))):g.SetLayer(pcb.Dwgs_User)
# W x H outline: RT corners away from the bus, RB at the bus edge.
# J1 socket body overhangs the bottom edge; J2 closes the left edge with its own cutout.
def edge(shape,*pts):
    s=pcb.PCB_SHAPE(b);s.SetShape(shape);s.SetLayer(pcb.Edge_Cuts);s.SetWidth(pcb.FromMM(.05))
    if shape==pcb.SHAPE_T_ARC:s.SetArcGeometry(*[v(*a) for a in pts])
    else:s.SetStart(v(*pts[0]));s.SetEnd(v(*pts[1]))
    b.Add(s)
h=math.sqrt(.5);jy=next(p['pos'][1] for p in parts if p['ref']=='J2')
for a,c in [((RT,0),(W-RT,0)),((W,RT),(W,H-RB)),((W-RB,H),(RB,H)),((0,H-RB),(0,jy+6.5)),((0,jy-6.5),(0,RT))]:edge(pcb.SHAPE_T_SEGMENT,a,c)
# Corner arcs as (start, centre, end), drawn clockwise.
for (sx,sy),(cx,cy),(ex,ey) in [((W-RT,0),(W-RT,RT),(W,RT)),((W,H-RB),(W-RB,H-RB),(W-RB,H)),((RB,H),(RB,H-RB),(0,H-RB)),((0,RT),(RT,RT),(RT,0))]:
    mx=cx+(sx+ex-2*cx)*h;my=cy+(sy+ey-2*cy)*h
    edge(pcb.SHAPE_T_ARC,(sx,sy),(mx,my),(ex,ey))
# The product name and logo are added by brand_project.py.
for text,x,y,size in [('LINE OUT',6.5,25,1)]:
    t=pcb.PCB_TEXT(b);t.SetText(text);t.SetPosition(v(x,y));t.SetTextSize(v(size,size));t.SetTextThickness(pcb.FromMM(.15));t.SetLayer(pcb.F_SilkS);b.Add(t)
# Revision mark in copper under the mask, the same 2.5 mm stroke text as on solderdemon_6502. The GND pour
# knocks a text out by its bounding box, so the letters go in as polygons and the pour follows their outline.
# Placed before routing so the router keeps clear.
t=pcb.PCB_TEXT(b);t.SetText('r1');t.SetPosition(v(88,50.5));t.SetTextSize(v(2.5,2.5));t.SetTextThickness(pcb.FromMM(.6));t.SetLayer(pcb.F_Cu)
glyphs=pcb.SHAPE_POLY_SET();t.TransformTextToPolySet(glyphs,0,pcb.FromMM(.005),pcb.ERROR_INSIDE);glyphs.Simplify()
for i in range(glyphs.OutlineCount()):  # stroke glyphs of 'r1' have no holes
    o=glyphs.Outline(i);g=pcb.PCB_SHAPE(b,pcb.SHAPE_T_POLY);g.SetPolyPoints(pcb.VECTOR_VECTOR2I([o.CPoint(k) for k in range(o.PointCount())]))
    g.SetFilled(True);g.SetWidth(0);g.SetLayer(pcb.F_Cu);b.Add(g)
settings=b.GetDesignSettings();settings.m_MinClearance=pcb.FromMM(.2);settings.m_TrackMinWidth=pcb.FromMM(.25);settings.m_ViasMinSize=pcb.FromMM(.65);settings.m_MinThroughDrill=pcb.FromMM(.3)
# SaveBoard writes the settings of this fresh board into .kicad_pro/.kicad_prl; the DRC rules live there.
kept={f:f.read_bytes() for f in (ROOT/(NAME+'.kicad_pro'),ROOT/(NAME+'.kicad_prl')) if f.exists()}
pcb.SaveBoard(str(ROOT/'tmp'/'placement.kicad_pcb'),b);pcb.SaveBoard(str(ROOT/(NAME+'.kicad_pcb')),b);pcb.ExportSpecctraDSN(b,str(ROOT/'routing.dsn'))
for f,data in kept.items():f.write_bytes(data)
dsn=(ROOT/'routing.dsn').read_text();dsn=dsn.replace('(width 200)','(width 250)').replace('600:300_um','650:300_um').replace('(circle F.Cu 600)','(circle F.Cu 650)').replace('(circle B.Cu 600)','(circle B.Cu 650)');(ROOT/'routing.dsn').write_text(dsn)
(ROOT/'design.json').write_text(json.dumps(parts,indent=2),encoding='utf-8')
with (ROOT/'BOM.csv').open('w',newline='',encoding='utf-8-sig') as out:
    w=csv.writer(out);w.writerow(['Reference','Value','Footprint']);w.writerows((p['ref'],p['value'],p['fp']) for p in parts if not p['ref'].startswith('#'))
print('Generated',len(parts),'symbols;',len(netnames),'nets;',f'{W}x{H} mm')
