"""Final audio-card build step: brand the existing routed KiCad files.

Use KiCad's Python after route_card.py and sync_metadata.py. This script does
not replace the routed board, nets or footprints.
"""

from pathlib import Path
import os
import subprocess
import pcbnew as pcb
import wx


wx.Log.EnableLogging(False)
ROOT = Path(__file__).resolve().parents[1]
NAME = 'solderdemon_m68k-audio'
TITLE = 'SolderDemon m68k Audio / YM2149F'
NOTICE = 'Copyright (c) 2026 SolderDemon'
OLD_NOTICES = ('Copyright (c) 2026 SolderDemon, CERN OHL v1.2',)
# Bottom silkscreen, mirrored, behind the logo: the card details the front leaves out.
BACK_TEXT = (('YM2149F / ABC STEREO', 22.5, 4.5, 1.0), ('F00101 ADDR / F00103 DATA', 22.5, 6.5, .8),
             ('Copyright (c) 2026 SolderDemon', 22.5, 8.5, .8))
# 'J1  1' repeated the J1 designator; the footprint's square pad and silk corner mark pin 1.
DROPPED_TEXT = ('CERN OHL v1.2', 'SolderDemon m68k Audio', 'rosco_m68k AUDIO', 'r1  2026-09', 'J1  1')
CLI = os.environ.get('KICAD_CLI', 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
LIB = 'SolderDemonAudio'
LOGO_FP = 'SolderDemon_Logo'
# SolderDemon identity on the front: only the pixel logo (tools/make_logo.py) and the card name under it,
# between the jack and U1; the details are on the back (BACK_TEXT).
LX, LOGO_Y = 22.5, 8.2
IDENTITY = (('SolderDemon', 16.6, 1.5, True), ('m68k Audio Card', 18.6, 1.0, False))


def brand_schematic(path):
    source = path.read_text(encoding='utf-8')
    result = source.replace('(project "rosco_m68k-audio"', f'(project "{NAME}"')
    result = result.replace('(title "rosco_m68k Audio / YM2149F")', f'(title "{TITLE}")')
    result = result.replace('(date "2026-09-14")', '(date "2026-09-29")', 1)
    for old in OLD_NOTICES:
        result = result.replace(f'(comment 1 "{old}")', f'(comment 1 "{NOTICE}")')
    if '(company "SolderDemon")' not in result:
        result = result.replace('(rev "r1-prototype"))',
                                f'(rev "r1-prototype") (company "SolderDemon") (comment 1 "{NOTICE}"))', 1)
    if source != result:
        path.write_text(result, encoding='utf-8')


def brand_board(path):
    board = pcb.LoadBoard(str(path))
    title = board.GetTitleBlock()
    changed = False
    for get, set_, value in (
        (title.GetTitle, title.SetTitle, TITLE),
        (title.GetCompany, title.SetCompany, 'SolderDemon'),
        (title.GetDate, title.SetDate, '2026-09-29'),
    ):
        if get() != value:
            set_(value)
            changed = True
    if title.GetComment(0) != NOTICE:
        title.SetComment(0, NOTICE)
        changed = True
    # Removed items stay referenced until the end: a freed SWIG object breaks the others.
    back_only = {text for text, *_ in BACK_TEXT}
    gone = [drawing for drawing in board.GetDrawings()
            if isinstance(drawing, pcb.PCB_TEXT) and (drawing.GetText() in DROPPED_TEXT or
               drawing.GetText() in back_only and drawing.GetLayer() == pcb.F_SilkS)]
    for drawing in gone:
        board.Remove(drawing)
        changed = True
    changed |= place_references(board)
    changed |= add_identity(board)
    back = {drawing.GetText(): drawing for drawing in board.GetDrawings()
            if isinstance(drawing, pcb.PCB_TEXT) and drawing.GetLayer() == pcb.B_SilkS}
    for text, x, y, size in BACK_TEXT:
        drawing = back.get(text)
        if drawing is None:
            drawing = pcb.PCB_TEXT(board)
            drawing.SetText(text)
            drawing.SetLayer(pcb.B_SilkS)
            drawing.SetMirrored(True)
            board.Add(drawing)
        elif drawing.GetPosition() == mm(x, y) and drawing.GetTextSize() == mm(size, size):
            continue
        drawing.SetPosition(mm(x, y))
        drawing.SetTextSize(mm(size, size))
        drawing.SetTextThickness(pcb.FromMM(size * .15))
        changed = True
    if changed:
        project = path.with_suffix('.kicad_pro')
        saved_project = project.read_bytes()
        local_state = path.with_suffix('.kicad_prl')
        saved_state = local_state.read_bytes() if local_state.exists() else None
        pcb.SaveBoard(str(path), board)
        project.write_bytes(saved_project)  # SaveBoard may overwrite the DRC rules.
        if saved_state is not None:
            local_state.write_bytes(saved_state)


def mm(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def place_references(board):
    """Put resistor and 5.08 mm ceramic capacitor designators inside their body outlines."""
    changed = False
    for footprint in board.GetFootprints():
        ref = footprint.GetReference()
        if ref[0] not in 'RC' or not ref[1:].isdigit():
            continue
        pads = sorted(footprint.Pads(), key=lambda pad: pad.GetNumber())
        a, b = (pad.GetPosition() for pad in pads[:2])
        cx, cy = pcb.ToMM((a.x + b.x) // 2), pcb.ToMM((a.y + b.y) // 2)
        angle = 0
        if ref[0] == 'R':
            # DIN0207 body: 6.3 x 2.5 mm between the pads; the text runs along it.
            x, y = cx, cy
            angle = 90 if a.x == b.x else 0
        elif str(footprint.GetFPID().GetLibItemName()).startswith('CP_Radial'):
            # 6.3 mm can: C7 and C8 to the right, between the can and its bleeder; C6 above.
            x, y = (cx + 4.5, cy) if ref in ('C7', 'C8') else (cx, cy - 4.3)
        elif str(footprint.GetFPID().GetLibItemName()) == 'C_Radial_5.08mm':
            x, y = cx, cy                     # Centre of the rectangular body outline, between the pads
            angle = 90 if a.x == b.x else 0   # Follow the capacitor's lead axis
        else:
            x, y = cx, cy - 2.25              # 5.0 x 2.5 mm disc: just above its outline
        text = footprint.Reference()
        size = mm(1, 1)
        if (text.GetPosition() != mm(x, y) or text.GetTextAngleDegrees() != angle or
                text.GetTextSize() != size):
            text.SetPosition(mm(x, y))
            text.SetTextAngleDegrees(angle)
            text.SetTextSize(size)
            text.SetTextThickness(pcb.FromMM(.15))
            changed = True
    return changed


def add_identity(board):
    changed = False
    logo = board.FindFootprintByReference('LOGO1')
    if logo is None:
        logo = pcb.FootprintLoad(str(ROOT / f'{LIB}.pretty'), LOGO_FP)
        logo.SetFPID(pcb.LIB_ID(LIB, LOGO_FP))
        logo.SetReference('LOGO1')
        board.Add(logo)
    if logo.GetPosition() != mm(LX, LOGO_Y):
        logo.SetPosition(mm(LX, LOGO_Y))
        changed = True
    present = {drawing.GetText(): drawing for drawing in board.GetDrawings()
               if isinstance(drawing, pcb.PCB_TEXT) and drawing.GetLayer() == pcb.F_SilkS}
    for text, y, size, bold in IDENTITY:
        drawing = present.get(text)
        if drawing is None:
            drawing = pcb.PCB_TEXT(board)
            drawing.SetText(text)
            drawing.SetLayer(pcb.F_SilkS)
            board.Add(drawing)
        elif (drawing.GetPosition() == mm(LX, y) and drawing.GetTextSize() == mm(size, size)
                and drawing.IsBold() == bold and drawing.GetHorizJustify() == pcb.GR_TEXT_H_ALIGN_CENTER):
            continue
        drawing.SetHorizJustify(pcb.GR_TEXT_H_ALIGN_CENTER)
        drawing.SetPosition(mm(LX, y))
        drawing.SetTextSize(mm(size, size))
        drawing.SetTextThickness(pcb.FromMM(size * .15))
        drawing.SetBold(bold)
        changed = True
    return changed


def main():
    schematic = ROOT / f'{NAME}.kicad_sch'
    brand_schematic(schematic)
    brand_board(ROOT / f'{NAME}.kicad_pcb')
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml',
                    '-o', str(ROOT / 'schematic.xml'), str(schematic)],
                   cwd=ROOT, check=True)
    # The DSN already contains the completed pre-route placement. Keep its
    # geometry and routing rules exactly as exported, updating its source path.
    dsn = ROOT / 'routing.dsn'
    source = dsn.read_text(encoding='utf-8')
    old_path = str(ROOT.parent / 'rosco_m68k-audio' / 'routing.dsn')
    result = source.replace(old_path, str(dsn), 1)
    if result != source:
        dsn.write_text(result, encoding='utf-8')
    print(f'Branded {NAME} KiCad schematic and PCB')


if __name__ == '__main__':
    main()
