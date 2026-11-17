from pathlib import Path
import pcbnew as p, xml.etree.ElementTree as ET, json
root=Path(__file__).resolve().parents[1]
b=p.LoadBoard(str(root / 'design' / 'solderdemon_m68k-audio.kicad_pcb'))
parts={a['ref']:a for a in json.loads((root / 'design' / 'design.json').read_text())}
x=ET.parse(root / 'design' / 'schematic.xml');pininfo={}
for n in x.findall('./nets/net'):
    for a in n.findall('node'):pininfo[(a.get('ref'),a.get('pin'))]=(n.get('name'),a.get('pinfunction'),a.get('pintype'))
for f in b.GetFootprints():
    if f.GetReference() not in parts:continue  # LOGO1 is board-only
    f.SetExcludedFromBOM(False)
    f.SetFPID(p.LIB_ID(*parts[f.GetReference()]['fp'].split(':')))
    for pad in f.Pads():
        info=pininfo.get((f.GetReference(),pad.GetNumber()))
        if not info:continue
        name,func,typ=info
        ni=b.FindNet(name)
        if ni is None:
            ni=p.NETINFO_ITEM(b,name);b.Add(ni)
        pad.SetNet(ni)
        if func:pad.SetPinFunction(func)
        if typ:pad.SetPinType(typ)
p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(str(root / 'design' / 'solderdemon_m68k-audio.kicad_pcb'),b)
print('Synchronized library IDs and native no-connect nets.')

