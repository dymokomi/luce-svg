#!/usr/bin/env python3
"""Render resvg's test suite with luce-svg and compare every test with its reference PNG.

The suite is resvg's crates/resvg/tests/tests (clone https://github.com/linebender/resvg
into ../.donors/resvg; it is never committed here). Each SVG is drawn 300 pixels wide by
build/suite (tools/suite.lucb), as resvg draws its references. A pixel differs when any
of its premultiplied RGBA8 channels is off by more than --threshold; a test passes when
at most --allowed of its pixels differ (a fraction of the image). The fuzzy rule absorbs
anti-aliasing differences (exact area here, supersampling in resvg) but not a missing
or misplaced feature. Prints a pass table per feature directory and per category.

  build/env/bin/python tools/suite.py [--only painting/fill] [--save run.json]
                                      [--compare run.json] [--list-failing] [--jobs 8]
"""
import argparse, json, os, struct, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT.parent / ".donors/resvg/crates/resvg/tests/tests"
OUT = ROOT / "build/suite-out"
TOOL = ROOT / "build/suite"


def build():
    base = os.environ.get("LUCE_BASE", "luce-base")
    subprocess.run([base, "build", str(ROOT / "tools/suite.lucb"), "-o", str(TOOL), "--release"],
                   cwd=ROOT, check=True)


def render_chunk(job, paths, timeout):
    """Render `paths` into OUT/<job>-<n>.rgba, restarting past any file that crashes
    or hangs the tool. Returns the indices that crashed."""
    crashed = []
    start = 0
    while start < len(paths):
        listing = OUT / f"list-{job}.txt"
        listing.write_text("\n".join(str(p) for p in paths[start:]) + "\n")
        sub = OUT / f"job-{job}-{start}"
        sub.mkdir(exist_ok=True)
        try:
            run = subprocess.run([str(TOOL), str(listing), str(sub)], capture_output=True, timeout=timeout)
            ok = run.returncode == 0
        except subprocess.TimeoutExpired:
            ok = False
        done = start
        for n in range(len(paths) - start):
            target = sub / f"{n}.rgba"
            if target.exists():
                target.rename(OUT / f"{job}-{start + n}.rgba")
                done = start + n + 1
        if ok:
            break
        # The first file without output after the last one written is the culprit.
        culprit = done
        while culprit < len(paths) and (OUT / f"{job}-{culprit}.rgba").exists():
            culprit += 1
        if culprit >= len(paths):
            break
        crashed.append(culprit)
        start = culprit + 1
    return crashed


def load_ours(path):
    data = path.read_bytes()
    w, h = struct.unpack("<II", data[:8])
    return np.frombuffer(data[8:], dtype=np.uint8).reshape(h, w, 4)


def premultiplied(rgba):
    a = rgba[:, :, 3:4].astype(np.float32) / 255.0
    out = rgba.astype(np.float32)
    out[:, :, :3] *= a
    return out


def compare(ours, reference, threshold, allowed):
    if ours is None:
        return False, 1.0
    if ours.shape != reference.shape:
        return False, 1.0
    diff = np.abs(premultiplied(ours) - premultiplied(reference)).max(axis=2)
    bad = float((diff > threshold).mean())
    return bad <= allowed, bad


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", default="", help="run tests whose path contains this")
    p.add_argument("--threshold", type=int, default=32)
    p.add_argument("--allowed", type=float, default=0.005)
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--save", default="")
    p.add_argument("--compare", default="")
    p.add_argument("--list-failing", action="store_true")
    p.add_argument("--no-build", action="store_true")
    a = p.parse_args()
    if not SUITE.exists():
        sys.exit(f"no suite at {SUITE}: clone https://github.com/linebender/resvg into ../.donors/resvg")
    if not a.no_build:
        build()
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.rglob("*.rgba"):
        stale.unlink()
    tests = sorted(t for t in SUITE.rglob("*.svg") if a.only in str(t.relative_to(SUITE)))
    chunks = [tests[i::a.jobs] for i in range(a.jobs)]
    with ThreadPoolExecutor(a.jobs) as pool:
        crashes = list(pool.map(lambda j: render_chunk(j, chunks[j], a.timeout), range(len(chunks))))
    results = {}
    for job, chunk in enumerate(chunks):
        for n, test in enumerate(chunk):
            name = str(test.relative_to(SUITE))[:-4]
            path = OUT / f"{job}-{n}.rgba"
            ours = load_ours(path) if path.exists() else None
            reference = np.asarray(Image.open(test.with_suffix(".png")).convert("RGBA"))
            ok, bad = compare(ours, reference, a.threshold, a.allowed)
            results[name] = {"pass": ok, "bad": round(bad, 5), "crash": n in crashes[job]}
            if ours is not None and not ok:
                Image.fromarray(np.ascontiguousarray(ours)).save(OUT / (name.replace("/", "_") + ".png"))
    table = {}
    for name, r in results.items():
        feature = "/".join(name.split("/")[:2])
        row = table.setdefault(feature, [0, 0, 0])
        row[0] += r["pass"]
        row[1] += 1
        row[2] += r["crash"]
    categories = {}
    print(f"{'feature':44} {'pass':>5} {'of':>5}")
    for feature in sorted(table):
        passed, total, crashed = table[feature]
        print(f"{feature:44} {passed:5} {total:5}" + (f"  ({crashed} crashed)" if crashed else ""))
        cat = categories.setdefault(feature.split("/")[0], [0, 0])
        cat[0] += passed
        cat[1] += total
    print()
    for cat in sorted(categories):
        print(f"{cat:44} {categories[cat][0]:5} {categories[cat][1]:5}")
    passed = sum(r["pass"] for r in results.values())
    print(f"{'total':44} {passed:5} {len(results):5}")
    if a.compare:
        before = json.loads(Path(a.compare).read_text())
        gained = sorted(n for n, r in results.items() if r["pass"] and not before.get(n, {}).get("pass"))
        lost = sorted(n for n, r in results.items() if not r["pass"] and before.get(n, {}).get("pass"))
        print(f"\nnewly passing: {len(gained)}  newly failing: {len(lost)}")
        for n in lost:
            print("  LOST", n, results[n]["bad"])
    if a.list_failing:
        for n, r in sorted(results.items()):
            if not r["pass"]:
                print(f"  fail {r['bad']:.4f} {'CRASH ' if r['crash'] else ''}{n}")
    if a.save:
        Path(a.save).write_text(json.dumps(results, indent=0, sort_keys=True))


if __name__ == "__main__":
    main()
