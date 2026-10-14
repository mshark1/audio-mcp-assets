"""Score a predictions file against items.jsonl.

Usage:
    python perception-benchmark/score.py predictions.jsonl [--json out.json] [--name "my model"] [--items items.jsonl]

predictions.jsonl: one {"id": "...", "answer": ...} per line. Missing ids score 0 and are counted as missing.
Answers may be free-form strings; see bench.py for exactly what is accepted (units, note names, A/B, yes/no, ...).

Output: a readable table (per category and per task: n, score, chance, missing) and, with --json, the same numbers
plus per-item scores and, for numeric tasks, the absolute-error distribution (median, 90th percentile).
Chance is the expected score of a uniform random guess over the answer space stated in each question (bench.chance).
Only the standard library is needed.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench import ITEMS, chance, grade, load_items, parse_number  # noqa: E402


def load_predictions(path):
    preds = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if "id" not in row:
            sys.exit(f"{path}:{n}: each line needs an 'id'")
        preds[row["id"]] = row.get("answer")
    return preds


def summarize(rows):
    n = len(rows)
    return {"n": n, "score": sum(r["score"] for r in rows) / n, "chance": sum(r["chance"] for r in rows) / n,
            "missing": sum(r["missing"] for r in rows)}


def score(items, preds):
    rows = []
    for item in items:
        pred = preds.get(item["id"])
        row = {"id": item["id"], "category": item["category"], "task": item["task"], "difficulty": item["difficulty"],
               "trap": "trap" in item, "score": grade(item, pred), "chance": chance(item), "missing": pred is None}
        if item["answer_type"] == "numeric" and pred is not None:
            value = parse_number(pred, item.get("unit"))
            row["abs_error"] = None if value is None else abs(value - item["answer"])
        rows.append(row)
    known = {i["id"] for i in items}
    extra = sorted(set(preds) - known)

    def group(key):
        out = {}
        for r in rows:
            out.setdefault(r[key] if not callable(key) else key(r), []).append(r)
        return {k: summarize(v) for k, v in out.items()}

    errors = {}
    for r in rows:
        if r.get("abs_error") is not None:
            errors.setdefault(r["task"], []).append(r["abs_error"])
    error_stats = {t: {"n": len(e), "median": statistics.median(e),
                       "p90": sorted(e)[min(len(e) - 1, int(0.9 * len(e)))]} for t, e in errors.items()}
    return {
        "overall": summarize(rows),
        "macro_category_score": statistics.mean(s["score"] for s in group("category").values()),
        "by_category": group("category"),
        "by_task": group(lambda r: f"{r['category']}.{r['task']}"),
        "by_difficulty": group("difficulty"),
        "traps": summarize([r for r in rows if r["trap"]]),
        "numeric_abs_error": error_stats,
        "unknown_ids": extra,
        "items": rows,
    }


def table(result, name):
    lines = [f"Perception benchmark: {name}", "",
             f"{'group':<34}{'n':>5}{'score':>9}{'chance':>9}{'missing':>9}", "-" * 66]

    def row(label, s):
        lines.append(f"{label:<34}{s['n']:>5}{s['score']:>9.1%}{s['chance']:>9.1%}{s['missing']:>9}")

    for cat, s in result["by_category"].items():
        row(cat, s)
        for task, t in result["by_task"].items():
            if task.startswith(cat + "."):
                row("  " + task.split(".", 1)[1], t)
    lines.append("-" * 66)
    for diff in ("easy", "medium", "hard"):
        if diff in result["by_difficulty"]:
            row(f"difficulty: {diff}", result["by_difficulty"][diff])
    row("trap items", result["traps"])
    row("OVERALL (micro, per item)", result["overall"])
    lines.append(f"{'macro average over categories':<34}{'':>5}{result['macro_category_score']:>9.1%}")
    if result["numeric_abs_error"]:
        lines += ["", "numeric answers, absolute error:"]
        for task, e in result["numeric_abs_error"].items():
            lines.append(f"  {task:<20} n={e['n']:<3} median {e['median']:.4g}  p90 {e['p90']:.4g}")
    if result["unknown_ids"]:
        lines.append(f"\n{len(result['unknown_ids'])} predictions had unknown ids (ignored)")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("predictions")
    ap.add_argument("--items", default=str(ITEMS))
    ap.add_argument("--json", help="write the full result (including per-item scores) here")
    ap.add_argument("--name", default=None)
    args = ap.parse_args()
    result = score(load_items(args.items), load_predictions(args.predictions))
    result["name"] = args.name or Path(args.predictions).stem
    print(table(result, result["name"]))
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
