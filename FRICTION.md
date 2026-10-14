# Friction log: building this pack with audio-mcp

This pack was made the way any AI agent would use audio-mcp: only through its MCP tools. Everything that was
wrong, awkward or missing was written down here and fixed in the tool. That was the point of the exercise.

First build: **16 of 22 files verified; 6 failed.** Four failures were tool problems and one was a mistake in a
recipe. The sixth turned out to be a useful property of the tool.

## Tool bugs found and fixed (audio-mcp 0.2.0)

| Symptom while building | Cause | Fix |
|---|---|---|
| A 997 Hz tone measured as 998.9 Hz (+3.3 cents); 1760 Hz read +10 cents sharp | YIN pitch refinement interpolated the normalized difference curve, which is biased sharp when a period spans few samples | Refine on the raw difference function: error at 1760 Hz fell from +10.2 to +0.6 cents |
| Pink noise labeled "mixed tonal/noise" (and brown noise, and even speech, labeled "tonal") | Whole-spectrum flatness treats any spectral slope as non-noise | Measure flatness per octave, energy-weighted: all noise colors now score about 0.57 and tones about 0 |
| Independent left/right noise flagged as an out-of-phase **error** | Any negative correlation (even -0.003) counted as a phase fault | Phase problems now need correlation below -0.3; wide stereo near 0 is reported as "wide", and the message gives the mono level loss |
| 4 ms clicks produced 0 events | Minimum event length was 30 ms | 10 ms minimum for events (splits inside a sound still need 30 ms, so glides aren't chopped up) |
| The last click in a file was never detected | The peak finder can't report the final frame; the event detector never measured the final partial frame | Pad both ends (the same edge case had been fixed for t=0, but not for the end) |

## Missing features that blocked assets (added in 0.2.0)

| Wanted | Workaround before | Now |
|---|---|---|
| Out-of-phase stereo | impossible | `polarity` op (all channels or one) |
| DC-offset problem file | impossible | `dc` synth wave |
| Single-sample impulse | impossible | `impulse` synth wave (single, or a train with `freq`) |
| Inter-sample-peak test | impossible (no phase control) | `phase` on oscillators, which now start exactly at that phase |
| Noise at an exact RMS level | analyze, then compute and apply the gain | `normalize_rms` op |
| Silence of a set length | a tone at -300 dB | `silence` synth wave |

## Recipe mistakes (the tool was right)

- **"Problem: loop seam click" didn't click.** audio-mcp generates pink and brown noise in the frequency domain,
  which makes it circular, so it loops seamlessly as generated. The recipe now cuts a section out of a longer noise
  (the way trimming a real recording breaks the loop), and the seamless looping is now documented as a feature.
- **True peak read +2.13 dBTP, against +2.01 in theory.** The test tone started and stopped abruptly, and a
  band-limited signal really does overshoot at a hard cut. With 10 ms fades it reads +2.03. The meter was correct.

## Possible improvements (not done yet)

- **Spectrogram low-frequency resolution.** On a 20 Hz-20 kHz sweep, everything below about 100 Hz looks like
  smeared blocks for the first seconds (bands are about 23 Hz wide at 48 kHz). An agent could misread that as
  low-frequency noise. A longer FFT for the low band, or a constant-Q display, would help.
- **Synth sequence durations**: a sequence ending in rests stops at the last sound, so the total length needs an
  explicit `duration`. That's reasonable, but easy to miss.

## Round 2: building the UI and retro-game effects pack

The 24 effects passed every technical check, but a set-level review through the tools (`audio_batch_survey`, plus
`audio_events` descriptions) showed problems that only appear once you treat the files as a *set*.

| Found | Cause | Fixed in the tool |
|---|---|---|
| Loudness spread of 8.8 dB even though every file was peak-normalized; the whoosh was far too quiet | Peak level isn't perceived loudness, and integrated LUFS is undefined under 0.4 s, so short effects had no perceptual measure | New `lufs_momentary_max` (EBU momentary loudness, loudest 400 ms window, defined for any length) in the analysis output; `normalize_lufs(measure="momentary_max")`. Spread fell to 1.0 dB |
| The batch survey suggested peak-normalizing files that were already peak-normalized | It fell back to RMS and a generic suggestion for short files | The survey compares one-shots by momentary loudness and suggests `normalize_lufs` with `measure="momentary_max"` and no limiter |
| 22 files warned "true peak above -1 dBTP" after normalizing to -1 dBFS | Sample peak isn't true peak | `normalize_peak(true_peak=true)`. `normalize_lufs`'s ceiling is now always a true-peak ceiling (it already was when limiting, but not otherwise) |
| Brown-noise sounds showed a DC offset and "53% of energy below 20 Hz" | The coloured-noise generator had energy all the way down to 0 Hz | Pink and brown noise now have nothing below 20 Hz, and still loop seamlessly |
| "Mains hum at 50 Hz (peaks at 250 Hz)" on a sound with one note at 250 Hz | Any peak on a mains harmonic counted | Hum now needs the 50/60 Hz fundamental or its 2nd harmonic |

Still open (logged, not fixed):
- **Over-splitting in `audio_events`:** a smooth pitch sweep (`game_jump`) or a noise swell (`ui_whoosh`) gets
  split into several events, because spectral-flux onsets fire as energy moves between frequency bins.
- **Fast chirps and dense square-wave sweeps read as "noisy"** in short analysis windows. That's arguably accurate
  for the window, but surprising.
- **Layered sounds confuse per-event pitch** (melody plus bass reads as glides). This is the known one-note-at-a-time
  limit.

A side effect of the noise-generator fix: the reference pack's "bad loop" file, which relied on random brown
noise, stopped clicking. The rebuild check caught it, and the file is now a deterministic tone cut mid-cycle.
