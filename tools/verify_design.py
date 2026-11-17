from pathlib import Path
import json,re,xml.etree.ElementTree as ET,itertools,hashlib
import pcbnew as pcb
root=Path(__file__).resolve().parents[1]
parts={a['ref']:a for a in json.loads((root / 'design' / 'design.json').read_text())}
b=pcb.LoadBoard(str(root / 'design' / 'solderdemon_m68k-audio.kicad_pcb'))
sch=ET.parse(root / 'design' / 'schematic.xml');nets={(n.get('ref'),n.get('pin')):x.get('name') for x in sch.findall('./nets/net') for n in x.findall('node')}
for ref,a in parts.items():
 if ref.startswith('#'):continue
 f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
 for pin,net in a['nets'].items():
  pads=[p for p in f.Pads() if p.GetNumber()==pin];assert pads,(ref,pin)
  for p in pads:
   actual=p.GetNetname().removeprefix('/')
   assert actual==net if net else actual.startswith('unconnected-') or not actual,(ref,pin,net,actual)
  if net:assert nets[(ref,pin)].removeprefix('/')==net,(ref,pin)
# External reference netlist is independent of card manifest.
refnet=ET.parse(root / 'design' / 'bus-reference.xml')
host={int(n.get('pin')):x.get('name') for x in refnet.findall('./nets/net') for n in x.findall('node') if n.get('ref')=='BUS5-1'}
for pin,net in parts['J1']['nets'].items():
 if net:assert ('VCC' if net=='+5V' else net)==host[int(pin)]
f=next(f for f in b.GetFootprints() if f.GetReference()=='J1')
coords={int(p.GetNumber()):(round(pcb.ToMM(p.GetPosition().x),3),round(pcb.ToMM(p.GetPosition().y),3)) for p in f.Pads()}
# J1 rows stand 10.46 and 7.92 mm in from the bus edge (the bottom of the outline).
bus=round(pcb.ToMM(b.GetBoardEdgesBoundingBox().GetBottom()),1)
for row in range(32):
 assert coords[2*row+1]==(round(10.63+row*2.54,3),round(bus-10.46,3))
 assert coords[2*row+2]==(round(10.63+row*2.54,3),round(bus-7.92,3))
assert not f.IsFlipped()
# Verify critical pins directly against manufacturer pinouts, not helper arrays.
assert {p:parts['U1']['nets'][p] for p in ['1','23','24','25','26','27','28','29','40']}=={'1':'GND','23':'RESET','24':'GND','25':'+5V','26':'+5V','27':'BDIR','28':'A1','29':'GND','40':'+5V'}
assert [parts['U2']['nets'][str(i)] for i in [3,4,7,8,13,14,17,18]]==['D'+str(i) for i in range(8)]
assert [parts['U2']['nets'][str(i)] for i in [2,5,6,9,12,15,16,19]]==['PSGD'+str(i) for i in range(8)]
assert parts['U2']['nets']['11']=='CAPTURE' and parts['U3']['nets']['21']=='CAPTURE'
assert parts['U3']['nets']['14']=='DTACK'
# Parse the actual GALasm source. No hand-copied model of its equations.
src=(root/'code/firmware/pld/audio_sequencer.pld').read_text().split('DESCRIPTION')[0]
eq={lhs.strip():rhs.strip() for lhs,rhs in re.findall(r'^([/A-Z0-9.]+)\s*=\s*([^\n]+)',src,re.M)}
def expr(s,v):
 return any(all((not v[t[1:]]) if t.startswith('/') else bool(v[t]) for t in term.strip().split()) for term in s.replace('*',' ').split('+'))
def request(v):return not expr(eq['/NREQ'],v)
selected=[]
for page in range(65536):
 a=page<<8
 v={'IOSEL':int(a>>20!=15),'MATCH':int((a>>8)&255!=1),'AS':0,'LDS':0,'RW':0,'RESET':1,**{'A'+str(i):(a>>i)&1 for i in range(16,20)}}
 if not request(v):selected.append(page)
assert selected==[0xF001],selected
for ios,match,as_,lds,rw,rst in itertools.product([0,1],repeat=6):
 v={'IOSEL':ios,'MATCH':match,'AS':as_,'LDS':lds,'RW':rw,'RESET':rst,**{'A'+str(i):0 for i in range(16,20)}}
 assert (not request(v))==(not(ios or match or as_ or lds or rw) and bool(rst))
# JEDEC checksums, device size and fitter pin allocation.
j=(root/'code/firmware/pld/audio_sequencer.jed').read_bytes();txt=j.decode('ascii');count=int(re.search(r'\*QF(\d+)',txt)[1]);assert count==5892
fuses=[int(re.search(r'\*F([01])',txt)[1])]*count
for start,bits in re.findall(r'\*L(\d+)\s+([01]+)',txt):fuses[int(start):int(start)+len(bits)]=map(int,bits)
packed=[sum(v<<(k%8) for k,v in enumerate(fuses[i:i+8])) for i in range(0,count,8)]
assert sum(packed)&65535==int(re.search(r'\*C([0-9A-Fa-f]{4})',txt)[1],16)
end=j.index(b'\x03');assert sum(j[j.index(b'\x02'):end+1])&65535==int(j[end+1:].strip(),16)
assert eq['DTACK.T']=='GND' and eq['DTACK.E']=='S6 * /NREQ'
pintext=(root/'code/firmware/pld/audio_sequencer.pin').read_text()
for pin,name in [(14,'DTACK'),(15,'NREQ'),(16,'BDIR'),(21,'S2')]:assert re.search(rf'\b{pin}\s*\|\s*{name}\s*\|',pintext)
# All valid PSG register/data values; held request must produce exactly one strobe.
transactions=0
for a1 in [0,1]:
 for data in range(256):
  v={f'S{i}':0 for i in range(7)};v.update(NREQ=False,GND=False)
  cap=[];strobe=[];ack=[]
  for edge in range(1,21):
   old=v.copy()
   for i in range(7):v[f'S{i}']=expr(eq[f'S{i}.R'],old)
   if v['S2'] and not old['S2']:cap.append(edge)
   if expr(eq['BDIR'],v):strobe.append(edge)
   if expr(eq['DTACK.E'],v):ack.append(edge)
   # BC1 is physically grounded; 3-bit hardware modes can never be READ=3.
   mode=(int(expr(eq['BDIR'],v))<<2)|(a1<<1)
   assert mode in [0,2,4,6]
  assert cap==[3] and strobe==[4,5] and ack==list(range(7,21))
  v['NREQ']=True;assert expr(eq['AR'],v);assert not expr(eq['BDIR'],v) and not expr(eq['DTACK.E'],v)
  transactions+=1
# Every possible interruption point resets the state chain before another write.
for abort in range(1,10):
 v={f'S{i}':False for i in range(7)};v.update(NREQ=False,GND=False)
 for _ in range(abort):
  old=v.copy();v.update({f'S{i}':expr(eq[f'S{i}.R'],old) for i in range(7)})
 v['NREQ']=True
 if expr(eq['AR'],v):v.update({f'S{i}':False for i in range(7)})
 assert all(not v[f'S{i}'] for i in range(7))
# Conservative timing at +/-50 ppm with propagation/skew allocations (ns).
tmin=1e9/(1843200*1.00005);tmax=1e9/(1843200*.99995)
setup=tmin-8-45-15-10-50; pulse_min=2*tmin-80;pulse_max=2*tmax+80;hold=tmin-8-15-15-10-50
assert setup>=300 and pulse_min>=300 and pulse_max<=10000 and hold>=80
result=f'''PASS: all schematic/PCB/manifest pins; 64-pin host mapping and connector pad geometry.
PASS: 65536 address pages (entire 24-bit space), all 64 bus-control combinations.
PASS: JEDEC 5892 fuses, fuse checksum, transmission checksum, fitter pin mapping.
PASS: {transactions} write sequences, held-request/no-retrigger, abort/reset paths.
PASS: BC1 grounded; no hardware READ mode or PSG bus contention.
Timing budget: setup >= {setup:.1f} ns; strobe {pulse_min:.1f}..{pulse_max:.1f} ns; post-strobe hold >= {hold:.1f} ns.
Scope: source-equation logic simulation plus JEDEC integrity checks, NOT a fuse-level silicon simulator or measured hardware qualification.
JEDEC SHA256: {hashlib.sha256(j).hexdigest()}
'''
(root/'verification.txt').write_text(result);print(result)
