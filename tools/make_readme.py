"""Regenerate README.md's file tables from the verified manifests, so the docs can never drift from the files.

Usage: python tools/make_readme.py
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GROUPS = [
    ("Tones and pitch", ("tone_", "scale_", "melody_", "chord_", "sweep_")),
    ("Noise and loudness", ("noise_", "loudness_", "silence_")),
    ("Stereo", ("stereo_",)),
    ("Timing and peaks", ("rhythm_", "impulse_", "true_peak_")),
    ("Problem files (and fixes)", ("problem_", "fixed_")),
]


def independent_count():
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "verify_independent.py"), str(ROOT / "reference-signals")],
        capture_output=True, text=True, encoding="utf-8",
    ).stdout
    m = re.search(r"(\d+)/(\d+) independent checks passed", out)
    if not m or m.group(1) != m.group(2):
        sys.exit("independent verification did not fully pass; fix that before regenerating the README")
    return int(m.group(2))


def main():
    m = json.loads((ROOT / "reference-signals" / "manifest.json").read_text(encoding="utf-8"))
    assets = m["assets"]
    if not all(r["pass"] for a in assets for r in a["verification"]):
        sys.exit("manifest has failing checks; rebuild before regenerating the README")
    rows = []
    for title, prefixes in GROUPS:
        rows.append(f"\n### {title}\n\n| File | What it is | Verified |\n|---|---|---|")
        for a in assets:
            if a["file"].startswith(prefixes):
                v, fmt = a["verification"], a["format"]
                ch = "stereo" if fmt["channels"] == 2 else "mono"
                rows.append(f"| `{a['file']}` | {a['description']} *({fmt['duration_s']:g} s, {ch})* | {len(v)}/{len(v)} |")
    n_checks = sum(len(a["verification"]) for a in assets)
    n_indep = independent_count()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    head, rest = readme.split("\n### Tones and pitch", 1)
    tail = rest[rest.index("\n## For AI agents") :]
    head = re.sub(r"\*\*\d+ test and calibration audio files", f"**{len(assets)} test and calibration audio files", head)
    head = re.sub(r"`manifest.json`: \d+ checks", f"`manifest.json`: {n_checks} checks", head)
    head = re.sub(r"`tools/verify_independent.py`: \d+ checks", f"`tools/verify_independent.py`: {n_indep} checks", head)
    (ROOT / "README.md").write_text(head + "\n".join(rows) + "\n" + tail, encoding="utf-8")
    print(f"README updated: {len(assets)} files, {n_checks} tool checks, {n_indep} independent checks")


if __name__ == "__main__":
    main()
