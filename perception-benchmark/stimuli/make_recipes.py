"""Generate recipes.json for the perception benchmark's extra stimuli.

These fill gaps the reference-signals pack can't cover on its own: many pitches for note-naming statistics, pairs for
"which is higher / louder" comparisons (including deliberate traps), and negative or distractor variants for the
defect questions. Every stimulus is an audio-mcp recipe with checks, built and verified by tools/build.py exactly like
the other packs, and re-checked without audio-mcp by perception-benchmark/validate.py.

File names are deliberately opaque (stim_001.wav, ...) so a model or agent can't read the answer from the name.
The order of STIMULI fixes the numbering; append new stimuli at the end.

    python perception-benchmark/stimuli/make_recipes.py
    python tools/build.py perception-benchmark/stimuli
"""

import json
from pathlib import Path

SR = 48000
NOTE_OFFSETS = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}


def note_hz(name):
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE_OFFSETS[pitch] + 12 * (octave - 4)) / 12)


def synth(spec, out="{out}"):
    return {"tool": "audio_synthesize", "args": {"spec": {"sample_rate": SR, **spec}, "output": out, "overwrite": True}}


def process(src, ops, out="{out}"):
    return {"tool": "audio_process", "args": {"path": src, "operations": ops, "output": out, "overwrite": True}}


def check(field, tool="audio_analyze", **kw):
    return {"tool": tool, "field": field, **kw}


def clicks(times, total):
    """A noise-click sequence (4 ms clicks, like the reference pack's rhythm file) with clicks starting at `times`."""
    seq, t = [], 0.0
    for start in times:
        if start > t + 1e-9:
            seq.append(["rest", round(start - t, 6)])
        seq.append(["x", 0.004])
        t = start + 0.004
    return synth({"seed": 6, "duration": total, "layers": [{"wave": "noise", "highpass": 1000,
                  "envelope": {"attack": 0.0005, "decay": 0.0, "sustain": 1, "release": 0.003}, "sequence": seq}]})


STIMULI = []  # (key, description, ground_truth, steps, checks)


def add(key, description, ground_truth, steps, checks):
    STIMULI.append((key, description, ground_truth, steps, checks))


# ---- Pitch: 24 steady tones on four waveforms, E2..C7 -------------------------------------------------------------
TONES = [
    ("E2", "triangle"), ("G#2", "sine"), ("C3", "saw"), ("D#3", "sine"), ("F3", "square"), ("A3", "triangle"),
    ("B3", "saw"), ("C#4", "sine"), ("D4", "square"), ("F#4", "triangle"), ("G4", "saw"), ("A#4", "sine"),
    ("C5", "triangle"), ("D#5", "square"), ("E5", "sine"), ("G5", "saw"), ("A5", "triangle"), ("B5", "sine"),
    ("C#6", "square"), ("D6", "triangle"), ("F6", "sine"), ("G#6", "saw"), ("A6", "sine"), ("C7", "sine"),
]
for note, wave in TONES:
    add(f"tone_{note}_{wave}", f"Steady {note} ({note_hz(note):.2f} Hz) {wave} wave, -6 dBFS peak, 0.8 s.",
        {"note": note, "frequency_hz": round(note_hz(note), 2), "wave": wave, "peak_dbfs": -6.0, "duration_s": 0.8},
        [synth({"normalize_peak_db": -6, "layers": [{"wave": wave, "freq": note, "duration": 0.8,
                                                      "envelope": {"attack": 0.01, "release": 0.05}}]})],
        [check("pitch.median.note", expect=note), check("levels.peak_dbfs", expect=-6.0, tol=0.01)])

# Off-grid frequencies (frequency estimation, not note naming) and two near-A4 tones for fine comparisons.
for hz, wave in [(150, "sine"), (300, "triangle"), (777, "sine"), (1234, "square"), (434, "sine"), (446, "sine")]:
    add(f"freq_{hz}_{wave}", f"Steady {hz} Hz {wave} wave (not on the equal-tempered grid), -6 dBFS peak, 0.8 s.",
        {"frequency_hz": hz, "wave": wave, "duration_s": 0.8},
        [synth({"normalize_peak_db": -6, "layers": [{"wave": wave, "freq": hz, "duration": 0.8,
                                                      "envelope": {"attack": 0.01, "release": 0.05}}]})],
        [check("pitch.median.hz", expect=hz, tol=hz * 0.005)])

# ---- Loudness: pink noise at known integrated loudness ------------------------------------------------------------
for lufs in (-15, -18, -21, -26, -30, -35):
    add(f"pink_{lufs}LUFS", f"Pink noise normalized to {lufs} LUFS integrated, 2 s.",
        {"type": "pink", "lufs_integrated": float(lufs)},
        [synth({"seed": 100 - lufs, "layers": [{"wave": "pink", "duration": 2}]}, "{tmp}/pink.wav"),
         process("{tmp}/pink.wav", [{"op": "normalize_lufs", "lufs": lufs}])],
        [check("levels.lufs_integrated", expect=float(lufs), tol=0.05)])

# Peak/loudness traps: high peak but low loudness, or the reverse.
add("trap_sparse_clicks", "Six short noise clicks, one every 0.5 s, peak -1 dBFS: a high peak but little energy.",
    {"peak_dbfs": -1.0, "lufs_integrated_max": -24.0},
    [clicks([0.25 + 0.5 * i for i in range(6)], 3.0)],
    [check("levels.peak_dbfs", expect=-1.0, tol=0.01), check("levels.lufs_integrated", max=-24.0)])
add("trap_quiet_with_click", "Very quiet pink noise with one near-full-scale click at 1.0 s.",
    {"peak_dbfs_min": -1.5, "lufs_integrated_max": -35.0},
    [synth({"seed": 21, "normalize_peak_db": None, "layers": [
        {"wave": "pink", "duration": 3, "gain_db": -30},
        {"wave": "impulse", "start": 1.0, "duration": 0.001, "gain_db": -1}]})],
    [check("levels.peak_dbfs", min=-1.5), check("levels.lufs_integrated", max=-35.0)])
add("trap_dense_sine", "Steady 1 kHz sine at only -12 dBFS peak: a low peak but continuous energy.",
    {"frequency_hz": 1000, "peak_dbfs": -12.0, "rms_dbfs": -15.01},
    [synth({"normalize_peak_db": -12, "layers": [{"wave": "sine", "freq": 1000, "duration": 3}]})],
    [check("levels.peak_dbfs", expect=-12.0, tol=0.01), check("levels.rms_dbfs", expect=-15.01, tol=0.02)])

# ---- Noise colours and RMS levels -----------------------------------------------------------------------------------
for key, wave, rms, seed in [("white_-30rms", "noise", -30, 31), ("pink_-16rms", "pink", -16, 32), ("brown_-20rms", "brown", -20, 33)]:
    colour = {"noise": "white", "pink": "pink", "brown": "brown"}[wave]
    add(key, f"{colour.capitalize()} noise at {rms} dBFS RMS, 2 s.", {"type": colour, "rms_dbfs": float(rms)},
        [synth({"seed": seed, "layers": [{"wave": wave, "duration": 2}]}, "{tmp}/n.wav"),
         process("{tmp}/n.wav", [{"op": "normalize_rms", "db": rms}])],
        [check("levels.rms_dbfs", expect=float(rms), tol=0.05), check("levels.clipped_samples", expect=0),
         check("spectrum.character", expect="noise-like")])

# ---- Defects ---------------------------------------------------------------------------------------------------------
add("clip_mild_sine", "PROBLEM: 330 Hz sine driven 2 dB past full scale (mild hard clipping), 2 s.",
    {"clipped": True},
    [synth({"normalize_peak_db": 2, "layers": [{"wave": "sine", "freq": 330, "duration": 2}]})],
    [check("levels.clipped_samples", min=1000)])
add("clip_pink", "PROBLEM: pink noise driven 3 dB past full scale, so its loudest peaks are clipped, 2 s.",
    {"clipped": True},
    [synth({"seed": 41, "normalize_peak_db": 3, "layers": [{"wave": "pink", "duration": 2}]})],
    [check("levels.clipped_samples", min=10)])
add("dc_on_noise", "PROBLEM: pink noise riding on a constant DC offset of +0.05, 2 s.",
    {"dc_offset": 0.05},
    [synth({"seed": 42, "normalize_peak_db": None, "layers": [
        {"wave": "pink", "duration": 2, "gain_db": -12}, {"wave": "dc", "duration": 2, "gain_db": -26.0206}]})],
    [check("levels.dc_offset", expect=0.05, tol=0.002)])
add("hum_50Hz", "PROBLEM: gated D5 tone over 50 Hz mains hum (with a 100 Hz harmonic) and faint hiss, 4 s.",
    {"hum_hz": 50, "hum_harmonics_hz": [100]},
    [synth({"seed": 43, "layers": [
        {"wave": "sine", "sequence": [["D5", 0.5], ["rest", 0.5]] * 4},
        {"wave": "sine", "freq": 50, "duration": 4, "gain_db": -18},
        {"wave": "sine", "freq": 100, "duration": 4, "gain_db": -26},
        {"wave": "pink", "duration": 4, "gain_db": -36}]})],
    [check("issues", contains="Mains hum at 50 Hz")])
add("hum_60Hz_under_noise", "PROBLEM: 60 Hz hum (with a 120 Hz harmonic) under a bed of pink noise, 3 s.",
    {"hum_hz": 60, "hum_harmonics_hz": [120]},
    [synth({"seed": 44, "layers": [
        {"wave": "pink", "duration": 3},
        {"wave": "sine", "freq": 60, "duration": 3, "gain_db": -16},
        {"wave": "sine", "freq": 120, "duration": 3, "gain_db": -24}]})],
    [check("levels.clipped_samples", expect=0)])
add("abrupt_sine", "PROBLEM: 500 Hz sine that starts at its peak (90 degrees phase) with no fade-in: a click at t=0. 1 s.",
    {"abrupt_start": True},
    [synth({"layers": [{"wave": "sine", "freq": 500, "phase": 90, "duration": 1,
                        "envelope": {"attack": 0, "release": 0.05}}]})],
    [check("edges.start_amplitude", min=0.5)])
add("faded_burst", "Noise burst like problem_abrupt_start.wav but with a 20 ms fade-in, so it does not click. 1 s.",
    {"abrupt_start": False},
    [synth({"seed": 9, "layers": [{"wave": "noise", "duration": 1, "envelope": {"attack": 0.02, "release": 0.2}}]})],
    [check("edges.start_amplitude", max=0.01)])
add("loop_clean_200Hz", "200 Hz sine, exactly 200 whole periods (1.0 s), no fades: loops without a seam.",
    {"loop_click": False, "periods": 200},
    [synth({"layers": [{"wave": "sine", "freq": 200, "duration": 1.0, "envelope": {"attack": 0, "release": 0}}]})],
    [check("edges.loop_seam.likely_click", expect=False)])
add("loop_cut_200Hz", "PROBLEM: 200 Hz sine cut after 200.25 periods (1.00125 s): the loop seam jumps from +1 to 0.",
    {"loop_click": True, "periods": 200.25},
    [synth({"layers": [{"wave": "sine", "freq": 200, "duration": 1.00125, "envelope": {"attack": 0, "release": 0}}]})],
    [check("edges.loop_seam.likely_click", expect=True)])

# ---- Time --------------------------------------------------------------------------------------------------------------
add("padded_tone", "600 Hz tone of 0.8 s with 0.5 s of silence before it and 0.25 s after it (1.55 s total).",
    {"leading_silence_s": 0.5, "trailing_silence_s": 0.25, "duration_s": 1.55},
    [synth({"layers": [{"wave": "sine", "freq": 600, "duration": 0.8}]}, "{tmp}/pt.wav"),
     process("{tmp}/pt.wav", [{"op": "pad", "start": 0.5, "end": 0.25}])],
    [check("silence.leading_s", expect=0.5, tol=0.02), check("silence.trailing_s", expect=0.25, tol=0.03)])
for key, times, total in [("clicks_3", [0.2, 0.9, 1.3], 2.0), ("clicks_5", [0.1, 0.45, 1.0, 1.3, 2.05], 2.5),
                          ("clicks_7", [0.1, 0.4, 0.6, 1.1, 1.5, 1.8, 2.4], 3.0)]:
    add(key, f"{len(times)} short clicks at irregular times ({', '.join(f'{t:g}' for t in times)} s).",
        {"onsets": len(times), "onset_times_s": times},
        [clicks(times, total)],
        [check("event_count", tool="audio_events", expect=len(times))])
for bpm in (90, 100, 150):
    period = 60 / bpm
    times = [round(i * period, 6) for i in range(8)]
    add(f"tempo_{bpm}", f"8 short clicks at exactly {bpm} BPM (one every {period:.4g} s, first at t=0).",
        {"bpm": bpm, "onsets": 8, "interval_s": round(period, 6)},
        [clicks(times, round(8 * period, 6))],
        # audio-mcp 0.2.0 reports no tempo_bpm for the 150 BPM file (3.2 s), though it finds all 8 onsets, so the
        # build pins the onsets; the tempo itself is checked independently in validate.py.
        [check("rhythm.onset_count", expect=8)] + ([check("rhythm.tempo_bpm", expect=bpm, tol=2)] if bpm != 150 else []))
for key, at, total in [("impulse_0.25s", 0.25, 1.0), ("impulse_1.2s", 1.2, 2.0)]:
    add(key, f"One full-scale sample at exactly {at} s in {total:g} s of silence.",
        {"impulse_time_s": at, "impulse_sample_index": int(round(at * SR))},
        [synth({"duration": total, "normalize_peak_db": None, "layers": [
            {"wave": "silence", "duration": total}, {"wave": "impulse", "start": at, "duration": 0.001}]})],
        [check("event_count", tool="audio_events", expect=1)])

# ---- Stereo ------------------------------------------------------------------------------------------------------------
add("stereo_right_only", "440 Hz tone in the right channel only; left channel silent. 3 s.",
    {"left": "silence", "right": "440 Hz tone"},
    [synth({"layers": [{"wave": "sine", "freq": 440, "duration": 3, "pan": 1}]})],
    [check("stereo.width", expect="one channel silent")])
add("stereo_pink_out_of_phase", "Pink noise with the right channel polarity-inverted (correlation -1). 3 s.",
    {"correlation": -1.0},
    [synth({"seed": 51, "stereo": True, "layers": [{"wave": "pink", "duration": 3}]}, "{tmp}/sp.wav"),
     process("{tmp}/sp.wav", [{"op": "polarity", "channel": 1}])],
    [check("stereo.correlation", expect=-1.0, tol=0.001)])
add("stereo_pink_identical", "The same pink noise in both channels (correlation +1, a mono signal in stereo). 3 s.",
    {"correlation": 1.0, "channels": "identical"},
    [synth({"seed": 52, "stereo": True, "layers": [{"wave": "pink", "duration": 3}]})],
    [check("stereo.correlation", expect=1.0, tol=0.001)])

# ---- Chords and melodies ---------------------------------------------------------------------------------------------
add("chord_Cmajor_sines", "C major triad (C4 E4 G4) of equal-level sines, 2 s.",
    {"notes": ["C4", "E4", "G4"], "polyphonic": True},
    [synth({"layers": [{"wave": "sine", "freq": n, "duration": 2} for n in ("C4", "E4", "G4")]})],
    [check("spectrum.spectral_peaks", expect=["C4", "E4", "G4"], pluck="note")])
add("chord_Aminor_triangles", "A minor triad (A3 C4 E4) on triangle waves, 2 s.",
    {"notes": ["A3", "C4", "E4"], "polyphonic": True},
    [synth({"layers": [{"wave": "triangle", "freq": n, "duration": 2} for n in ("A3", "C4", "E4")]})],
    [check("levels.clipped_samples", expect=0)])
MELODIES = [
    ("melody_twinkle", "'Twinkle, Twinkle, Little Star' opening (traditional, public domain), triangle wave, 0.4 s per note.",
     ["C4", "C4", "G4", "G4", "A4", "A4", "G4"], "triangle", 0.4),
    ("melody_frere_jacques", "'Frere Jacques' opening (traditional, public domain), sine wave, 0.35 s per note.",
     ["C4", "D4", "E4", "C4", "C4", "D4", "E4", "C4"], "sine", 0.35),
    ("melody_wholetone_down", "Descending whole-tone scale A4 to B3 (an exercise, not a tune), square wave, 0.3 s per note.",
     ["A4", "G4", "F4", "D#4", "C#4", "B3"], "square", 0.3),
]
for key, desc, notes, wave, dur in MELODIES:
    add(key, desc, {"notes": notes, "note_duration_s": dur},
        [synth({"layers": [{"wave": wave, "sequence": [[n, dur] for n in notes],
                            "envelope": {"attack": 0.005, "release": 0.03}}]})],
        # audio_events, not audio_melody: in audio-mcp 0.2.0 audio_melody merges the repeated C4 C4 of the sine
        # melody into one long note, while audio_events keeps them apart.
        [check("pitched_sequence", tool="audio_events", expect=" ".join(notes))])


def file_of(key):
    for i, s in enumerate(STIMULI, 1):
        if s[0] == key:
            return f"stim_{i:03d}.wav"
    raise KeyError(key)


def main():
    assets = []
    for i, (key, description, gt, steps, checks) in enumerate(STIMULI, 1):
        assets.append({"file": f"stim_{i:03d}.wav", "key": key, "description": description,
                       "ground_truth": gt, "steps": steps, "checks": checks})
    pack = {"name": "audio-mcp perception benchmark stimuli", "version": "1.0.0",
            "description": "Extra stimuli for the perception benchmark: tones, comparison pairs, traps and distractors, "
                           "each synthesized with audio-mcp from a recipe and verified.",
            "made_with": "https://github.com/mshark1/audio-mcp"}
    out = Path(__file__).with_name("recipes.json")
    out.write_text(json.dumps({"pack": pack, "assets": assets}, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(assets)} stimuli)")


if __name__ == "__main__":
    main()
