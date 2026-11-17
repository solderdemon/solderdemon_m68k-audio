"""Generate public-facing assembly documentation and release metadata."""
from pathlib import Path
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUILD = '''# SolderDemon m68k Audio r1 — assembly and build

The current r1 layout has not yet been tested on a physical board.

## Assembly

Use the m68k BOM and check the component footprints before ordering. The board is
100 × 72 mm, two-layer FR-4, 1.6 mm thick, with 1 oz copper. All components are
through-hole. Fit low-profile sockets: U1 DIP-40 (15.24 mm row spacing), U2 and
U4 DIP-20 (7.62 mm), and U3 DIP-24 (7.62 mm). Check socket and connector height
against the enclosure and adjacent cards. Match every pad and switch connection
before substituting the audio jack.

J3 is optional: pin 1 L, pin 2 GND, pin 3 R, in parallel with J2. Both are line
outputs for an amplifier or powered speakers, not headphones or passive speakers.

Install low components first, then sockets, connectors and capacitors. Check
capacitor polarity, IC notches and oscillator pin 1. Program U3 with the m68k
JEDEC in `code/firmware/pld/`; the 6502 firmware is different.

## First power-up

1. Inspect soldering and polarity, and check for a short between 5 V and GND.
2. Apply current-limited 5 V and verify the supply at the ICs and oscillator.
3. Verify the 1.8432 MHz PSG clock and that the host boots and resets normally.
4. Test channels A, B and C individually: A is left, B is centered and C is
   right. Test noise, envelope and both audio channels; test J3 if fitted.
5. Verify bus timing at the intended host clock. Logical simulation does not
   establish worst-case electrical timing.

## Regeneration

Full regeneration needs KiCad 10 Python with pcbnew, Java 25+, and the shared
SolderDemon hardware workspace `tools/` directory beside this repository,
including the routing, branding and capacitor libraries. Set `KICAD_CLI` and
`KICAD_SHARE` for the machine. Run `tools/build_design.py`,
`tools/verify_design.py` and `tools/route_card.py`, then the shared
`tools/release_audio.py m68k` from the workspace. After release generation, run
`python3 tools/prepare_public_libraries.py` to refresh the local footprints.
The generator clears the tracks; a full rebuild requires rerouting. The KiCad
project and manufacturing files can be inspected without the shared workspace.

## Manufacturing files

`manufacturing/` contains Gerbers, drill files, BOM, positions, schematic PDF,
PLD files and ordering archives. The Gerber archive contains fabrication files;
the release archive also includes assembly and verification documents.
`release.json` records checks and input hashes. J3 is optional, but its plated
holes remain in the fabrication files.
'''

def write_docs(root=ROOT):
    readme = root / 'README.md'
    text = readme.read_text(encoding='utf-8-sig')
    text = re.sub(r'\s*<!-- audio-r1 -->.*?<!-- /audio-r1 -->\s*', '\n\n', text, flags=re.S)
    status = '**Status:** The current r1 layout has not yet been tested on a physical board. See the [assembly and build guide](docs/BUILD.md).\n'
    if status not in text:
        marker = '![Assembled SolderDemon m68k Audio Board]'
        text = text.replace(marker, status + '\n' + marker, 1)
    readme.write_text(text, encoding='utf-8')
    (root / 'docs' / 'BUILD.md').write_text(BUILD, encoding='utf-8')
    (root / 'DESIGN.md').write_text('# SolderDemon m68k Audio r1\n\nSee the [README](README.md) and [assembly and build guide](docs/BUILD.md).\n', encoding='utf-8')

def refresh_release(root=ROOT):
    out = root / 'manufacturing'
    (out / 'BUILD.md').write_text(BUILD, encoding='utf-8')
    (out / 'batch-acceptance.csv').unlink(missing_ok=True)
    manifest = out / 'release.json'
    data = json.loads(manifest.read_text())
    data.pop('previous_hardware', None)
    data['r1_hardware'] = 'Current layout has not been physically tested'
    data['inputs'] = {('design/' + k if k.startswith('solderdemon_m68k-audio.kicad_') else k.replace('code/pld/', 'code/firmware/pld/')): v for k, v in data['inputs'].items()}
    manifest.write_text(json.dumps(data, indent=2) + '\n')
    archive = out / 'solderdemon_m68k-audio-r1-2026-11-12-release.zip'
    tmp = archive.with_suffix('.tmp')
    with zipfile.ZipFile(archive) as src, zipfile.ZipFile(tmp, 'w') as dst:
        for item in src.infolist():
            if item.filename == 'batch-acceptance.csv':
                continue
            contents = (out / item.filename).read_bytes() if item.filename in ('BUILD.md', 'release.json') else src.read(item.filename)
            dst.writestr(item, contents)
    tmp.replace(archive)

if __name__ == '__main__':
    write_docs()
    refresh_release()
