# Perception benchmark: can an AI hear basic physical properties of audio?

**193 machine-gradable questions about 94 audio files**, covering pitch, loudness, defects, timing, stereo, spectrum and
melody. **Every answer is known by construction:** each file was synthesized from a recipe of
[audio-mcp](https://github.com/mshark1/audio-mcp) tool calls, verified by the tool when built, and then re-measured
by `validate.py` with separate code that doesn't use audio-mcp.

The benchmark scores two kinds of systems on **identical items**:

- **native audio models**, which listen to the audio directly;
- **tool-using agents**, such as an LLM calling audio-mcp's analysis tools.

That makes it possible to ask whether an agent with measurement tools beats a model that "hears", and on which
properties. [`prompts.md`](prompts.md) explains how to run both.

## Why

Two 2026 benchmarks report that audio-language models are weak at basic physical audio properties:

- **SonicBench** (Sun et al., arXiv:2601.11039, January 2026). It tests 12 physical attributes in five dimensions:
  spectral and amplitude (pitch, brightness, loudness, velocity), temporal (duration, tempo), spatial and
  environment (direction, distance, reverberation), timbre (timbre, texture) and scene-level (counting).
  - It has 2,400 items. Each attribute gets 100 *recognition* items (one 4 s clip) and 100 *comparison* items (two
    4 s clips joined by a 0.5 s gap).
  - Every item is a binary A/B choice scored by exact match. Chance is 50%, and an answer that can't be parsed
    counts as an abstention (wrong).
  - Stimuli come from a generation toolbox plus public corpora, and labels come from generation parameters or
    physical measurements.
  - Humans averaged 91%. The best model (Qwen3-Omni) scored 72%, and about half of the models were near chance.
    Linear probes on frozen audio encoders reached at least 60%, so the authors place the bottleneck in alignment
    and decoding rather than in the encoder.
  - <https://arxiv.org/abs/2601.11039> (accessed 2026-10-13).
- **PitchBench** (Liessens Dujardin, Yu, Thomas-Smith, Chan and Nguyen, arXiv:2605.26176, May 2026). It runs 28 pitch
  experiments in three levels: single tones; context (chords, sequences, acoustic variations); and melodic lines,
  including voices in Bach chorales.
  - Stimuli use 19 timbres: four synthetic waveforms and 15 General MIDI instruments rendered with FluidSynth, at
    16 kHz.
  - Answers are pitch labels as MIDI numbers, scientific pitch notation, solfège or Hz. Grading is mostly exact
    match with enharmonics accepted, Hz answers get a ±1% tolerance, and note sequences are graded position-exact.
  - The authors report that pitch hearing is unreliable across frontier models. Mean accuracy ranged from 47.7%
    (Qwen-3.5 Omni Plus) to 8.4% (GPT-4o audio).
  - <https://arxiv.org/abs/2605.26176> (accessed 2026-10-13).

These summaries come from the arXiv abstract pages and HTML full texts. I couldn't find PitchBench's package URL on
the arXiv page, so none is cited here.

**How this benchmark complements them:**

- **Engineering properties they don't cover:** LUFS, RMS, sample peak vs true peak, clipping, DC offset, mains
  hum, abrupt starts, loop-seam clicks, leading and trailing silence, impulse timing, stereo correlation and
  polarity, and noise colour. These are what an agent editing audio actually has to get right.
- **Exact numbers:** many items ask for a value with a tolerance ("-23 LUFS ±1"), not only a binary choice.
- **Traps:** 17 items where an easy cue points the wrong way. Examples: a sawtooth that is brighter but lower than a
  sine, a clip with the higher peak but the lower loudness, a wide uncorrelated stereo file that isn't
  out of phase, and a square wave that looks flat-topped but isn't clipped.
- **A tool ceiling:** a rule-based baseline calls audio-mcp to show what measurement tools make possible on
  the same items.
- **Compatible conventions:**
  - Comparisons use SonicBench's A/B format and present clip A, then clip B.
  - Pitch uses PitchBench's conventions: scientific pitch notation (A4 = 440 Hz), enharmonics equal, ±1% for
    frequency in Hz, and position-exact grading of note sequences.

## Items

`items.jsonl` has one JSON object per line:

```json
{"id": "loudness.louder.06", "category": "loudness", "task": "louder",
 "audio": ["perception-benchmark/stimuli/stim_038.wav", "perception-benchmark/stimuli/stim_039.wav"],
 "question": "You hear two clips: A (first file) then B (second file). Which clip is louder, in integrated loudness (LUFS, ITU-R BS.1770), not in peak level? Answer A or B.",
 "answer_type": "choice", "options": ["A", "B"], "answer": "B",
 "provenance": {"derivation": "louder_measured", "links": [{"manifest": "perception-benchmark/stimuli/manifest.json", "file": "stim_038.wav", "field": "ground_truth.lufs_integrated_max", "value": -35.0}], "note": "..."},
 "difficulty": "hard", "trap": "A has the higher peak (-1 vs -12 dBFS) but B is far louder"}
```

| Field | Meaning |
|---|---|
| `id` | `category.task.NN` |
| `audio` | one or two paths, relative to the repository root. With two, A is the first and B the second |
| `question` | the question text, which states the allowed options or range |
| `answer_type` | `choice` (with `options`), `numeric` (with `unit`, `tolerance` as `{"abs": x}` or `{"rel": r}`, `range`, and `integer` for counts), `note` (with `range`) or `note_sequence` (with `range`) |
| `answer` | the ground truth |
| `provenance` | `links` give the manifest fields that prove the answer, with their values. `derivation` is the rule from those fields to the answer: `equal`, `yesno`, `higher`, `sign`, `nearest_note`, `hum_hz`, `count_of`, `yesno_chord`, `louder_measured` or `construction` (follows from the recipe; see `note`) |
| `difficulty` | `easy`, `medium` or `hard` (hand-assigned: 48 / 99 / 46) |
| `trap` | present on the 17 items where a salient cue points the wrong way; says what the cue is |

### Categories and counts

| Category | Tasks (items) | Answer types |
|---|---|---|
| pitch (53) | note name (26), frequency in Hz ±1% (12), which is higher (15, incl. 4 brightness traps and 3 fine 23-47 cent pairs) | note, numeric, choice |
| loudness (37) | LUFS ±1 LU (10), which is louder (10, incl. 5 peak-vs-loudness traps), RMS ±1 dB (7), sample peak ±0.5 dB (5), true peak ±0.5 dB (1), true peak ≥1 dB above sample peak? (4) | numeric, choice |
| defects (31) | clipping (8), DC offset (6), mains hum none/50/60 Hz (7), abrupt start (5), loop-seam click (5) | choice |
| time (30) | duration (10), leading silence (2), trailing silence (2), all silent? (2), onset count (7), tempo BPM ±2 (4), impulse time ±10 ms (3) | numeric, choice |
| stereo (15) | correlation positive/near zero/negative (5), channels left/right/both (5), out of phase? (5) | choice |
| spectrum (22) | tone or noise (8), white/pink/brown noise (7), chord or single note (7) | choice |
| melody (5) | transcribe 6 to 13 notes: chromatic scale, *Mary Had a Little Lamb*, *Twinkle Twinkle* and *Frère Jacques* openings (all public domain), and a whole-tone exercise | note_sequence |

### Audio

- **26 files from [`reference-signals/`](../reference-signals/)**, used as they are.
- **68 new stimuli in [`stimuli/`](stimuli/)**: tones at 24 pitches on four waveforms, 6 off-grid frequencies,
  pink noise at 6 loudness levels, peak-vs-loudness traps, clipped/DC/hum/abrupt/loop variants and their clean
  counterparts, click tracks, impulses, stereo variants, chords and melodies.
  - They are built the same way as the other packs: `stimuli/make_recipes.py` writes `recipes.json` (recipes
    plus checks), and `python tools/build.py perception-benchmark/stimuli` renders them over MCP and writes
    `manifest.json` (104 checks, all passing).
  - File names are opaque (`stim_001.wav`) so they don't give the answer away.
  - Format: 48 kHz, 24-bit WAV, mostly 0.8 to 3 s each, 18 MB in total.
- `make_items.py` generates `items.jsonl` from both manifests, so answers are read from manifest fields rather than
  typed by hand.

### Validation (`validate.py`, run in CI)

1. **Schema:** required fields, the answer is among the options or inside the stated range, and ids are unique.
2. **Files:** every audio file exists.
3. **Provenance:** every linked manifest field still holds the recorded value, and the answer follows from it by
   the stated derivation.
4. **Independent re-measurement** (numpy, scipy, soundfile and pyloudnorm only, no audio-mcp code) for 179 of the
   193 items:
   - pitch: zero-padded FFT peak;
   - loudness: pyloudnorm, and true peak by 8x oversampling;
   - defects and time: sample counts, the sample mean, the seam jump, click positions, and the narrowband peak at
     50/60 Hz;
   - stereo: correlation;
   - spectrum: slope-detrended spectral flatness for tone vs noise, and the dB/octave slope for noise colour.

   For the trap pairs, it also confirms that peak and loudness really do point opposite ways. The other 14 items
   (chords, melodies, and the two melody onset counts) rest on their recipe and manifest checks.

## Scoring

```bash
python perception-benchmark/score.py predictions.jsonl --name "my model" --json result.json
```

- **Input:** one `{"id": ..., "answer": ...}` per line. Answers can be free-form; [`prompts.md`](prompts.md#what-the-scorer-accepts)
  lists what is accepted, such as `440 Hz`, `0.44 kHz`, `A4`, `Gb3` for F#3, `first` for A, `true` for yes, and
  `1500 ms` for 1.5 s.
- **Output:** a table and JSON with the score per category, task, difficulty and for traps; the overall micro
  (per-item) and macro (per-category) averages; missing answers; and, for numeric tasks, the absolute-error
  median and 90th percentile.
- **Chance** is computed per item as the expected score of a uniform random guess over the answer space the
  question states:
  - choice: 1/number of options;
  - note: 1/number of notes in the stated range (C2 to C7, 61 notes);
  - note sequence: the same per note (C3 to C6);
  - numeric: the fraction of the stated range covered by the tolerance window (exact for integer counts).

  Numeric chance is therefore low by design, so read numeric scores together with the error distribution.
- **Answer skew:** chance assumes uniform guessing, but the answers aren't perfectly balanced. Across the 35 yes/no
  items, "no" is the answer on 22 and "yes" on 13. A model that always says "no"
  would beat chance there, so check per-task scores.

## Baseline results (measured)

| Baseline | Overall (micro) | Macro over categories | pitch | loudness | defects | time | stereo | spectrum | melody |
|---|---|---|---|---|---|---|---|---|---|
| Chance (analytic) | 24.6% | | 15.1% | 20.7% | 46.2% | 5.9% | 38.9% | 44.7% | 2.7% |
| Random (`baselines/random.py`, seed 0) | 23.4% | 23.5% | 11.3% | 27.0% | 41.9% | 10.0% | 40.0% | 31.8% | 2.5% |
| Tool ceiling (`baselines/audio_mcp_tools.py`, audio-mcp 0.3.0) | **98.7%** | 97.4% | 100% | 100% | 100% | 96.7% | 100% | 95.5% | 90% |

- **Random baseline:** over seeds 0 to 10 the overall score ranged from 21.2% to 29.0%, with a mean of 24.5%,
  matching the analytic chance.
- **Tool ceiling: what it is.** It is **not an LLM and not an agent**: it applies one hand-written rule per task to
  audio-mcp's output (for example, `pitch.median.note` for note names, `levels.lufs_integrated` for loudness, and
  `issues` for mains hum). The audio is copied to opaque names first.
- **What it shows:** what the tools make possible, an upper reference for a tool-using agent, which still has to
  pick the right tool and read the right field. Its predictions and a per-item trace of the measurements are in
  [`baselines/results/`](baselines/results/).
- **Model results:** none are reported here. This repository can't run external models, so no native-audio or
  LLM-agent results exist yet.

### Tool misses

With audio-mcp 0.3.0 the tool ceiling misses 3 of 193 items (98.7%). Each is a real limitation of the tool,
and the ground truth was re-checked independently. The first row below was a fourth miss in 0.2.0 (98.2% then):
this benchmark found it, and it was **fixed in audio-mcp 0.3.0**, which is the point of building it.

| Item | Expected | Tool gave | Cause |
|---|---|---|---|
| ~~`loudness.true_peak_over.02`~~ **fixed in 0.3.0** (`reference-signals/tone_997Hz_-20dBFS_mono.wav`) | no (true peak ≈ sample peak, -19.99 dBTP) | 0.2.0 said yes: `true_peak_dbtp` -18.92, +1.08 dB over the sample peak. 0.3.0 reads -19.99 | **Bug in `dsp.true_peak`:** it oversamples in blocks of 2^18 samples with 64-sample padding, but takes the maximum over the padded edges too. The resampler rings where a block boundary cuts the waveform, so a steady tone longer than 5.46 s at 48 kHz reads about 1 dB high (`tone_997Hz_-23LUFS_stereo.wav`: -21.92 instead of -22.99 dBTP). Discarding the padded margins of each upsampled block gives the correct value. |
| `time.tempo.04` (`stim_058`, 8 clicks at 150 BPM, 3.2 s) | 150 BPM | no `tempo_bpm` in the output | The tool finds all 8 onsets at exactly 0.4 s spacing ("very regular") but reports no tempo; 90 and 100 BPM files of 8 clicks get one. |
| `spectrum.chord_or_single.02` (`stim_064`, C major triad C4 E4 G4, sines) | chord | single note: `polyphony_likely` false | C4:E4:G4 is close to 4:5:6, which fits harmonics 4 to 6 of C2, so the harmonic-series test accepts it as one note with a missing fundamental. `spectrum.spectral_peaks` does list C4, E4 and G4. The Cmaj7 and A minor (triangle) chords are detected. |
| `melody.transcription.04` (`stim_067`, *Frère Jacques* opening on a sine) | C4 D4 E4 C4 C4 D4 E4 C4 | C4 D4 E4 C4 D4 E4 C4 (score 0.5: the merge shifts every later note by one position) | `audio_melody` merges the repeated C4 C4 into one 0.68 s note, although each note has its own 30 ms release and 5 ms attack. `audio_events` on the same file separates them (`pitched_sequence` matches exactly). Repeated notes on the triangle-wave *Mary Had a Little Lamb* are kept apart. |

Two of these also turned up while building the stimuli. The build checks for `stim_058` (tempo) and `stim_067`
(melody) were changed to construction-level checks that the tool passes (onset count; `audio_events`
pitched sequence), with comments in `stimuli/make_recipes.py`, so the build stays green while the miss is still
measured here.

Not counted as misses, but worth knowing:

- `spectrum.brightness` labels pink noise "very bright/harsh" (centroid 8.2 kHz) and brown noise "bright".
- There is no direct noise-colour output; the ceiling infers it from `band_energy_percent`.
- `audio_events` places the single-sample impulse at 0.49 s instead of 0.50 s, exactly at the edge of the ±10 ms
  tolerance (still scored correct).

## Limitations

- **Synthetic, single-source signals.** Everything is synthesized: sines, band-limited classic waveforms, coloured
  noise and clicks, mostly one source at a time, with no recordings, speech, real instruments, rooms or mixes.
  Scores here say nothing about perception of real-world audio; they test basic properties under ideal conditions.
- **One generator.** audio-mcp both made and (in the ceiling) measured the audio. `validate.py`'s independent
  checks guard the ground truth, but the tool ceiling is somewhat favoured: the stimuli are the kind of signals
  the tool was developed on.
- **Small per task.** Some tasks have 1 to 5 items (true peak, leading/trailing silence, all-silent, melody), so
  their scores are coarse. Report categories, not single tasks.
- **Not covered:** direction and distance, reverberation, timbre and instrument identity, velocity, texture,
  counting overlapping sources, speech, emotion, events in real scenes, perceptual (equal-loudness) loudness rather
  than BS.1770, pitch of real instruments or voices, vibrato, and microtonal intonation below about 20 cents.
  SonicBench and PitchBench cover several of these.
- **Hand-assigned difficulty**, not calibrated against people. There is no human baseline yet.
- **Exact samples matter.** Peak, true-peak, clipping, DC and loop-seam items assume lossless 48 kHz input. APIs that
  resample or compress change what the model receives (see `prompts.md`).

## Rebuild

```bash
python perception-benchmark/stimuli/make_recipes.py && python tools/build.py perception-benchmark/stimuli
python perception-benchmark/make_items.py
python perception-benchmark/validate.py
python perception-benchmark/baselines/random.py && python perception-benchmark/score.py perception-benchmark/baselines/results/random.jsonl
python perception-benchmark/baselines/audio_mcp_tools.py && python perception-benchmark/score.py perception-benchmark/baselines/results/audio_mcp_tools.jsonl
```

`validate.py` needs numpy, scipy, soundfile and pyloudnorm. `score.py` and `baselines/random.py` need only Python.
The stimulus build needs `audio-mcp>=0.2.0`; the tool-ceiling numbers above were measured with 0.3.0.

## License

[CC0 1.0 Universal](../LICENSE): the items, audio, code and documentation are dedicated to the public domain.
