"""Final audio-card build step: brand the existing routed KiCad files.

Use KiCad's Python after finish_board.py and sync_metadata.py. This script does
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
NOTICE = 'Copyright (c) 2026 SolderDemon, CERN OHL v1.2'
# Bottom silkscreen, mirrored, in the free area between U4, U2, X1 and the test points.
BACK_TEXT = (('Copyright (c) 2026 SolderDemon', 54, 61), ('CERN OHL v1.2', 54, 62.6))
CLI = os.environ.get('KICAD_CLI', 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')


def brand_schematic(path):
    source = path.read_text(encoding='utf-8')
    result = source.replace('(project "rosco_m68k-audio"', f'(project "{NAME}"')
    result = result.replace('(title "rosco_m68k Audio / YM2149F")', f'(title "{TITLE}")')
    result = result.replace('(date "2026-09-14")', '(date "2026-09-29")', 1)
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
    product_text = [drawing for drawing in board.GetDrawings()
                    if isinstance(drawing, pcb.PCB_TEXT) and drawing.GetText() in
                    ('rosco_m68k AUDIO', 'SolderDemon m68k Audio')]
    if len(product_text) != 1:
        raise RuntimeError(f'expected one product label on PCB, found {len(product_text)}')
    drawing = product_text[0]
    position = pcb.VECTOR2I(pcb.FromMM(60), pcb.FromMM(5))
    size = pcb.VECTOR2I(pcb.FromMM(1.5), pcb.FromMM(1.5))
    if (drawing.GetText() != 'SolderDemon m68k Audio' or
            drawing.GetPosition() != position or drawing.GetTextSize() != size):
        drawing.SetText('SolderDemon m68k Audio')
        drawing.SetPosition(position)
        drawing.SetTextSize(size)
        changed = True
    back = {drawing.GetText() for drawing in board.GetDrawings()
            if isinstance(drawing, pcb.PCB_TEXT) and drawing.GetLayer() == pcb.B_SilkS}
    for text, x, y in BACK_TEXT:
        if text in back:
            continue
        drawing = pcb.PCB_TEXT(board)
        drawing.SetText(text)
        drawing.SetLayer(pcb.B_SilkS)
        drawing.SetPosition(pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y)))
        drawing.SetTextSize(pcb.VECTOR2I(pcb.FromMM(.8), pcb.FromMM(.8)))
        drawing.SetTextThickness(pcb.FromMM(.12))
        drawing.SetMirrored(True)
        board.Add(drawing)
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
