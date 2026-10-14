"""Random baseline: a uniform random guess over the answer space each question states. Should land near chance.

    python perception-benchmark/baselines/random.py [--seed 0] [--out predictions.jsonl]

Only the standard library is needed (this runs in CI).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# This file is called random.py: drop its own directory from the import path so `import random` gets the stdlib.
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != HERE]

import argparse  # noqa: E402
import json  # noqa: E402
import random as rnd  # noqa: E402

sys.path.insert(0, str(HERE.parent))
from bench import load_items, midi_to_note, note_range  # noqa: E402


def guess(item, rng):
    kind = item["answer_type"]
    if kind == "choice":
        return rng.choice(item["options"])
    if kind == "note":
        return midi_to_note(rng.choice(note_range(*item["range"])))
    if kind == "note_sequence":
        notes = note_range(*item["range"])
        return " ".join(midi_to_note(rng.choice(notes)) for _ in item["answer"])  # the question states the count
    lo, hi = item["range"]
    value = rng.randint(lo, hi) if item.get("integer") else rng.uniform(lo, hi)
    return f"{value:.4g} {item['unit']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(HERE / "results" / "random.jsonl"))
    args = ap.parse_args()
    rng = rnd.Random(args.seed)
    rows = [{"id": it["id"], "answer": guess(it, rng)} for it in load_items()]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote {len(rows)} random answers to {out}")


if __name__ == "__main__":
    main()
