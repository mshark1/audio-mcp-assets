"""Tool-ceiling baseline: answer every item by calling audio-mcp tools over MCP and mapping measurements to answers.

This is NOT a language model and NOT an agent. It is a fixed, hand-written rule per task (below, in ANSWER), so it
shows what the tools make possible when they are used well: an upper reference for a tool-using agent, which still
has to choose the right tool, read the right field and reason correctly. Rules are generic per task (no per-item
or per-file special cases), and the audio is first copied to opaque names (001.wav, ...) so nothing can be read
from file names.

    python perception-benchmark/baselines/audio_mcp_tools.py [--out results/audio_mcp_tools.jsonl]

Needs audio-mcp (pip install "audio-mcp>=0.2.0"). Writes predictions plus, alongside, a *_trace.jsonl with the raw
measurement behind each answer, so misses can be traced to a specific tool output.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# baselines/random.py would shadow the stdlib `random` (used by tempfile): keep this directory off the import path.
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != HERE]

import argparse  # noqa: E402
import asyncio  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402

from mcp.client.session import ClientSession  # noqa: E402
from mcp.client.stdio import StdioServerParameters, stdio_client  # noqa: E402

sys.path.insert(0, str(HERE.parent))
from bench import ROOT, load_items  # noqa: E402


class Tools:
    """Calls audio-mcp tools over MCP and caches results per (tool, file)."""

    def __init__(self, session, blind):
        self.session, self.blind, self.cache, self.calls = session, blind, {}, 0

    async def __call__(self, tool, rel):
        key = (tool, rel)
        if key not in self.cache:
            self.calls += 1
            res = await self.session.call_tool(tool, {"path": self.blind[rel]})
            text = next((c.text for c in res.content if c.type == "text"), "")
            if res.is_error:
                raise RuntimeError(f"{tool} failed on {rel}: {text}")
            self.cache[key] = json.loads(text)
        return self.cache[key]


def issue(analysis, pattern):
    for i in analysis.get("issues", []):
        m = re.search(pattern, i["message"])
        if m:
            return m
    return None


def lufs_value(a):
    v = a["levels"]["lufs_integrated"]
    return float("-inf") if v is None else v


async def answer(item, t):
    """Return (answer, evidence) for one item."""
    task, files = item["task"], item["audio"]
    a = await t("audio_analyze", files[0])
    lv, sil = a["levels"], a["silence"]
    if task == "note_name":
        return a["pitch"]["median"]["note"], a["pitch"]["median"]
    if task == "frequency":
        return a["pitch"]["median"]["hz"], a["pitch"]["median"]
    if task == "higher":
        b = await t("audio_analyze", files[1])
        ha, hb = a["pitch"]["median"]["hz"], b["pitch"]["median"]["hz"]
        return ("A" if ha > hb else "B"), {"hz": [ha, hb]}
    if task == "lufs":
        return lv["lufs_integrated"], {"lufs_integrated": lv["lufs_integrated"]}
    if task == "louder":
        b = await t("audio_analyze", files[1])
        la, lb = lufs_value(a), lufs_value(b)
        return ("A" if la > lb else "B"), {"lufs": [lv["lufs_integrated"], b["levels"]["lufs_integrated"]]}
    if task == "rms":
        return lv["rms_dbfs"], {"rms_dbfs": lv["rms_dbfs"]}
    if task == "sample_peak":
        return lv["peak_dbfs"], {"peak_dbfs": lv["peak_dbfs"]}
    if task == "true_peak":
        return lv["true_peak_dbtp"], {"true_peak_dbtp": lv["true_peak_dbtp"]}
    if task == "true_peak_over":
        d = lv["true_peak_dbtp"] - lv["peak_dbfs"]
        return ("yes" if d >= 1 else "no"), {"true_minus_sample_db": round(d, 2)}
    if task == "clipping":
        return ("yes" if lv["clipped_samples"] > 0 else "no"), {"clipped_samples": lv["clipped_samples"]}
    if task == "dc_offset":
        return ("yes" if abs(lv["dc_offset"]) >= 0.01 else "no"), {"dc_offset": lv["dc_offset"]}
    if task == "mains_hum":
        m = issue(a, r"Mains hum at (\d+) Hz")
        return (f"{m.group(1)} Hz" if m else "none"), {"issue": m.group(0) if m else None}
    if task == "abrupt_start":
        m = issue(a, r"Starts abruptly")
        return ("yes" if m else "no"), {"issue": bool(m), "start_amplitude": a["edges"]["start_amplitude"]}
    if task == "loop_click":
        seam = a["edges"]["loop_seam"]
        return ("yes" if seam["likely_click"] else "no"), seam
    if task == "duration":
        return a["duration_s"], {"duration_s": a["duration_s"]}
    if task == "leading_silence":
        return sil["leading_s"], {"leading_s": sil["leading_s"]}
    if task == "trailing_silence":
        return sil["trailing_s"], {"trailing_s": sil["trailing_s"]}
    if task == "all_silent":
        return ("yes" if sil.get("all_silent") else "no"), {"all_silent": sil.get("all_silent")}
    if task == "onset_count":
        ev = await t("audio_events", files[0])
        return ev["event_count"], {"event_count": ev["event_count"], "rhythm.onset_count": a["rhythm"]["onset_count"]}
    if task == "tempo":
        bpm = a["rhythm"].get("tempo_bpm")
        return bpm, {"tempo_bpm": bpm, "onset_count": a["rhythm"]["onset_count"]}
    if task == "impulse_time":
        ev = await t("audio_events", files[0])
        start = ev["events"][0]["start_s"] if ev["events"] else None
        return start, {"events": ev["as_text"]}
    if task == "correlation":
        c = a["stereo"]["correlation"]
        if c is None:
            return None, a["stereo"]
        return ("positive" if c > 0.3 else "negative" if c < -0.3 else "near zero"), {"correlation": c}
    if task == "channels":
        st = a["stereo"]
        if st["width"] == "one channel silent":
            return ("left only" if st["balance_db"] > 0 else "right only"), st
        return "both", st
    if task == "out_of_phase":
        m = issue(a, r"out of phase")
        return ("yes" if m else "no"), {"issue": bool(m), "correlation": a["stereo"]["correlation"]}
    if task == "tone_or_noise":
        ch = a["spectrum"]["character"]
        return ("noise" if ch == "noise-like" else "tone"), {"character": ch}
    if task == "noise_colour":
        # audio-mcp has no noise-colour field; infer it from the band energy split (white: mostly 'brilliance',
        # brown: mostly 'sub' + 'bass', pink: spread across bands).
        be = a["spectrum"]["band_energy_percent"]
        colour = "white" if be["brilliance"] > 40 else "brown" if be["sub"] + be["bass"] > 70 else "pink"
        return colour, be
    if task == "chord_or_single":
        poly = a["pitch"].get("polyphony_likely", False)
        return ("chord" if poly else "single note"), {"polyphony_likely": poly}
    if task == "transcription":
        mel = await t("audio_melody", files[0])
        return [n["note"] for n in mel["notes"]], {"as_text": mel["as_text"]}
    raise ValueError(f"no rule for task {task}")


async def run(items):
    files = sorted({f for it in items for f in it["audio"]})
    tmp = Path(tempfile.mkdtemp(prefix="perception-blind-"))
    blind = {}
    for n, rel in enumerate(files, 1):
        blind[rel] = str(tmp / f"{n:03d}.wav")
        shutil.copyfile(ROOT / rel, blind[rel])
    server = StdioServerParameters(command=sys.executable, args=["-m", "audio_mcp"])
    preds, trace = [], []
    try:
        async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            tools = Tools(session, blind)
            for it in items:
                ans, evidence = await answer(it, tools)
                preds.append({"id": it["id"], "answer": ans})
                trace.append({"id": it["id"], "answer": ans, "expected": it["answer"], "evidence": evidence})
            print(f"{len(items)} items, {tools.calls} MCP tool calls on {len(files)} files")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return preds, trace


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "results" / "audio_mcp_tools.jsonl"))
    args = ap.parse_args()
    preds, trace = asyncio.run(run(load_items()))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(p) + "\n" for p in preds), encoding="utf-8")
    out.with_name(out.stem + "_trace.jsonl").write_text(
        "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in trace), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
