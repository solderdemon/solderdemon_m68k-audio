from pathlib import Path
import pcbnew as p
root=Path(__file__).resolve().parents[1]
b=p.LoadBoard(str(root/'tmp'/'placement.kicad_pcb'))
assert p.ImportSpecctraSES(b,str(root/'routing.ses'))
for layer in [p.F_Cu,p.B_Cu]:
 z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('/GND'));z.SetLocalClearance(p.FromMM(.25));z.SetThermalReliefGap(p.FromMM(.25));z.SetThermalReliefSpokeWidth(p.FromMM(.3));z.SetPadConnection(p.ZONE_CONNECTION_THERMAL)
 poly=z.Outline();poly.NewOutline()
 for x,y in [(0.6,0.6),(99.4,0.6),(99.4,99.4),(.6,99.4)]:poly.Append(int(p.FromMM(x)),int(p.FromMM(y)))
 b.Add(z)
for ref,pin in [('U2','10'),('C2','2'),('TP1','1')]:
 f=next(f for f in b.GetFootprints() if f.GetReference()==ref)
 next(a for a in f.Pads() if a.GetNumber()==pin).SetLocalZoneConnection(p.ZONE_CONNECTION_FULL)
# Collect items once: re-reading GetTracks() after deleting corrupts the SWIG wrapper.
items=list(b.GetTracks());vias=[t for t in items if t.GetClass()=='PCB_VIA'];tracks=[];seen=set()
pads=[pd for fp in b.GetFootprints() for pd in fp.Pads()]
# Drop duplicate segments (same layer/net/endpoints in either direction) the router leaves behind.
for t in items:
 if t.GetClass()!='PCB_TRACK':continue
 a,c=(t.GetStart().x,t.GetStart().y),(t.GetEnd().x,t.GetEnd().y)
 k=(t.GetLayer(),t.GetNetCode(),min(a,c),max(a,c))
 if k in seen or a==c:b.Delete(t)
 else:seen.add(k);tracks.append(t)
# Drop autorouter stubs whose end touches nothing on its layer (repeat until stable).
def touched(t,pt):
 return any(o is not t and o.GetLayer()==t.GetLayer() and pt in (o.GetStart(),o.GetEnd()) for o in tracks) or any(v.GetPosition()==pt for v in vias) or any(pd.IsOnLayer(t.GetLayer()) and pd.HitTest(pt) for pd in pads)
while True:
 dead=[t for t in tracks if not(touched(t,t.GetStart()) and touched(t,t.GetEnd()))]
 if not dead:break
 for t in dead:tracks.remove(t);b.Delete(t)
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(root/'solderdemon_m68k-audio.kicad_pcb'),b)
print('Routed segments/vias:',len(b.GetTracks()))
