"""Independent check of the reference pack, using NO audio-mcp code: only soundfile, numpy, scipy and pyloudnorm.

build.py verifies each file with the same tool that made it, which can't catch a bug that affects both. This script
re-derives the key ground truth straight from the samples with separate, simple implementations.

Usage: python tools/verify_independent.py reference-signals
"""

import sys
from pathlib import Path

import numpy as np
import pyloudnorm
import soundfile as sf
from scipy import signal


def db(x):
    return 20 * np.log10(max(x, 1e-12))


def rms_db(x):
    return 10 * np.log10(max(np.mean(np.square(x, dtype=np.float64)), 1e-24))


def lufs(x, sr):
    return pyloudnorm.Meter(sr, filter_class="DeMan").integrated_loudness(x)


def dominant_hz(x, sr):
    """Frequency of the strongest spectral peak, refined by zero-padding (independent of any pitch tracker)."""
    n = 1 << 22
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)), n))
    return np.fft.rfftfreq(n, 1 / sr)[np.argmax(spec)]


def true_peak_db(x, factor=8):
    return db(np.max(np.abs(signal.resample_poly(x, factor, 1, axis=0))))


def approx(value, target, tol):
    return abs(value - target) <= tol


CHECKS = {
    "tone_997Hz_-20dBFS_mono.wav": lambda x, sr: [
        ("peak dBFS = -20.00", approx(db(np.abs(x).max()), -20, 0.01)),
        ("dominant frequency = 997 Hz", approx(dominant_hz(x[:, 0], sr), 997, 0.05)),
    ],
    "tone_997Hz_-23LUFS_stereo.wav": lambda x, sr: [
        ("LUFS = -23.0 (pyloudnorm)", approx(lufs(x, sr), -23, 0.05)),
        ("channels identical", np.array_equal(x[:, 0], x[:, 1])),
    ],
    "tone_A4_440Hz_-12dBFS.wav": lambda x, sr: [
        ("dominant frequency = 440 Hz", approx(dominant_hz(x[:, 0], sr), 440, 0.05)),
        ("peak dBFS = -12.00", approx(db(np.abs(x).max()), -12, 0.01)),
    ],
    "noise_pink_30s_-20dBFS_rms.wav": lambda x, sr: [("RMS = -20.00 dBFS", approx(rms_db(x), -20, 0.01))],
    "noise_white_10s_-20dBFS_rms.wav": lambda x, sr: [("RMS = -20.00 dBFS", approx(rms_db(x), -20, 0.01))],
    "loudness_pink_-16LUFS.wav": lambda x, sr: [("LUFS = -16.0 (pyloudnorm)", approx(lufs(x, sr), -16, 0.05))],
    "loudness_pink_-23LUFS.wav": lambda x, sr: [("LUFS = -23.0 (pyloudnorm)", approx(lufs(x, sr), -23, 0.05))],
    "problem_too_quiet_-40LUFS.wav": lambda x, sr: [("LUFS = -40.0 (pyloudnorm)", approx(lufs(x, sr), -40, 0.05))],
    "silence_10s.wav": lambda x, sr: [("every sample is zero", not x.any()), ("10 s long", len(x) == 10 * sr)],
    "stereo_left_only.wav": lambda x, sr: [("right channel all zero", not x[:, 1].any()), ("left has signal", x[:, 0].any())],
    "stereo_out_of_phase.wav": lambda x, sr: [("right = -left exactly", np.array_equal(x[:, 1], -x[:, 0]))],
    "stereo_uncorrelated_noise.wav": lambda x, sr: [
        ("|correlation| < 0.02", abs(np.corrcoef(x[:, 0], x[:, 1])[0, 1]) < 0.02)
    ],
    "impulse_single_sample.wav": lambda x, sr: [
        ("exactly one nonzero sample", np.count_nonzero(x) == 1),
        ("at index 24000 (0.5 s)", int(np.flatnonzero(x[:, 0])[0]) == 24000),
        ("value = +1.0 (full scale; 24-bit max)", approx(float(x[24000, 0]), 1.0, 2**-22)),
    ],
    "true_peak_intersample_+2dBTP.wav": lambda x, sr: [
        ("sample peak = -1.00 dBFS", approx(db(np.abs(x).max()), -1.0, 0.01)),
        ("true peak = +2.0 dBTP (8x oversampled)", approx(true_peak_db(x), 2.01, 0.05)),
    ],
    "problem_dc_offset.wav": lambda x, sr: [("mean (DC) = 0.100", approx(float(x.mean()), 0.1, 0.001))],
    "problem_clipping.wav": lambda x, sr: [("> 1000 samples at full scale", np.count_nonzero(np.abs(x) >= 0.9999) > 1000)],
    "problem_leading_silence.wav": lambda x, sr: [
        ("first non-zero sample at 1.5 s", approx(np.flatnonzero(np.abs(x[:, 0]) > 1e-6)[0] / sr, 1.5, 0.002)),
        ("last non-zero sample 1.0 s before end", approx((len(x) - 1 - np.flatnonzero(np.abs(x[:, 0]) > 1e-6)[-1]) / sr, 1.0, 0.002)),
    ],
    "problem_loop_seam_click.wav": lambda x, sr: [
        ("seam jump |last - first| > 0.3 (an audible click)", abs(float(x[-1, 0] - x[0, 0])) > 0.3)
    ],
    "fixed_loop_seamless.wav": lambda x, sr: [
        ("seam jump no bigger than a normal sample step", abs(float(x[-1, 0] - x[0, 0])) <= np.abs(np.diff(x[:, 0])).max())
    ],
    "rhythm_clicks_120bpm_16beats.wav": lambda x, sr: [
        ("clicks start every 0.500 s", _click_starts(x[:, 0], sr)),
    ],
    "sweep_log_20Hz-20kHz_10s_-6dBFS.wav": lambda x, sr: [
        ("starts near 20 Hz", approx(dominant_hz(x[: sr // 2, 0], sr), 20 * 2 ** (0.25 * np.log2(1000) / 10), 3)),
        ("ends near 20 kHz", approx(dominant_hz(x[-sr // 20 :, 0], sr), 20000, 400)),
        ("peak dBFS = -6.0", approx(db(np.abs(x).max()), -6.0, 0.05)),
    ],
}


def _click_starts(x, sr):
    onsets = np.flatnonzero(np.abs(x) > 0.05)
    starts = onsets[np.concatenate(([True], np.diff(onsets) > sr // 10))] / sr
    return len(starts) == 16 and np.allclose(starts, np.arange(16) * 0.5, atol=0.002)


def main(pack: Path):
    failed = 0
    total = 0
    for name, check in CHECKS.items():
        x, sr = sf.read(str(pack / name), always_2d=True)
        for label, ok in check(x, sr):
            total += 1
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name}: {label}")
    print(f"\n{total - failed}/{total} independent checks passed across {len(CHECKS)} files")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
