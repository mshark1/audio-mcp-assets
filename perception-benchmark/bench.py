"""Shared helpers for the perception benchmark: loading items, parsing free-form answers, grading and chance.

Answer types (see README.md for the full item format):
  choice         one of item["options"]; graded by exact match after normalization
  numeric        a number in item["unit"]; correct if within item["tolerance"] ({"abs": x} or {"rel": r})
  note           a note name in scientific pitch notation (A4 = 440 Hz); correct if it is the same MIDI note
  note_sequence  a list of note names; scored per note (position-exact), partial credit in [0, 1]

No third-party imports, so score.py and the CI smoke test only need the standard library.
"""

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repository root; item audio paths are relative to it
HERE = Path(__file__).resolve().parent
ITEMS = HERE / "items.jsonl"

PITCH_CLASS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_RE = re.compile(r"^([A-Ga-g])\s*(#|b|♯|♭|sharp|flat|-sharp|-flat)?\s*(-?\d)$")


def load_items(path=ITEMS):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


# ---- notes ---------------------------------------------------------------------------------------------------------

def note_to_midi(name):
    """'A4' -> 69. Accepts sharps/flats as #, b, ♯, ♭ (so Db4 == C#4), any case. Returns None if not a note."""
    if not isinstance(name, str):
        return None
    m = NOTE_RE.match(name.strip().replace(" ", ""))
    if not m:
        return None
    letter, acc, octave = m.group(1).upper(), (m.group(2) or "").lower(), int(m.group(3))
    shift = 1 if acc in ("#", "♯", "sharp", "-sharp") else -1 if acc in ("b", "♭", "flat", "-flat") else 0
    return PITCH_CLASS[letter] + shift + 12 * (octave + 1)


def midi_to_note(m):
    return f"{SHARP_NAMES[m % 12]}{m // 12 - 1}"


def midi_to_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def hz_to_midi(hz):
    return int(round(69 + 12 * math.log2(hz / 440.0)))


def note_range(lo, hi):
    return list(range(note_to_midi(lo), note_to_midi(hi) + 1))


# ---- parsing -------------------------------------------------------------------------------------------------------

NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _clean(text):
    return str(text).strip().replace("−", "-").replace("–", "-")


def parse_number(pred, unit=None):
    """First number in the answer, converted to the item's unit where the answer names another one.

    '440 Hz', '440', '0.44 kHz' -> 440 (Hz); '1500 ms' -> 1.5 (s); '-23 LUFS', '-23 LU', '−23' -> -23;
    for unit Hz a note name ('A4') is accepted and converted to its equal-tempered frequency."""
    if isinstance(pred, bool):
        return None
    if isinstance(pred, (int, float)):
        return float(pred)
    text = _clean(pred)
    if unit == "Hz":
        m = note_to_midi(text)
        if m is not None:
            return midi_to_hz(m)
    found = NUM_RE.search(text.replace(",", ""))
    if not found:
        return None
    value = float(found.group())
    low = text.lower()
    if unit == "Hz" and "khz" in low:
        value *= 1000
    if unit == "s" and re.search(r"\d\s*ms\b", low):
        value /= 1000
    return value


def parse_note(pred):
    """A note name, or a frequency ('261.6 Hz', 261.6) which is mapped to the nearest equal-tempered note."""
    if isinstance(pred, (int, float)) and not isinstance(pred, bool):
        return hz_to_midi(float(pred)) if pred > 0 else None
    text = _clean(pred)
    m = note_to_midi(text)
    if m is None:
        token = re.search(r"[A-Ga-g](?:#|b|♯|♭)?-?\d", text)
        m = note_to_midi(token.group()) if token else None
    if m is None and re.search(r"hz", text.lower()):
        hz = parse_number(text)
        m = hz_to_midi(hz) if hz and hz > 0 else None
    return m


def parse_sequence(pred):
    """A list of notes, or a string separated by spaces, commas, dashes or arrows."""
    if isinstance(pred, str):
        pred = [t for t in re.split(r"[\s,;|>→]+|(?<=\d)-(?=[A-Ga-g])", _clean(pred)) if t]
    if not isinstance(pred, list):
        return []
    return [parse_note(p) for p in pred]


def _norm(text):
    return re.sub(r"[\s_.\-:'\"()]", "", _clean(text).lower())


YES = {"yes", "y", "true", "present", "1"}
NO = {"no", "n", "false", "absent", "none", "0"}
FIRST = {"a", "first", "1", "1st", "filea", "clipa", "the first"}
SECOND = {"b", "second", "2", "2nd", "fileb", "clipb", "the second"}


def parse_choice(pred, options):
    """Return the matching option (or None). Case, spaces, punctuation and units are ignored; yes/no accept
    true/false; A/B pairs accept first/second; otherwise a single letter picks options by position (a, b, c...);
    a bare number matches an option containing that number ('50' -> '50 Hz')."""
    if pred is None:
        return None
    if isinstance(pred, bool):
        pred = "yes" if pred else "no"
    raw = _clean(pred)
    p = _norm(raw)
    norm_opts = {_norm(o): o for o in options}
    if p in norm_opts:
        return norm_opts[p]
    low = raw.lower().strip(" .!")
    if set(norm_opts) == {"yes", "no"}:
        if low in YES or p in YES:
            return "yes"
        if low in NO or p in NO:
            return "no"
    if set(norm_opts) == {"a", "b"}:
        if low in FIRST or p in FIRST:
            return norm_opts["a"]
        if low in SECOND or p in SECOND:
            return norm_opts["b"]
    if len(p) == 1 and p.isalpha() and ord(p) - 97 < len(options):
        return options[ord(p) - 97]
    num = NUM_RE.fullmatch(p.replace("hz", ""))
    if num:
        hits = [o for o in options if re.search(rf"(?<![\d.]){re.escape(num.group())}(?![\d.])", o)]
        if len(hits) == 1:
            return hits[0]
    starts = [o for o in options if p and _norm(o).startswith(p)]
    return starts[0] if len(starts) == 1 else None


# ---- grading -------------------------------------------------------------------------------------------------------

def tolerance(item):
    tol = item["tolerance"]
    return tol.get("abs", 0.0) + tol.get("rel", 0.0) * abs(item["answer"])


def grade(item, pred):
    """Score in [0, 1] for one prediction (None = missing)."""
    if pred is None:
        return 0.0
    kind = item["answer_type"]
    if kind == "choice":
        return float(parse_choice(pred, item["options"]) == item["answer"])
    if kind == "numeric":
        value = parse_number(pred, item.get("unit"))
        return float(value is not None and abs(value - item["answer"]) <= tolerance(item) + 1e-9)
    if kind == "note":
        return float(parse_note(pred) == note_to_midi(item["answer"]))
    if kind == "note_sequence":
        truth = [note_to_midi(n) for n in item["answer"]]
        got = parse_sequence(pred)
        hits = sum(1 for t, g in zip(truth, got) if g == t)
        return hits / max(len(truth), len(got))
    raise ValueError(f"unknown answer_type {kind!r}")


def chance(item):
    """Expected score of a uniform random guess over the answer space stated in the question.

    choice: 1/len(options). note / note_sequence: 1/(number of notes in item['range']) per note.
    numeric: probability that a uniform guess in item['range'] lands within the tolerance."""
    kind = item["answer_type"]
    if kind == "choice":
        return 1 / len(item["options"])
    if kind in ("note", "note_sequence"):
        return 1 / len(note_range(*item["range"]))
    lo, hi = item["range"]
    if item.get("integer"):
        tol = tolerance(item)
        return len([v for v in range(math.ceil(lo), math.floor(hi) + 1) if abs(v - item["answer"]) <= tol]) / (
            math.floor(hi) - math.ceil(lo) + 1)
    tol = tolerance(item)
    a, b = max(lo, item["answer"] - tol), min(hi, item["answer"] + tol)
    return max(0.0, b - a) / (hi - lo)
