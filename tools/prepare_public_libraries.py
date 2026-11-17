#!/usr/bin/env python3
"""Copy the shared footprints used by this project into its KiCad library table."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
shared = root.parent / 'tools'
design = root / 'design'
for src, dst in [
    (shared / 'capacitors/SolderDemonCaps.pretty/C_Radial_5.08mm.kicad_mod', design / 'SolderDemonCaps.pretty/C_Radial_5.08mm.kicad_mod'),
    (shared / 'brand/SolderDemon.pretty/SolderDemon_Logo.kicad_mod', design / 'SolderDemonBrand.pretty/SolderDemon_Logo.kicad_mod'),
]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
(design / 'fp-lib-table').write_text('''(fp_lib_table
  (lib (name "SolderDemonAudio") (type "KiCad") (uri "${KIPRJMOD}/SolderDemonAudio.pretty") (options "") (descr "Audio card footprints"))
  (lib (name "SolderDemonCaps") (type "KiCad") (uri "${KIPRJMOD}/SolderDemonCaps.pretty") (options "") (descr "Radial capacitor"))
  (lib (name "SolderDemonBrand") (type "KiCad") (uri "${KIPRJMOD}/SolderDemonBrand.pretty") (options "") (descr "SolderDemon logo"))
)
''')
