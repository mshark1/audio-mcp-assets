"""Generate items.jsonl from the two verified manifests (reference-signals and perception-benchmark/stimuli).

Every answer is read from a manifest field (ground_truth, or format.duration_s) or derived from one by a stated rule,
and the item records that link as its provenance; validate.py re-checks the link and, independently of audio-mcp,
re-measures the property from the samples.

    python perception-benchmark/make_items.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "stimuli"))

from bench import hz_to_midi, midi_to_note  # noqa: E402
from make_recipes import TONES, file_of  # noqa: E402

REF_MANIFEST = "reference-signals/manifest.json"
STIM_MANIFEST = "perception-benchmark/stimuli/manifest.json"
ROOT = HERE.parent
MANIFESTS = {m: {a["file"]: a for a in json.loads((ROOT / m).read_text(encoding="utf-8"))["assets"]}
             for m in (REF_MANIFEST, STIM_MANIFEST)}

ITEMS = []
COUNTERS = {}


def ref(name):
    return (REF_MANIFEST, name)


def stim(key):
    return (STIM_MANIFEST, file_of(key))


def path(src):
    manifest, name = src
    return str(Path(manifest).parent / name).replace("\\", "/")


def dig(src, field):
    data = MANIFESTS[src[0]][src[1]]
    for k in field.split("."):
        data = data[int(k)] if isinstance(data, list) else data[k]
    return data


def link(src, field):
    return {"manifest": src[0], "file": src[1], "field": field, "value": dig(src, field)}


def add(category, task, sources, question, answer_type, answer, derivation, difficulty, links=(), note=None, **extra):
    n = COUNTERS[task] = COUNTERS.get(task, 0) + 1
    item = {"id": f"{category}.{task}.{n:02d}", "category": category, "task": task,
            "audio": [path(s) for s in sources], "question": question, "answer_type": answer_type}
    item.update({k: v for k, v in extra.items() if k in ("options", "unit", "tolerance", "range", "integer")})
    item["answer"] = answer
    item["provenance"] = {"derivation": derivation, "links": list(links)}
    if note:
        item["provenance"]["note"] = note
    item["difficulty"] = difficulty
    if "trap" in extra:
        item["trap"] = extra["trap"]
    ITEMS.append(item)


def yesno(category, task, src, question, value, field=None, difficulty="easy", note=None, trap=None):
    links = [link(src, field)] if field else []
    kw = {"trap": trap} if trap else {}
    add(category, task, [src], question, "choice", "yes" if value else "no", "yesno" if field else "construction",
        difficulty, links, note, options=["yes", "no"], **kw)


def numeric(category, task, src, question, field, unit, tol, rng, difficulty, integer=False, note=None, scale=1.0):
    value = dig(src, field)
    add(category, task, [src], question, "numeric", round(value * scale, 6), "equal", difficulty, [link(src, field)],
        note, unit=unit, tolerance=tol, range=rng, integer=integer)


PAIR_OPTIONS = ["A", "B"]
PAIR_PREAMBLE = "You hear two clips: A (first file) then B (second file). "

# ===================================== pitch =====================================
NOTE_Q = ("What musical note is this steady tone? Answer with a note name in scientific pitch notation "
          "(A4 = 440 Hz), between C2 and C7, e.g. 'F#3'.")
for note, wave in TONES:
    src = stim(f"tone_{note}_{wave}")
    octave = int(note[-1])
    diff = "easy" if wave == "sine" and 3 <= octave <= 5 else "hard" if octave in (2, 7) or wave == "saw" else "medium"
    add("pitch", "note_name", [src], NOTE_Q, "note", dig(src, "ground_truth.note"), "equal", diff,
        [link(src, "ground_truth.note")], range=["C2", "C7"])
src = ref("tone_A4_440Hz_-12dBFS.wav")
add("pitch", "note_name", [src], NOTE_Q, "note", dig(src, "ground_truth.note"), "equal", "easy",
    [link(src, "ground_truth.note")], range=["C2", "C7"])
src = ref("tone_997Hz_-20dBFS_mono.wav")
add("pitch", "note_name", [src], NOTE_Q + " If it lies between two notes, give the nearest one.", "note",
    midi_to_note(hz_to_midi(dig(src, "ground_truth.frequency_hz"))), "nearest_note", "medium",
    [link(src, "ground_truth.frequency_hz")], range=["C2", "C7"])

FREQ_Q = "What is the frequency of this steady tone, in Hz (between 50 and 2500 Hz)?"
for src, diff in [(stim("freq_150_sine"), "medium"), (stim("freq_300_triangle"), "medium"),
                  (stim("freq_777_sine"), "medium"), (stim("freq_1234_square"), "hard"),
                  (stim("freq_434_sine"), "medium"), (stim("freq_446_sine"), "medium"),
                  (ref("tone_997Hz_-20dBFS_mono.wav"), "medium"), (ref("tone_A4_440Hz_-12dBFS.wav"), "easy"),
                  (stim("tone_C3_saw"), "hard"), (stim("tone_E5_sine"), "medium"),
                  (stim("tone_D6_triangle"), "medium"), (stim("tone_G#2_sine"), "hard")]:
    numeric("pitch", "frequency", src, FREQ_Q, "ground_truth.frequency_hz", "Hz", {"rel": 0.01}, [50, 2500], diff)

HIGHER_Q = PAIR_PREAMBLE + "Which clip has the higher pitch? Answer A or B."
PAIRS = [  # (a, b, difficulty, trap)
    ("tone_C3_saw", "tone_D#3_sine", "hard", "A is a bright sawtooth, B a dull sine: brightness and pitch disagree"),
    ("tone_C#4_sine", "tone_B3_saw", "hard", "B is brighter (sawtooth) but lower"),
    ("tone_G4_saw", "tone_A#4_sine", "hard", "A is brighter (sawtooth) but lower"),
    ("tone_A5_triangle", "tone_G5_saw", "hard", "B is brighter (sawtooth) but lower"),
    ("tone_A#4_sine", "tone_C5_triangle", "medium", None),
    ("tone_E5_sine", "tone_D#5_square", "medium", None),
    ("tone_F3_square", "tone_A3_triangle", "medium", None),
    ("tone_D4_square", "tone_C#4_sine", "medium", None),
    ("tone_E2_triangle", "tone_E5_sine", "easy", None),
    ("tone_A6_sine", "tone_F6_sine", "easy", None),
    ("tone_G#2_sine", "tone_E2_triangle", "medium", None),
    ("tone_B5_sine", "tone_C#6_square", "medium", None),
]
for a, b, diff, trap in PAIRS:
    sa, sb = stim(a), stim(b)
    fa, fb = dig(sa, "ground_truth.frequency_hz"), dig(sb, "ground_truth.frequency_hz")
    kw = {"trap": trap} if trap else {}
    add("pitch", "higher", [sa, sb], HIGHER_Q, "choice", "A" if fa > fb else "B", "higher", diff,
        [link(sa, "ground_truth.frequency_hz"), link(sb, "ground_truth.frequency_hz")], options=PAIR_OPTIONS, **kw)
for a, b in [(ref("tone_A4_440Hz_-12dBFS.wav"), stim("freq_446_sine")), (stim("freq_434_sine"), ref("tone_A4_440Hz_-12dBFS.wav")),
             (stim("freq_446_sine"), stim("freq_434_sine"))]:
    fa, fb = dig(a, "ground_truth.frequency_hz"), dig(b, "ground_truth.frequency_hz")
    add("pitch", "higher", [a, b], HIGHER_Q, "choice", "A" if fa > fb else "B", "higher", "hard",
        [link(a, "ground_truth.frequency_hz"), link(b, "ground_truth.frequency_hz")], options=PAIR_OPTIONS,
        note="fine comparison: 23 to 47 cents apart")

# ===================================== loudness =====================================
LUFS_Q = "What is the integrated loudness of this file in LUFS (ITU-R BS.1770 / EBU R128), between -60 and 0?"
for src in [stim(f"pink_{v}LUFS") for v in (-15, -18, -21, -26, -30, -35)] + [
        ref("loudness_pink_-16LUFS.wav"), ref("loudness_pink_-23LUFS.wav"), ref("problem_too_quiet_-40LUFS.wav"),
        ref("tone_997Hz_-23LUFS_stereo.wav")]:
    numeric("loudness", "lufs", src, LUFS_Q, "ground_truth.lufs_integrated", "LUFS", {"abs": 1.0}, [-60, 0], "medium")

LOUDER_Q = PAIR_PREAMBLE + ("Which clip is louder, in integrated loudness (LUFS, ITU-R BS.1770), not in peak level? "
                            "Answer A or B.")
LOUDER = [  # (a, b, difficulty, trap)
    (stim("pink_-18LUFS"), stim("pink_-21LUFS"), "medium", None),
    (stim("pink_-26LUFS"), stim("pink_-15LUFS"), "easy", None),
    (stim("pink_-35LUFS"), stim("pink_-30LUFS"), "medium", None),
    (ref("loudness_pink_-16LUFS.wav"), ref("loudness_pink_-23LUFS.wav"), "easy", None),
    (stim("trap_dense_sine"), stim("pink_-18LUFS"), "medium", None),
    (stim("trap_quiet_with_click"), stim("trap_dense_sine"), "hard", "A has the higher peak (-1 vs -12 dBFS) but B is far louder"),
    (stim("pink_-21LUFS"), stim("trap_sparse_clicks"), "hard", "B has the higher peak (-1 vs -9 dBFS) but A is louder"),
    (ref("impulse_single_sample.wav"), stim("pink_-35LUFS"), "hard", "A peaks at 0 dBFS (one sample) but B is louder"),
    (stim("trap_sparse_clicks"), stim("pink_-26LUFS"), "hard", "A has the higher peak (-1 vs -14 dBFS) but B is louder"),
    (stim("pink_-30LUFS"), stim("trap_quiet_with_click"), "hard", "B has the higher peak (-1 vs -19 dBFS) but A is louder"),
]
def lufs_of(src):
    """Integrated loudness: the manifest's ground truth, else the build's audio-mcp measurement (verification),
    else (impulse_single_sample.wav only) measured here with pyloudnorm. validate.py re-measures all with pyloudnorm."""
    asset = MANIFESTS[src[0]][src[1]]
    if "lufs_integrated" in asset["ground_truth"]:
        return asset["ground_truth"]["lufs_integrated"]
    for r in asset["verification"]:
        if r["measure"] == "audio_analyze:levels.lufs_integrated":
            return r["measured"]
    import pyloudnorm
    import soundfile as sf
    x, sr = sf.read(str(ROOT / path(src)), always_2d=True)
    return pyloudnorm.Meter(sr).integrated_loudness(x)


LOUD_NOTE = "LUFS of trap stimuli are bounds from build checks; validate.py measures both files with pyloudnorm"
for a, b, diff, trap in LOUDER:
    kw = {"trap": trap} if trap else {}
    links = []
    for s in (a, b):
        gt = MANIFESTS[s[0]][s[1]]["ground_truth"]
        for f in ("lufs_integrated", "lufs_integrated_max"):
            if f in gt:
                links.append(link(s, f"ground_truth.{f}"))
    va, vb = lufs_of(a), lufs_of(b)
    add("loudness", "louder", [a, b], LOUDER_Q, "choice", "A" if va > vb else "B", "louder_measured", diff, links,
        LOUD_NOTE, options=PAIR_OPTIONS, **kw)

RMS_Q = "What is the RMS level of this file in dBFS (between -60 and 0)?"
for src in [ref("noise_pink_30s_-20dBFS_rms.wav"), ref("noise_white_10s_-20dBFS_rms.wav"),
            ref("tone_997Hz_-20dBFS_mono.wav"), stim("trap_dense_sine"), stim("white_-30rms"), stim("pink_-16rms"),
            stim("brown_-20rms")]:
    numeric("loudness", "rms", src, RMS_Q, "ground_truth.rms_dbfs", "dBFS", {"abs": 1.0}, [-60, 0], "medium")

PEAK_Q = "What is the sample peak level of this file in dBFS (between -60 and +6)?"
for src in [ref("tone_997Hz_-20dBFS_mono.wav"), ref("tone_A4_440Hz_-12dBFS.wav"),
            ref("sweep_log_20Hz-20kHz_10s_-6dBFS.wav"), stim("trap_dense_sine")]:
    numeric("loudness", "sample_peak", src, PEAK_Q, "ground_truth.peak_dbfs", "dBFS", {"abs": 0.5}, [-60, 6], "medium")
src = ref("true_peak_intersample_+2dBTP.wav")
numeric("loudness", "sample_peak", src, PEAK_Q, "ground_truth.sample_peak_dbfs", "dBFS", {"abs": 0.5}, [-60, 6], "hard")
numeric("loudness", "true_peak", src, "What is the true peak (inter-sample peak, ITU-R BS.1770) of this file in dBTP "
        "(between -60 and +6)?", "ground_truth.true_peak_dbtp", "dBTP", {"abs": 0.5}, [-60, 6], "hard")
TP_Q = "Is this file's true peak (inter-sample peak) at least 1 dB higher than its sample peak?"
add("loudness", "true_peak_over", [src], TP_Q, "choice", "yes", "construction", "hard",
    [link(src, "ground_truth.sample_peak_dbfs"), link(src, "ground_truth.true_peak_dbtp")],
    "true_peak_dbtp - sample_peak_dbfs = 3.01 dB", options=["yes", "no"])
for s in (ref("tone_997Hz_-20dBFS_mono.wav"), ref("tone_A4_440Hz_-12dBFS.wav"), stim("tone_E5_sine")):
    add("loudness", "true_peak_over", [s], TP_Q, "choice", "no", "construction", "medium", [],
        "a low-frequency sine (well below fs/4) has its true peak within a small fraction of a dB of its sample peak",
        options=["yes", "no"])

# ===================================== defects =====================================
CLIP_Q = "Is this file digitally clipped (samples flattened at full scale)?"
yesno("defects", "clipping", ref("problem_clipping.wav"), CLIP_Q, True, "ground_truth.clipped")
yesno("defects", "clipping", stim("clip_mild_sine"), CLIP_Q, True, "ground_truth.clipped", "medium")
yesno("defects", "clipping", stim("clip_pink"), CLIP_Q, True, "ground_truth.clipped", "hard")
for s, d, trap in [(ref("tone_997Hz_-20dBFS_mono.wav"), "easy", None), (ref("noise_white_10s_-20dBFS_rms.wav"), "easy", None),
                   (stim("tone_D4_square"), "medium", "square wave: flat-looking tops, but peak -6 dBFS and nothing clipped"),
                   (ref("true_peak_intersample_+2dBTP.wav"), "hard", "every sample sits at -1 dBFS (looks flat-topped) but nothing reaches full scale"),
                   (ref("loudness_pink_-16LUFS.wav"), "easy", None)]:
    yesno("defects", "clipping", s, CLIP_Q, False, difficulty=d, trap=trap,
          note="synthesized below full scale; validate.py confirms no sample reaches full scale")

DC_Q = "Does this file have a DC offset (a constant shift of the waveform away from zero)?"
yesno("defects", "dc_offset", ref("problem_dc_offset.wav"), DC_Q, True, "ground_truth.dc_offset")
yesno("defects", "dc_offset", stim("dc_on_noise"), DC_Q, True, "ground_truth.dc_offset", "medium")
for s in (ref("tone_A4_440Hz_-12dBFS.wav"), ref("noise_pink_30s_-20dBFS_rms.wav"), ref("chord_Cmaj7_sines.wav"),
          stim("tone_C3_saw")):
    yesno("defects", "dc_offset", s, DC_Q, False, None, note="no DC component in the recipe")

HUM_Q = "Is there mains hum in this file? Answer 'none', '50 Hz' or '60 Hz'."
HUM_OPTIONS = ["none", "50 Hz", "60 Hz"]
for s, d in [(ref("problem_mains_hum_60Hz.wav"), "medium"), (stim("hum_50Hz"), "medium"), (stim("hum_60Hz_under_noise"), "hard")]:
    add("defects", "mains_hum", [s], HUM_Q, "choice", f"{dig(s, 'ground_truth.hum_hz')} Hz", "hum_hz", d,
        [link(s, "ground_truth.hum_hz")], options=HUM_OPTIONS)
for s, d, trap in [(ref("tone_997Hz_-20dBFS_mono.wav"), "easy", None), (ref("noise_pink_30s_-20dBFS_rms.wav"), "medium", None),
                   (ref("melody_mary_had_a_little_lamb.wav"), "easy", None),
                   (ref("sweep_log_20Hz-20kHz_10s_-6dBFS.wav"), "hard", "the sweep passes through 50 and 60 Hz but is not hum")]:
    kw = {"trap": trap} if trap else {}
    add("defects", "mains_hum", [s], HUM_Q, "choice", "none", "construction", d, [],
        "no steady 50/60 Hz component in the recipe", options=HUM_OPTIONS, **kw)

ABRUPT_Q = "Does this file start abruptly, at a high level with no fade-in (so it clicks at the start)?"
yesno("defects", "abrupt_start", ref("problem_abrupt_start.wav"), ABRUPT_Q, True, "ground_truth.abrupt_start")
yesno("defects", "abrupt_start", stim("abrupt_sine"), ABRUPT_Q, True, "ground_truth.abrupt_start", "medium")
yesno("defects", "abrupt_start", stim("faded_burst"), ABRUPT_Q, False, "ground_truth.abrupt_start", "hard",
      trap="same noise burst as an abrupt one, but with a 20 ms fade-in")
for s in (ref("tone_A4_440Hz_-12dBFS.wav"), ref("problem_leading_silence.wav")):
    yesno("defects", "abrupt_start", s, ABRUPT_Q, False, None, note="recipe has a fade-in (synth default 5 ms attack)")

LOOP_Q = "If this file is played on repeat (looped), is there an audible click at the loop point?"
for s, d in [(ref("problem_loop_seam_click.wav"), "medium"), (ref("fixed_loop_seamless.wav"), "medium"),
             (stim("loop_clean_200Hz"), "medium"), (stim("loop_cut_200Hz"), "medium")]:
    yesno("defects", "loop_click", s, LOOP_Q, dig(s, "ground_truth.loop_click"), "ground_truth.loop_click", d)
yesno("defects", "loop_click", ref("noise_pink_30s_-20dBFS_rms.wav"), LOOP_Q, False, None, "hard",
      note="audio-mcp generates pink noise circularly, so it loops seamlessly as generated (see FRICTION.md)")

# ===================================== time =====================================
DUR_Q = "How long is this file, in seconds (between 0 and 30)?"
for s in [ref("silence_10s.wav"), ref("impulse_single_sample.wav"), ref("problem_loop_seam_click.wav"),
          ref("problem_leading_silence.wav"), ref("scale_chromatic_C4-C5_triangle.wav"),
          ref("melody_mary_had_a_little_lamb.wav"), ref("rhythm_clicks_120bpm_16beats.wav"),
          ref("noise_pink_30s_-20dBFS_rms.wav"), stim("padded_tone"), stim("tone_A#4_sine")]:
    d = dig(s, "format.duration_s")
    numeric("time", "duration", s, DUR_Q, "format.duration_s", "s", {"abs": round(max(0.05, 0.02 * d), 3)}, [0, 30],
            "hard" if s[1] in ("silence_10s.wav", "impulse_single_sample.wav") else "easy")
LEAD_Q = "How much silence is there at the START of this file, before the sound begins, in seconds (between 0 and {d:g})?"
TRAIL_Q = "How much silence is there at the END of this file, after the sound stops, in seconds (between 0 and {d:g})?"
for s in (ref("problem_leading_silence.wav"), stim("padded_tone")):
    d = dig(s, "format.duration_s")
    numeric("time", "leading_silence", s, LEAD_Q.format(d=d), "ground_truth.leading_silence_s", "s", {"abs": 0.05}, [0, d], "medium")
    numeric("time", "trailing_silence", s, TRAIL_Q.format(d=d), "ground_truth.trailing_silence_s", "s", {"abs": 0.05}, [0, d], "medium")
SIL_Q = "Is this file completely silent (digital silence)?"
yesno("time", "all_silent", ref("silence_10s.wav"), SIL_Q, True, "ground_truth.all_samples_zero", "medium")
yesno("time", "all_silent", ref("problem_too_quiet_-40LUFS.wav"), SIL_Q, False, None, "hard",
      note="pink noise at -40 LUFS: very quiet, not silent")

ONSET_Q = "How many separate sounds (onsets) are in this file? Count every click or note, including repeated ones (0 to 20)."
for s, field, d in [(ref("rhythm_clicks_120bpm_16beats.wav"), "ground_truth.onsets", "medium"),
                    (stim("clicks_3"), "ground_truth.onsets", "easy"), (stim("clicks_5"), "ground_truth.onsets", "medium"),
                    (stim("clicks_7"), "ground_truth.onsets", "medium"), (stim("tempo_90"), "ground_truth.onsets", "medium")]:
    numeric("time", "onset_count", s, ONSET_Q, field, "count", {"abs": 0}, [0, 20], d, integer=True)
for s, d in [(ref("melody_mary_had_a_little_lamb.wav"), "hard"), (stim("melody_frere_jacques"), "hard")]:
    notes = dig(s, "ground_truth.notes")
    add("time", "onset_count", [s], ONSET_Q, "numeric", len(notes), "count_of", d, [link(s, "ground_truth.notes")],
        "number of notes in the melody (repeated notes are separate onsets)", unit="count", tolerance={"abs": 0},
        range=[0, 20], integer=True)

TEMPO_Q = "This file is a steady click track. What is its tempo in BPM (one click per beat; between 40 and 200)?"
for s in (ref("rhythm_clicks_120bpm_16beats.wav"), stim("tempo_90"), stim("tempo_100"), stim("tempo_150")):
    numeric("time", "tempo", s, TEMPO_Q, "ground_truth.bpm", "BPM", {"abs": 2.0}, [40, 200], "medium")
IMP_Q = "This file contains a single click (one sample) in silence. At what time does it occur, in seconds (between 0 and {d:g})?"
for s in (ref("impulse_single_sample.wav"), stim("impulse_0.25s"), stim("impulse_1.2s")):
    d = dig(s, "format.duration_s")
    numeric("time", "impulse_time", s, IMP_Q.format(d=d), "ground_truth.impulse_time_s", "s", {"abs": 0.01}, [0, d], "hard")

# ===================================== stereo =====================================
CORR_Q = "What is the correlation between the left and right channels: 'positive', 'near zero' or 'negative'?"
CORR_OPTIONS = ["positive", "near zero", "negative"]
for s, field, d in [(ref("tone_997Hz_-23LUFS_stereo.wav"), None, "easy"), (ref("stereo_out_of_phase.wav"), "ground_truth.correlation", "medium"),
                    (ref("stereo_uncorrelated_noise.wav"), "ground_truth.correlation", "medium"),
                    (stim("stereo_pink_out_of_phase"), "ground_truth.correlation", "medium"),
                    (stim("stereo_pink_identical"), "ground_truth.correlation", "easy")]:
    if field:
        c = dig(s, field)
        ans = "positive" if c > 0.3 else "negative" if c < -0.3 else "near zero"
        add("stereo", "correlation", [s], CORR_Q, "choice", ans, "sign", d, [link(s, field)], options=CORR_OPTIONS)
    else:
        add("stereo", "correlation", [s], CORR_Q, "choice", "positive", "construction", d,
            [link(s, "ground_truth.channels")], "identical channels: correlation +1", options=CORR_OPTIONS)
CH_Q = "Which channels carry sound: 'left only', 'right only' or 'both'?"
CH_OPTIONS = ["left only", "right only", "both"]
add("stereo", "channels", [ref("stereo_left_only.wav")], CH_Q, "choice", "left only", "construction", "easy",
    [link(ref("stereo_left_only.wav"), "ground_truth.right")], "ground_truth.right = silence", options=CH_OPTIONS)
add("stereo", "channels", [stim("stereo_right_only")], CH_Q, "choice", "right only", "construction", "easy",
    [link(stim("stereo_right_only"), "ground_truth.left")], "ground_truth.left = silence", options=CH_OPTIONS)
for s, d, trap in [(ref("tone_997Hz_-23LUFS_stereo.wav"), "easy", None), (ref("stereo_uncorrelated_noise.wav"), "easy", None),
                   (ref("stereo_out_of_phase.wav"), "medium", "inverted right channel: still sound in both channels")]:
    kw = {"trap": trap} if trap else {}
    add("stereo", "channels", [s], CH_Q, "choice", "both", "construction", d, [], "both channels synthesized with signal",
        options=CH_OPTIONS, **kw)
OOP_Q = "Is this stereo file out of phase (one channel polarity-inverted, so it cancels when summed to mono)?"
for s, v, d, trap in [(ref("stereo_out_of_phase.wav"), True, "medium", None), (stim("stereo_pink_out_of_phase"), True, "medium", None),
                      (ref("tone_997Hz_-23LUFS_stereo.wav"), False, "easy", None),
                      (ref("stereo_uncorrelated_noise.wav"), False, "hard", "very wide, but not inverted (correlation 0, not -1)"),
                      (stim("stereo_pink_identical"), False, "easy", None)]:
    yesno("stereo", "out_of_phase", s, OOP_Q, v, None, d, trap=trap,
          note="ground_truth.correlation (or identical channels) by construction: -1 means inverted")

# ===================================== spectrum =====================================
TN_Q = "Is this sound a tone (periodic, with a pitch) or noise? Answer 'tone' or 'noise'."
for s, v, d in [(ref("tone_997Hz_-20dBFS_mono.wav"), "tone", "easy"), (ref("noise_white_10s_-20dBFS_rms.wav"), "noise", "easy"),
                (ref("noise_pink_30s_-20dBFS_rms.wav"), "noise", "easy"), (stim("brown_-20rms"), "noise", "medium"),
                (stim("tone_C3_saw"), "tone", "easy"), (ref("sweep_log_20Hz-20kHz_10s_-6dBFS.wav"), "tone", "medium"),
                (stim("tone_C#6_square"), "tone", "easy"), (stim("pink_-30LUFS"), "noise", "medium")]:
    add("spectrum", "tone_or_noise", [s], TN_Q, "choice", v, "construction", d, [],
        f"recipe wave: {'noise generator' if v == 'noise' else 'oscillator'}", options=["tone", "noise"])
COL_Q = "What colour of noise is this: 'white' (flat spectrum), 'pink' (-3 dB per octave) or 'brown' (-6 dB per octave)?"
for s in (ref("noise_white_10s_-20dBFS_rms.wav"), ref("noise_pink_30s_-20dBFS_rms.wav"), stim("pink_-35LUFS"),
          stim("white_-30rms"), stim("pink_-16rms"), stim("brown_-20rms"), stim("pink_-21LUFS")):
    add("spectrum", "noise_colour", [s], COL_Q, "choice", dig(s, "ground_truth.type"), "equal",
        "hard" if dig(s, "ground_truth.type") == "brown" else "medium", [link(s, "ground_truth.type")],
        options=["white", "pink", "brown"])
CHORD_Q = "Is this a single note or a chord (several notes at once)? Answer 'single note' or 'chord'."
for s in (ref("chord_Cmaj7_sines.wav"), stim("chord_Cmajor_sines"), stim("chord_Aminor_triangles")):
    add("spectrum", "chord_or_single", [s], CHORD_Q, "choice", "chord", "yesno_chord", "medium",
        [link(s, "ground_truth.polyphonic")], options=["single note", "chord"])
for s, d, trap in [(ref("tone_A4_440Hz_-12dBFS.wav"), "easy", None),
                   (stim("tone_G4_saw"), "hard", "a sawtooth has many harmonics but is one note"),
                   (stim("tone_D#5_square"), "hard", "a square wave has many harmonics but is one note"),
                   (stim("tone_F#4_triangle"), "medium", None)]:
    kw = {"trap": trap} if trap else {}
    add("spectrum", "chord_or_single", [s], CHORD_Q, "choice", "single note", "construction", d, [],
        "recipe: one oscillator layer", options=["single note", "chord"], **kw)

# ===================================== melody =====================================
MEL_Q = ("This file is a melody of {n} notes, one at a time. Write the notes in order as note names in scientific pitch "
         "notation (A4 = 440 Hz), between C3 and C6, separated by spaces, e.g. 'C4 D4 E4'. Repeated notes count separately.")
for s, d in [(ref("scale_chromatic_C4-C5_triangle.wav"), "medium"), (ref("melody_mary_had_a_little_lamb.wav"), "medium"),
             (stim("melody_twinkle"), "medium"), (stim("melody_frere_jacques"), "hard"), (stim("melody_wholetone_down"), "hard")]:
    notes = dig(s, "ground_truth.notes")
    add("melody", "transcription", [s], MEL_Q.format(n=len(notes)), "note_sequence", notes, "equal", d,
        [link(s, "ground_truth.notes")], range=["C3", "C6"])


def main():
    out = HERE / "items.jsonl"
    out.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in ITEMS), encoding="utf-8")
    counts = {}
    for i in ITEMS:
        counts[i["category"]] = counts.get(i["category"], 0) + 1
    print(f"wrote {out}: {len(ITEMS)} items", counts)


if __name__ == "__main__":
    main()
