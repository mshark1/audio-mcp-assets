# audio-mcp reference signals

**26 test and calibration audio files with known ground truth**: tones, sweeps, calibrated noise,
loudness references, stereo and phase tests, impulses, an inter-sample-peak test, and deliberately broken
"problem files". Use them to check audio software, meters and plugins, or to test whether an AI can really perceive
audio.

- **Public domain (CC0 1.0).** Use them for anything, no attribution needed.
- **Every file is synthesized from scratch** (no recordings or samples) with [audio-mcp](https://github.com/mshark1/audio-mcp),
  an MCP server that gives AI agents audio perception and editing tools. An AI agent built this pack by calling
  those tools over MCP; the exact tool calls for each file are in `recipes.json`.
- **Every file is verified twice:**
  1. `manifest.json`: 51 checks of each file's intended properties, measured with audio-mcp's own analysis tools.
  2. `tools/verify_independent.py`: 32 checks that use **no audio-mcp code at all** (numpy, scipy and pyloudnorm,
     reading the samples directly), so a bug in the tool can't confirm itself.

All files are 48 kHz, 24-bit WAV.

### Tones and pitch

| File | What it is | Verified |
|---|---|---|
| `tone_997Hz_-20dBFS_mono.wav` | Steady 997 Hz sine (the EBU reference frequency, chosen to avoid aligning with sample rates), sample peak -20 dBFS, 10 s. *(10 s, mono)* | 4/4 |
| `tone_997Hz_-23LUFS_stereo.wav` | 997 Hz sine in both channels, normalized to exactly -23 LUFS integrated (EBU R128 broadcast target). Use it to check a loudness meter. *(10 s, stereo)* | 2/2 |
| `tone_A4_440Hz_-12dBFS.wav` | Concert A (A4 = 440 Hz) sine at -12 dBFS peak, 5 s. Tuning and pitch-detection reference. *(5 s, mono)* | 3/3 |
| `scale_chromatic_C4-C5_triangle.wav` | Chromatic scale C4 to C5, 13 notes of 0.4 s each on a band-limited triangle wave. Melody/pitch-tracking reference. *(5.2 s, mono)* | 1/1 |
| `melody_mary_had_a_little_lamb.wav` | 'Mary Had a Little Lamb' (public domain), triangle wave, quarter note = 0.4 s. Includes repeated notes, which a melody transcriber must keep separate. *(6.4 s, mono)* | 1/1 |
| `chord_Cmaj7_sines.wav` | C major 7 chord (C4 E4 G4 B4) of equal-level sines, 4 s. A monophonic pitch tracker should report this as polyphonic, not as one note. *(4 s, mono)* | 2/2 |
| `sweep_log_20Hz-20kHz_10s_-6dBFS.wav` | Exponential (logarithmic) sine sweep from 20 Hz to 20 kHz over 10 s, -6 dBFS peak. Frequency-response and spectrogram reference. *(10 s, mono)* | 2/2 |

### Noise and loudness

| File | What it is | Verified |
|---|---|---|
| `noise_pink_30s_-20dBFS_rms.wav` | Pink noise (equal energy per octave), 30 s, -20 dBFS RMS: the usual level for speaker and room calibration. *(30 s, mono)* | 3/3 |
| `noise_white_10s_-20dBFS_rms.wav` | White noise (flat spectrum), 10 s, -20 dBFS RMS. *(10 s, mono)* | 2/2 |
| `loudness_pink_-16LUFS.wav` | Pink noise at exactly -16 LUFS integrated (common podcast/voice target), 20 s, no limiting. *(20 s, mono)* | 1/1 |
| `loudness_pink_-23LUFS.wav` | Pink noise at exactly -23 LUFS integrated (EBU R128 broadcast target), 20 s. *(20 s, mono)* | 1/1 |
| `silence_10s.wav` | 10 s of digital silence (every sample exactly zero). *(10 s, mono)* | 1/1 |

### Stereo

| File | What it is | Verified |
|---|---|---|
| `stereo_left_only.wav` | 440 Hz tone in the left channel only; right channel silent. Channel-identification test. *(4 s, stereo)* | 2/2 |
| `stereo_out_of_phase.wav` | 440 Hz tone with the right channel polarity-inverted (correlation -1). Sounds wide on headphones but cancels to silence in mono: the classic phase-problem test. *(4 s, stereo)* | 2/2 |
| `stereo_uncorrelated_noise.wav` | Independent white noise in each channel (correlation near 0): maximally wide, no phase relationship. *(6 s, stereo)* | 2/2 |

### Timing and peaks

| File | What it is | Verified |
|---|---|---|
| `rhythm_clicks_120bpm_16beats.wav` | 16 short clicks at exactly 120 BPM (one every 0.5 s, first at t=0). Onset and tempo reference. *(8 s, mono)* | 3/3 |
| `impulse_single_sample.wav` | One full-scale sample (+1.0) at exactly 0.5 s in 1 s of silence. Impulse-response, latency and alignment reference. *(1 s, mono)* | 3/3 |
| `true_peak_intersample_+2dBTP.wav` | 12 kHz sine at 45 degrees phase (a quarter of the sample rate): every sample sits at -1.0 dBFS but the reconstructed waveform peaks about 3 dB higher, at +2.0 dBTP. Sample-peak meters miss this; true-peak meters (BS.1770) must catch it. *(3 s, mono)* | 3/3 |

### Problem files (and fixes)

| File | What it is | Verified |
|---|---|---|
| `problem_clipping.wav` | PROBLEM FILE: 220 Hz tone driven 6 dB past full scale, so its peaks are flattened (hard clipping). An analyzer should flag it. *(3 s, mono)* | 2/2 |
| `problem_mains_hum_60Hz.wav` | PROBLEM FILE: gated 700 Hz tone over 60 Hz mains hum (with a 180 Hz harmonic) and faint hiss, as from a ground loop. *(6 s, mono)* | 1/1 |
| `problem_leading_silence.wav` | PROBLEM FILE: a short tone preceded by 1.5 s and followed by 1.0 s of silence (a common one-shot sound-effect defect). *(3 s, mono)* | 3/3 |
| `problem_too_quiet_-40LUFS.wav` | PROBLEM FILE: pink noise at -40 LUFS, far below any delivery target. An analyzer should flag it as very quiet. *(10 s, mono)* | 2/2 |
| `problem_abrupt_start.wav` | PROBLEM FILE: noise burst that starts at full level with no fade-in, so playback begins with a click. *(1 s, mono)* | 1/1 |
| `problem_loop_seam_click.wav` | PROBLEM FILE: a 110 Hz drone meant to loop, but cut mid-cycle (2.0025 s = 220.275 periods), so the waveform jumps from about +0.5 back to 0 at every repeat: an audible click. Pair with fixed_loop_seamless.wav. *(2.002 s, mono)* | 1/1 |
| `fixed_loop_seamless.wav` | FIXED: problem_loop_seam_click.wav after a 100 ms equal-power loop crossfade; the seam is now continuous and it repeats without a click. *(1.903 s, mono)* | 1/1 |
| `problem_dc_offset.wav` | PROBLEM FILE: 440 Hz tone riding on a constant DC offset of +0.1 (a fault from some converters and cheap interfaces). Fix with remove_dc or a high-pass filter. *(3 s, mono)* | 2/2 |

## For AI agents and test harnesses

`reference-signals/manifest.json` is machine-readable: for every file it lists the format, the `ground_truth`
(what the file *is*), the `verification` results (expected vs. measured) and the `recipe` (the tool calls that
made it). A model or audio tool under test can be scored against `ground_truth` directly.

## Also in this repository: UI and retro game sounds

[`sfx-retro-ui/`](sfx-retro-ui/) has 24 short interface and retro-game sound effects (clicks, toggles,
notifications, coin, jump, laser, explosion and more), also CC0 and synthesized from recipes, loudness-matched,
listened to by a person, and checked for resemblance to famous game sounds. Its README explains the provenance,
including one design that was withdrawn for sounding like a famous effect.

## Perception benchmark: can an AI hear these properties?

[`perception-benchmark/`](perception-benchmark/) has 193 machine-gradable questions about 94 files (these reference
signals plus 68 new stimuli), covering pitch, loudness, defects, timing, stereo, spectrum and melody. Every answer is
known by construction and re-measured independently.

- It scores native audio models and tool-using agents (an LLM calling audio-mcp) on identical items.
- It complements SonicBench and PitchBench with engineering properties such as LUFS, true peak, clipping, hum and
  loop seams, plus deliberate traps where peak and loudness, or brightness and pitch, disagree.
- Measured baselines: random 23.4% (chance 24.6%), and a rule-based audio-mcp "tool ceiling" (not an LLM) at 98.2%.
  The ceiling's four misses are documented as tool limitations.

## Rebuild or extend

```bash
pip install "audio-mcp>=0.2.0" pyloudnorm   # 0.2.0 added the features this pack needs
python tools/build.py reference-signals               # regenerate every file via MCP and re-verify
python tools/verify_independent.py reference-signals  # independent cross-check
```

To add a signal or a sound, see [CONTRIBUTING.md](CONTRIBUTING.md) (design rules and checks). Building this pack
turned up several bugs and missing features in audio-mcp, which were fixed upstream; see [FRICTION.md](FRICTION.md).

## License

[CC0 1.0 Universal](LICENSE): dedicated to the public domain.
