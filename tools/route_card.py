"""Autoroute the board written by build_design.py and pour ground on both sides.

The work is in the workspace-wide tools/route_lib.py; this only names the card and its outline:
R4 on all four corners.

    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/route_card.py

ROUTE_MODE=fast|best|single and FREEROUTING_JAR behave as route_lib documents.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'tools'))
import route_lib

route_lib.route('solderdemon_m68k-audio', root=ROOT / 'design', corner=4.0)
