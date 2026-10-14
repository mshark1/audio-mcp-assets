"""Validate items.jsonl: schema, audio files, provenance links, and an independent re-measurement of each answer.

Three layers, all without audio-mcp (numpy, scipy, soundfile and pyloudnorm only):
  1. schema: required fields, valid answer types, options/tolerance/range present and consistent, unique ids;
  2. provenance: every linked manifest field still holds the recorded value, and the answer follows from it by the
     item's stated derivation (equal, yesno, higher, sign, nearest_note, ...);
  3. independent check: the property is re-measured from the samples with simple, separate implementations
     (FFT peak, pyloudnorm, sample counts, correlation...). Items with no cheap independent measure (melodies,
     chords, mains-hum negatives) rely on their recipe and manifest checks and are reported as such.

Usage: python perception-benchmark/validate.py   (exit status 1 on any failure)
"""

import json
import sys
from pathlib import Path

import numpy as np
import pyloudnorm
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench import ROOT, hz_to_midi, load_items, note_to_midi, parse_choice  # noqa: E402

TYPES = {"choice", "numeric", "note", "note_sequence"}
_cache = {}


def audio(rel):
    if rel not in _cache:
        x, sr = sf.read(str(ROOT / rel), always_2d=True)
        _cache[rel] = (x, sr)
    return _cache[rel]


def db(v):
    return 20 * np.log10(max(v, 1e-12))


def dominant_hz(x, sr):
    mono = x.mean(axis=1)
    n = 1 << 21
    spec = np.abs(np.fft.rfft(mono * np.hanning(len(mono)), n))
    return np.fft.rfftfreq(n, 1 / sr)[np.argmax(spec)]


def lufs(x, sr):
    return pyloudnorm.Meter(sr).integrated_loudness(x)


def click_starts(x, sr):
    a = np.abs(x).max(axis=1)
    idx = np.flatnonzero(a > 0.05 * a.max())
    return idx[np.concatenate(([True], np.diff(idx) > sr // 20))] / sr


def hum_level_db(x, sr, hz):
    """(peak at hz above the median of its +/-15 Hz neighbourhood, peak relative to total power), both in dB."""
    f, p = signal.welch(x.mean(axis=1), sr, nperseg=sr)  # 1 Hz bins
    i = int(round(hz))
    near = np.r_[p[i - 15:i - 2], p[i + 3:i + 16]]
    peak = p[i - 1:i + 2].max()
    return 10 * np.log10(peak / max(np.median(near), 1e-30)), 10 * np.log10(peak / p.sum())


def frame_flatness(x, sr):
    """Median spectral flatness of 2048-sample frames after removing each frame's overall spectral slope, so
    coloured (pink, brown) noise scores like white noise (~0.5) and any tone or sweep scores near 0."""
    f, t, s = signal.stft(x.mean(axis=1), sr, nperseg=2048)
    band = (f >= 50) & (f <= 16000)
    p = np.abs(s[band]) ** 2 + 1e-20
    loud = p.sum(axis=0) > 1e-6 * p.sum(axis=0).max()
    lp, lf = np.log(p[:, loud]), np.log2(f[band])
    coef = np.polyfit(lf, lp, 1)
    r = np.exp(lp - (np.outer(lf, coef[0]) + coef[1]))
    flat = np.exp(np.mean(np.log(r), axis=0)) / np.mean(r, axis=0)
    return float(np.median(flat))


def noise_slope(x, sr):
    """Power-spectrum slope in dB/octave between 100 Hz and 10 kHz."""
    f, p = signal.welch(x.mean(axis=1), sr, nperseg=8192)
    band = (f >= 100) & (f <= 10000)
    return np.polyfit(np.log2(f[band]), 10 * np.log10(p[band]), 1)[0]


def independent(item):
    """(ok, detail) from re-measuring the samples, or None when there is no cheap independent measure."""
    task, ans = item["task"], item["answer"]
    xs = [audio(p) for p in item["audio"]]
    x, sr = xs[0]
    if task == "note_name":
        hz = dominant_hz(x, sr)
        return hz_to_midi(hz) == note_to_midi(ans), f"FFT peak {hz:.2f} Hz"
    if task == "frequency":
        hz = dominant_hz(x, sr)
        return abs(hz - ans) <= 0.002 * ans, f"FFT peak {hz:.2f} Hz"
    if task == "higher":
        fa, fb = dominant_hz(*xs[0]), dominant_hz(*xs[1])
        return ("A" if fa > fb else "B") == ans, f"{fa:.1f} vs {fb:.1f} Hz"
    if task == "lufs":
        v = lufs(x, sr)
        return abs(v - ans) <= 0.1, f"pyloudnorm {v:.2f} LUFS"
    if task == "louder":
        la, lb = lufs(*xs[0]), lufs(*xs[1])
        pa, pb = db(np.abs(xs[0][0]).max()), db(np.abs(xs[1][0]).max())
        ok = ("A" if la > lb else "B") == ans and abs(la - lb) >= 2.0
        if "trap" in item:  # a trap must really have peak and loudness pointing opposite ways
            ok = ok and (pa > pb) != (la > lb)
        return ok, f"{la:.1f} vs {lb:.1f} LUFS, peaks {pa:.1f} vs {pb:.1f} dBFS"
    if task == "rms":
        v = 10 * np.log10(np.mean(np.square(x)))
        return abs(v - ans) <= 0.05, f"RMS {v:.2f} dBFS"
    if task == "sample_peak":
        v = db(np.abs(x).max())
        return abs(v - ans) <= 0.05, f"peak {v:.2f} dBFS"
    if task in ("true_peak", "true_peak_over"):
        tp = db(np.abs(signal.resample_poly(x, 8, 1, axis=0)).max())
        sp = db(np.abs(x).max())
        if task == "true_peak":
            return abs(tp - ans) <= 0.1, f"true peak {tp:.2f} dBTP (8x)"
        return ("yes" if tp - sp >= 1 else "no") == ans, f"true peak - sample peak = {tp - sp:.2f} dB"
    if task == "clipping":
        n = int(np.count_nonzero(np.abs(x) >= 0.9999))
        return ("yes" if n > 0 else "no") == ans, f"{n} samples at full scale"
    if task == "dc_offset":
        m = float(x.mean())
        return ("yes" if abs(m) > 0.01 else "no") == ans and (abs(m) > 0.01 or abs(m) < 0.002), f"mean {m:+.4f}"
    if task == "mains_hum":
        (r50, a50), (r60, a60) = hum_level_db(x, sr, 50), hum_level_db(x, sr, 60)
        hum50, hum60 = r50 > 12 and a50 > -40, r60 > 12 and a60 > -40
        weak = (r50 < 6 or a50 < -60) and (r60 < 6 or a60 < -60)
        got = "50 Hz" if hum50 and not hum60 else "60 Hz" if hum60 and not hum50 else "none" if weak else "?"
        return got == ans, (f"50 Hz: {r50:.0f} dB above neighbours, {a50:.0f} dB of total; "
                            f"60 Hz: {r60:.0f} dB, {a60:.0f} dB")
    if task == "abrupt_start":
        first = np.abs(x[: sr // 4000]).max() / np.abs(x).max()
        return ("yes" if first > 0.2 else "no") == ans and not 0.08 < first < 0.2, f"first 0.25 ms at {first:.3f} of peak"
    if task == "loop_click":
        jump = np.abs(x[-1] - x[0]).max()
        step = np.abs(np.diff(x, axis=0)).max()
        return ("yes" if jump > 2 * step else "no") == ans, f"seam jump {jump:.3f}, largest step {step:.3f}"
    if task == "duration":
        return abs(len(x) / sr - ans) <= 0.001, f"{len(x)} samples"  # manifest durations are rounded to 1 ms
    if task in ("leading_silence", "trailing_silence"):
        idx = np.flatnonzero(np.abs(x).max(axis=1) > 0.001)
        v = idx[0] / sr if task == "leading_silence" else (len(x) - 1 - idx[-1]) / sr
        return abs(v - ans) <= 0.02, f"{v:.3f} s"
    if task == "all_silent":
        return ("yes" if not x.any() else "no") == ans, "all zero" if not x.any() else "has signal"
    if task == "onset_count":
        if item["provenance"]["derivation"] == "count_of":
            return None
        n = len(click_starts(x, sr))
        return n == ans, f"{n} clicks"
    if task == "tempo":
        starts = click_starts(x, sr)
        bpm = 60 / np.median(np.diff(starts))
        return abs(bpm - ans) <= 0.5, f"{bpm:.2f} BPM from click spacing"
    if task == "impulse_time":
        t = np.argmax(np.abs(x).max(axis=1)) / sr
        return abs(t - ans) < 1 / sr and np.count_nonzero(x) == 1, f"single sample at {t:.5f} s"
    if task == "correlation":
        c = np.corrcoef(x[:, 0], x[:, 1])[0, 1]
        got = "positive" if c > 0.3 else "negative" if c < -0.3 else "near zero"
        return got == ans, f"correlation {c:+.3f}"
    if task == "channels":
        left, right = x[:, 0].any(), x[:, 1].any()
        got = "both" if left and right else "left only" if left else "right only"
        return got == ans, got
    if task == "out_of_phase":
        c = np.corrcoef(x[:, 0], x[:, 1])[0, 1]
        return ("yes" if c < -0.9 else "no") == ans, f"correlation {c:+.3f}"
    if task == "tone_or_noise":
        fl = frame_flatness(x, sr)
        return ("noise" if fl > 0.3 else "tone") == ans and not 0.2 < fl < 0.3, f"frame flatness {fl:.3f}"
    if task == "noise_colour":
        sl = noise_slope(x, sr)
        got = "white" if abs(sl) < 1 else "pink" if abs(sl + 3) < 1 else "brown" if abs(sl + 6) < 1 else "?"
        return got == ans, f"spectral slope {sl:+.2f} dB/octave"
    return None  # chords and melodies: recipe + manifest only


def check_schema(item, seen):
    errs = []
    for key in ("id", "category", "task", "audio", "question", "answer_type", "answer", "provenance", "difficulty"):
        if key not in item:
            errs.append(f"missing {key}")
    if errs:
        return errs
    if item["id"] in seen:
        errs.append("duplicate id")
    seen.add(item["id"])
    kind = item["answer_type"]
    if kind not in TYPES:
        errs.append(f"bad answer_type {kind}")
    if item["difficulty"] not in ("easy", "medium", "hard"):
        errs.append("bad difficulty")
    if not item["audio"] or not all((ROOT / p).is_file() for p in item["audio"]):
        errs.append(f"missing audio {item['audio']}")
    if kind == "choice" and (item["answer"] not in item.get("options", []) or parse_choice(item["answer"], item["options"]) != item["answer"]):
        errs.append("answer not among options")
    if kind == "numeric":
        if not isinstance(item["answer"], (int, float)) or "tolerance" not in item or "unit" not in item or "range" not in item:
            errs.append("numeric item needs number answer, unit, tolerance, range")
        elif not item["range"][0] <= item["answer"] <= item["range"][1]:
            errs.append("answer outside stated range")
    if kind in ("note", "note_sequence"):
        notes = [item["answer"]] if kind == "note" else item["answer"]
        lo, hi = (note_to_midi(n) for n in item.get("range", ["?", "?"]))
        if None in (lo, hi) or not all(note_to_midi(n) is not None and lo <= note_to_midi(n) <= hi for n in notes):
            errs.append("note answer invalid or outside range")
    return errs


def check_provenance(item, manifests):
    prov, ans = item["provenance"], item["answer"]
    values = []
    for ln in prov["links"]:
        assets = manifests.setdefault(ln["manifest"], {a["file"]: a for a in json.loads((ROOT / ln["manifest"]).read_text(encoding="utf-8"))["assets"]})
        data = assets.get(ln["file"])
        for k in ln["field"].split("."):
            data = data[int(k)] if isinstance(data, list) else (data or {}).get(k)
        if data != ln["value"]:
            return [f"manifest {ln['file']}:{ln['field']} = {data!r}, item recorded {ln['value']!r}"]
        if not any(Path(a).name == ln["file"] and Path(a).parent.as_posix() == Path(ln["manifest"]).parent.as_posix()
                   for a in item["audio"]):
            return [f"link {ln['file']} does not match the item's audio"]
        values.append(data)
    d = prov["derivation"]
    expect = {
        "equal": lambda: values[0],
        "yesno": lambda: "yes" if values[0] else "no",
        "yesno_chord": lambda: "chord" if values[0] else "single note",
        "higher": lambda: "A" if values[0] > values[1] else "B",
        "nearest_note": lambda: note_to_midi(ans) == hz_to_midi(values[0]) and ans,
        "hum_hz": lambda: f"{values[0]} Hz",
        "count_of": lambda: len(values[0]),
        "sign": lambda: "positive" if values[0] > 0.3 else "negative" if values[0] < -0.3 else "near zero",
    }
    if d in ("construction", "louder_measured"):
        return []  # established by the recipe; re-measured by the independent check
    if d not in expect:
        return [f"unknown derivation {d}"]
    if not values:
        return [f"derivation {d} needs a link"]
    got = expect[d]()
    return [] if got == ans else [f"derivation {d} gives {got!r}, answer is {ans!r}"]


def main():
    items = load_items()
    seen, manifests, failures, indep, skipped = set(), {}, [], 0, []
    for item in items:
        errs = check_schema(item, seen)
        if not errs:
            errs = check_provenance(item, manifests)
        if not errs:
            res = independent(item)
            if res is None:
                skipped.append(item["id"])
            else:
                indep += 1
                if not res[0]:
                    errs.append(f"independent check disagrees: {res[1]} (answer {item['answer']!r})")
        for e in errs:
            failures.append(f"{item.get('id', '?')}: {e}")
    print(f"{len(items)} items, {len(items) - len({f.split(':')[0] for f in failures})} valid; "
          f"{indep} re-measured independently, {len(skipped)} rely on recipe + manifest ({', '.join(sorted({s.rsplit('.', 1)[0] for s in skipped}))})")
    for f in failures:
        print("FAIL", f)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
