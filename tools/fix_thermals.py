from pathlib import Path
import json,sys
import pcbnew as p
# Pads whose thermal spokes land on an isolated pour island get a solid zone connection.
# Usage: kicad-cli pcb drc --format json -o tmp/drc.json solderdemon_m68k-audio.kicad_pcb; python tools/fix_thermals.py tmp/drc.json
root=Path(__file__).resolve().parents[1]
report=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
starved={i['uuid'] for v in report.get('violations',[]) if v['type']=='starved_thermal' for i in v['items']}
b=p.LoadBoard(str(root/'solderdemon_m68k-audio.kicad_pcb'))
fixed=[]
for f in b.GetFootprints():
 for pad in f.Pads():
  if pad.m_Uuid.AsString() in starved:
   pad.SetLocalZoneConnection(p.ZONE_CONNECTION_FULL);fixed.append(f'{f.GetReference()}.{pad.GetNumber()}')
if fixed:
 p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(root/'solderdemon_m68k-audio.kicad_pcb'),b)
print('Solid zone connection:',', '.join(fixed) or 'none needed')
