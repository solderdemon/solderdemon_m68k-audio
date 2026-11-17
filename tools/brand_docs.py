"""Apply SolderDemon product naming to the audio board documentation.

The hardware and software keep rosco_m68k compatibility identifiers. This
script changes only the project title, introductory prose, and KiCad file
references in README.md and DESIGN.md. It is safe to run repeatedly.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CHANGES = {
    "README.md": (
        (
            "# rosco_m68k Audio Board",
            "# SolderDemon m68k Audio Board",
        ),
        (
            "A Yamaha YM2149F programmable sound generator (PSG) expansion card for the "
            "[rosco_m68k](https://github.com/rosco-m68k/rosco_m68k) Motorola 68000/68010 "
            "single-board computer.",
            "A SolderDemon Yamaha YM2149F programmable sound generator (PSG) expansion card "
            "for SolderDemon m68k, compatible with the "
            "[rosco_m68k](https://github.com/rosco-m68k/rosco_m68k) Motorola 68000/68010 "
            "computer and its expansion bus.",
        ),
        (
            "`rosco_m68k-audio.kicad_pro`, `rosco_m68k-audio.kicad_sch`, "
            "`rosco_m68k-audio.kicad_pcb`",
            "`solderdemon_m68k-audio.kicad_pro`, `solderdemon_m68k-audio.kicad_sch`, "
            "`solderdemon_m68k-audio.kicad_pcb`",
        ),
        (
            "[`rosco_m68k-audio.pdf`](rosco_m68k-audio.pdf)",
            "[`solderdemon_m68k-audio.pdf`](solderdemon_m68k-audio.pdf)",
        ),
    ),
    "DESIGN.md": (
        (
            "# rosco_m68k-audio — design intake",
            "# SolderDemon m68k Audio — design intake",
        ),
        (
            "Sound expansion card for rosco_m68k, using Yamaha YM2149 "
            "(proposed DIP-40 YM2149F).",
            "Sound expansion card for SolderDemon m68k, compatible with the rosco_m68k "
            "expansion bus, using Yamaha YM2149 (proposed DIP-40 YM2149F).",
        ),
        (
            "- The initial rosco_m68k-audio.kicad_sch and .kicad_pcb are empty KiCad 10 "
            "project files.",
            "- At project intake, the initial KiCad 10 schematic and PCB files were empty. "
            "The current project files are `solderdemon_m68k-audio.kicad_sch` and "
            "`solderdemon_m68k-audio.kicad_pcb`.",
        ),
    ),
}


def update(path: Path, changes: tuple[tuple[str, str], ...]) -> bool:
    original = path.read_bytes()
    result = original
    for before, after in changes:
        old = before.encode("utf-8")
        new = after.encode("utf-8")
        if old in result:
            result = result.replace(old, new)
        elif new not in result:
            raise ValueError(f"Expected text missing from {path}: {before[:70]}")
    if result != original:
        path.write_bytes(result)
        return True
    return False


if __name__ == "__main__":
    for name, changes in CHANGES.items():
        path = ROOT / name
        print(f"{path.name}: {'updated' if update(path, changes) else 'unchanged'}")
