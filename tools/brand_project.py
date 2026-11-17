"""Compatibility entry point for shared SolderDemon identity (silkscreen only)."""
from pathlib import Path
import subprocess, sys
subprocess.run([sys.executable, str(Path(__file__).resolve().parents[2] / 'tools/brand/apply_identity.py'), 'solderdemon_m68k-audio'], check=True)
