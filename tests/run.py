#!/usr/bin/env python3
"""Build and run luce-svg's test blocks in native and C modes. LUCE_BASE names the
compiler; by default it is the luce-base checkout beside this package."""
import os, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get("LUCE_BASE") or ROOT.parent / "luce-base/build/luce-base").resolve()
MODES = [["--native"], ["--backend=c"]]
env = dict(os.environ, LUCE_BASE=str(BASE))
for flags in MODES:
    subprocess.run([str(BASE), "test", str(ROOT / "src/luce_svg/svg"), *flags],
                   env=env, check=True, timeout=180)
print("PASS luce-svg parser, flattener and rasterisers")
