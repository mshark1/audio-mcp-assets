"""Check melodic sounds in a pack against famous jingles and sound trademarks, by note sequence.

Usage: python tools/similarity_check.py <pack_dir> [--include-removed]

What it compares: the note sequence of every melodic recipe layer (from recipes.json), transposition-invariantly,
against a reference list of well-known game sounds, jingles and sound marks. Melodies are what make these sounds
recognizable, so this catches the most likely problem. Limits, stated plainly:
  * The reference list is written FROM MEMORY by the AI that built the pack; pitches are approximate, and the list
    covers only famous sounds it knows of. Passing this check does not prove a sound is unlike every existing
    sound; it catches the obvious cases. Please report any resemblance you hear.
  * Non-melodic sounds (sweeps, noise, single strikes) aren't compared; they're built from generic synthesis
    idioms (rising sweep, noise burst, bell strike) rather than specific melodies.

A match is flagged when it covers either (a) at least 4 notes with exactly the same interval shape (in any key),
or (b) the WHOLE of a short reference (2-3 notes, e.g. a two-note coin sound or a three-note sound mark) with the
same intervals at nearly the same pitches (within 2 semitones). Shorter partial overlaps, such as a 3-note major
triad that also occurs inside a longer tune, are too generic to mean anything, and repeated notes aren't melody.
"""

import json
import sys
from pathlib import Path

NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
        "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def midi(name):
    pitch, octave = (name[:2], name[2:]) if name[1:2] in ("#", "b") else (name[:1], name[1:])
    return NOTE[pitch] + 12 * (int(octave) + 1)


# Approximate, from memory. (name, notes)
REFERENCES = [
    ("Super Mario Bros. coin", ["B5", "E6"]),
    ("Super Mario Bros. 1-up", ["E6", "G6", "E7", "C7", "D7", "G7"]),
    ("Super Mario Bros. death (opening)", ["B4", "F5", "F5", "F5", "E5", "D5", "C5"]),
    ("The Legend of Zelda 'secret found'", ["G6", "F#6", "D#6", "A5", "G#5", "E6", "G#6", "C7"]),
    ("Final Fantasy victory fanfare (opening)", ["C5", "C5", "C5", "C5", "Ab4", "Bb4", "C5", "Bb4", "C5"]),
    ("Tetris / Korobeiniki (opening)", ["E5", "B4", "C5", "D5", "C5", "B4", "A4"]),
    ("NBC chimes (sound trademark)", ["G4", "E5", "C5"]),
    ("Intel bong (sound trademark)", ["Db5", "Db5", "Gb5", "Db5", "Ab5"]),
    ("Nokia tune (opening)", ["E6", "D6", "F#5", "G#5", "C#6", "B5", "D5", "E5"]),
    ("'Sad trombone' (trope)", ["Bb3", "A3", "Ab3", "G3"]),
    ("'Charge!' bugle call (trope)", ["G4", "C5", "E5", "G5", "E5", "G5"]),
    ("'Shave and a haircut' (trope)", ["C5", "G4", "G4", "A4", "G4", "B4", "C5"]),
    ("Windows-style rising notification (generic shape)", ["E5", "G#5", "B5"]),
]


# Matches a person has reviewed and judged acceptable, each with its reason. The check fails only on unreviewed
# matches. Add an entry only after listening, and say why in plain words.
REVIEWED = {
    ("game_powerup.wav", "'Charge!' bugle call (trope)"): (
        "Any major arpeggio rising past an octave contains G-C-E-G. 'Charge!' is recognized by its rhythm "
        "(short-short-short-long, then a pause); this is an even 45 ms run up two octaves. The call is a "
        "public-domain military bugle call, not anyone's signature sound. Reviewed by ear 2026-10-13."
    ),
}


def intervals(notes):
    m = [midi(n) for n in notes]
    return [b - a for a, b in zip(m, m[1:])], m


def windows(seq, w):
    return [tuple(seq[i : i + w]) for i in range(len(seq) - w + 1)]


def melodic_layers(recipe):
    synth = next(s for s in recipe["steps"] if s.get("tool") == "audio_synthesize")
    for layer in synth["args"]["spec"]["layers"]:
        seq = [n for n, _ in layer.get("sequence", []) if n not in ("rest", "r", "-", "x")]
        if len(seq) >= 2:
            yield seq


def check(notes):
    ivs, m = intervals(notes)
    hits = []
    for ref_name, ref_notes in REFERENCES:
        rivs, rm = intervals(ref_notes)
        # (a) 4+ notes (3+ intervals) with exactly the same shape, ignoring pure repeated-note runs
        shape = {w for w in windows(rivs, 3) if any(w)}
        if any(w in shape for w in windows(ivs, 3)):
            hits.append(ref_name)
            continue
        # (b) the entire short reference, same intervals, nearly the same pitches
        if len(ref_notes) <= 3:
            k = len(rivs)
            for i in range(len(ivs) - k + 1):
                if ivs[i : i + k] == rivs and all(abs(m[i + j] - rm[j]) <= 2 for j in range(k + 1)):
                    hits.append(ref_name)
                    break
    return hits


def main(pack: Path, extra=()):
    recipes = json.loads((pack / "recipes.json").read_text(encoding="utf-8"))["assets"]
    flagged = 0
    checked = 0
    cases = [(r["file"], seq) for r in recipes for seq in melodic_layers(r)] + list(extra)
    for name, seq in cases:
        checked += 1
        hits = check(seq)
        open_hits = [h for h in hits if (name, h) not in REVIEWED]
        flagged += bool(open_hits)
        status = "FLAG" if open_hits else ("rev " if hits else "ok  ")
        print(f"{status} {name:28s} {' '.join(seq):40s} {'~ ' + ', '.join(hits) if hits else ''}")
        for h in hits:
            if (name, h) in REVIEWED:
                print(f"       reviewed: {REVIEWED[(name, h)]}")
    print(f"\n{checked} melodic layers checked against {len(REFERENCES)} references; {flagged} unreviewed matches")
    return flagged


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pack = Path(sys.argv[1])
    extra = []
    if "--include-removed" in sys.argv:  # sanity check: the designs that were withdrawn must be caught
        extra = [("REMOVED old game_coin", ["B5", "E6"]), ("REMOVED old game_over", ["G4", "F#4", "F4", "E4"])]
    sys.exit(1 if main(pack, extra) and "--include-removed" not in sys.argv else 0)
