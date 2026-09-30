"""Export the branded audio schematic PDF and board previews from KiCad."""

from pathlib import Path
import os
import subprocess
import pymupdf


ROOT = Path(__file__).resolve().parents[1]
NAME = 'solderdemon_m68k-audio'
CLI = os.environ.get('KICAD_CLI', 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')


def run(*args):
    subprocess.run([CLI, *map(str, args)], cwd=ROOT, check=True)


def main():
    sch = ROOT / f'{NAME}.kicad_sch'
    pcb = ROOT / f'{NAME}.kicad_pcb'
    preview = ROOT / 'preview'
    preview.mkdir(exist_ok=True)
    run('sch', 'export', 'pdf', '-o', ROOT / f'{NAME}.pdf', sch)
    with pymupdf.open(ROOT / f'{NAME}.pdf') as document:
        document[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False).save(
            preview / 'schematic.png')
    # Side lights only: the top and camera lights leave a specular glare on the soldermask.
    lights = ('--light-top', '0', '--light-camera', '0', '--light-side', '0.8')
    run('pcb', 'render', '--width', '1600', '--height', '900', '--zoom', '0.9',
        '--rotate', '-35,0,30', *lights, '-o', ROOT / f'{NAME}-3d.png', pcb)
    run('pcb', 'render', '--width', '1280', '--height', '1280', '--side', 'top',
        '--rotate', '0,0,0', *lights, '-o', preview / 'top.png', pcb)
    run('pcb', 'export', 'svg', '--mode-single', '--layers', 'F.Cu,F.SilkS,Edge.Cuts',
        '--page-size-mode', '2', '-o', preview / f'{NAME}.svg', pcb)


if __name__ == '__main__':
    main()
