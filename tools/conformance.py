#!/usr/bin/env python3
"""Render every luciaos-assets icon with resvg and with luce-svg at one size, diff the
coverage, rank the mismatches and write side-by-side images for the worst ones.
  build/env/bin/python tools/conformance.py [--size 256] [--worst 12]"""
import argparse, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT.parent / "luciaos-assets/rounded/icons"
OUT = ROOT / "build/conformance"
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--size", type=int, default=256)
p.add_argument("--worst", type=int, default=12)
p.add_argument("--only", default="")
a = p.parse_args()
OUT.mkdir(parents=True, exist_ok=True)
render = ROOT / "build/render"
rows = []
for svg in sorted(ICONS.rglob("*.svg")):
    if a.only and a.only not in svg.stem:
        continue
    ref_png = OUT / f"{svg.stem}.ref.png"
    ours_pgm = OUT / f"{svg.stem}.ours.pgm"
    subprocess.run(["resvg", "--width", str(a.size), "--height", str(a.size), str(svg), str(ref_png)], check=True, capture_output=True)
    subprocess.run([str(render), str(svg), str(a.size), str(ours_pgm)], check=True, capture_output=True)
    ref = np.asarray(Image.open(ref_png).convert("RGBA"))[:, :, 3].astype(np.int16)
    ours = np.asarray(Image.open(ours_pgm)).astype(np.int16)
    diff = np.abs(ref - ours)
    mean = diff.mean() / 255.0
    bad = (diff > 128).mean()
    inter = ((ref > 127) & (ours > 127)).sum(); union = ((ref > 127) | (ours > 127)).sum()
    iou = inter / union if union else 1.0
    rows.append((bad, mean, iou, svg))
rows.sort(key=lambda r: -r[0])
print(f"{len(rows)} icons at {a.size}px; pixels off by >50%: mean {np.mean([r[0] for r in rows])*100:.2f}%  worst {rows[0][0]*100:.2f}%  IoU mean {np.mean([r[2] for r in rows]):.3f}")
print("worst:")
for bad, mean, iou, svg in rows[:a.worst]:
    print(f"  {bad*100:6.2f}% bad  mean {mean*100:5.2f}%  IoU {iou:.3f}  {svg.relative_to(ICONS)}")
# side-by-side sheet: reference | ours | diff
tiles = []
for bad, mean, iou, svg in rows[:a.worst]:
    ref = Image.open(OUT / f"{svg.stem}.ref.png").convert("RGBA").split()[3].convert("L")
    ours = Image.open(OUT / f"{svg.stem}.ours.pgm").convert("L")
    d = Image.fromarray(np.abs(np.asarray(ref).astype(np.int16) - np.asarray(ours).astype(np.int16)).astype(np.uint8))
    row = Image.new("L", (a.size * 3 + 8, a.size), 40)
    row.paste(ref, (0, 0)); row.paste(ours, (a.size + 4, 0)); row.paste(d, (2 * a.size + 8, 0))
    tiles.append(row)
if tiles:
    sheet = Image.new("L", (tiles[0].width, sum(t.height + 4 for t in tiles)), 40)
    y = 0
    for t in tiles:
        sheet.paste(t, (0, y)); y += t.height + 4
    sheet.save(OUT / "worst.png")
    print("sheet:", OUT / "worst.png")
good = [r for r in rows if r[0] < 0.002]
print(f"{len(good)} icons within 0.2% bad pixels")
