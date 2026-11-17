"""Compatibility entry point: build the checked r1 release using the shared script."""
from pathlib import Path
import subprocess, sys
subprocess.run([sys.executable, str(Path(__file__).resolve().parents[2] / 'tools/release_audio.py'), 'm68k'], check=True)
