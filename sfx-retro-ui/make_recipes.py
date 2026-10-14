"""Generate recipes.json for the UI and retro-game sound effects pack.

Design rule (see CONTRIBUTING.md): describe each sound by what it does, never by what it imitates, and don't
recreate named or recognizable sounds. The first coin design broke this rule (it reused the Super Mario Bros. coin's
notes and shape) and was replaced. Check with tools/similarity_check.py; a person listens before release.

Each sound is a synth spec (the design) plus the same finishing chain and technical checks. Run:
    python sfx-retro-ui/make_recipes.py && python tools/build.py sfx-retro-ui
"""

import json
from pathlib import Path

SR = 48000

# name -> (description, layers, extra spec keys)
SOUNDS = {
    # ---- UI ----
    "ui_click": ("Crisp, very short interface click.", [
        {"wave": "noise", "duration": 0.012, "highpass": 2500, "envelope": {"attack": 0.0005, "release": 0.011}},
        {"wave": "sine", "freq": 2200, "duration": 0.012, "gain_db": -8, "envelope": {"attack": 0.0005, "release": 0.011}}], {}),
    "ui_tap_soft": ("Soft, rounded tap for touch feedback.", [
        {"wave": "sine", "freq": 880, "freq_end": 700, "duration": 0.05, "envelope": {"attack": 0.001, "release": 0.045}}], {}),
    "ui_toggle_on": ("Two quick rising notes (G5 to C6): switch on.", [
        {"wave": "triangle", "sequence": [["G5", 0.05], ["C6", 0.08]], "envelope": {"attack": 0.002, "release": 0.03}}], {}),
    "ui_toggle_off": ("Two quick falling notes (C6 to G5): switch off.", [
        {"wave": "triangle", "sequence": [["C6", 0.05], ["G5", 0.08]], "envelope": {"attack": 0.002, "release": 0.03}}], {}),
    "ui_confirm": ("Bright three-note arpeggio (C5 E5 G5): action confirmed.", [
        {"wave": "triangle", "sequence": [["C5", 0.06], ["E5", 0.06], ["G5", 0.18]], "envelope": {"attack": 0.002, "decay": 0.04, "sustain": 0.6, "release": 0.08}},
        {"wave": "sine", "sequence": [["C6", 0.06], ["E6", 0.06], ["G6", 0.18]], "gain_db": -12, "envelope": {"attack": 0.002, "release": 0.08}}], {}),
    "ui_success": ("Four-note rising arpeggio ending on a held octave: task complete.", [
        {"wave": "triangle", "sequence": [["C5", 0.07], ["E5", 0.07], ["G5", 0.07], ["C6", 0.35]], "envelope": {"attack": 0.002, "decay": 0.05, "sustain": 0.5, "release": 0.2}},
        {"wave": "sine", "sequence": [["C6", 0.07], ["E6", 0.07], ["G6", 0.07], ["C7", 0.35]], "gain_db": -14, "envelope": {"attack": 0.002, "release": 0.2}}], {}),
    "ui_error": ("Low buzzy descending pair: something went wrong.", [
        {"wave": "square", "sequence": [["A3", 0.12], ["rest", 0.03], ["F3", 0.18]], "lowpass": 1800, "envelope": {"attack": 0.003, "release": 0.05}}], {}),
    "ui_warning": ("Two identical mid beeps: attention needed.", [
        {"wave": "square", "sequence": [["E5", 0.09], ["rest", 0.06], ["E5", 0.09]], "lowpass": 3500, "gain_db": -3, "envelope": {"attack": 0.002, "release": 0.03}}], {}),
    "ui_notification": ("Soft two-partial bell: incoming notification.", [
        {"wave": "sine", "freq": "E6", "duration": 0.7, "envelope": {"attack": 0.002, "decay": 0.68, "sustain": 0.0, "release": 0.01}},
        {"wave": "sine", "freq": "B6", "duration": 0.45, "gain_db": -9, "envelope": {"attack": 0.002, "decay": 0.43, "sustain": 0.0, "release": 0.01}},
        {"wave": "sine", "freq": "E7", "duration": 0.2, "gain_db": -18, "envelope": {"attack": 0.002, "decay": 0.19, "sustain": 0.0, "release": 0.01}}], {}),
    "ui_pop": ("Quick upward bubble pop: message or tooltip appears.", [
        {"wave": "sine", "freq": 500, "freq_end": 1300, "duration": 0.08, "envelope": {"attack": 0.001, "release": 0.05}}], {}),
    "ui_whoosh": ("Airy noise swell: panel slides in.", [
        {"wave": "pink", "duration": 0.32, "highpass": 700, "lowpass": 7000, "envelope": {"attack": 0.15, "decay": 0.0, "sustain": 1, "release": 0.17}}], {}),
    "ui_delete": ("Crumple-and-drop: item deleted.", [
        {"wave": "noise", "duration": 0.09, "lowpass": 3000, "envelope": {"attack": 0.002, "release": 0.08}},
        {"wave": "sine", "freq": 420, "freq_end": 130, "start": 0.03, "duration": 0.16, "gain_db": -2, "envelope": {"attack": 0.003, "release": 0.1}}], {}),
    # ---- retro game ----
    "game_coin": ("Bright metallic chime: coin or gem collected. One struck tone with a non-harmonic bell partial "
                  "and a short upward glint (deliberately not a two-note square-wave melody).", [
        {"wave": "sine", "freq": 1480, "duration": 0.45, "envelope": {"attack": 0.001, "decay": 0.44, "sustain": 0.0, "release": 0.01}},
        {"wave": "sine", "freq": 4085, "duration": 0.18, "gain_db": -11, "envelope": {"attack": 0.001, "decay": 0.17, "sustain": 0.0, "release": 0.01}},
        {"wave": "sine", "freq": 2960, "duration": 0.25, "gain_db": -15, "envelope": {"attack": 0.001, "decay": 0.24, "sustain": 0.0, "release": 0.01}},
        {"wave": "triangle", "freq": 1100, "freq_end": 1480, "duration": 0.025, "gain_db": -9, "envelope": {"attack": 0.001, "release": 0.02}}], {}),
    "game_jump": ("Upward square-wave sweep: player jumps.", [
        {"wave": "square", "freq": 180, "freq_end": 620, "duration": 0.18, "lowpass": 5000, "envelope": {"attack": 0.002, "release": 0.07}}], {}),
    "game_powerup": ("Fast rising arpeggio over two octaves: power-up collected.", [
        {"wave": "triangle", "sequence": [[n, 0.045] for n in ("C5", "E5", "G5", "C6", "E6", "G6", "C7")] + [["E7", 0.15]], "envelope": {"attack": 0.002, "release": 0.02}},
        {"wave": "square", "sequence": [[n, 0.045] for n in ("C4", "E4", "G4", "C5", "E5", "G5", "C6")] + [["E6", 0.15]], "lowpass": 3000, "gain_db": -14, "envelope": {"attack": 0.002, "release": 0.02}}], {}),
    "game_laser": ("Falling square-wave zap: laser shot.", [
        {"wave": "square", "freq": 1800, "freq_end": 180, "duration": 0.25, "lowpass": 6000, "envelope": {"attack": 0.001, "release": 0.1}}], {}),
    "game_explosion": ("Low noise blast with a sub thump: explosion.", [
        {"wave": "brown", "duration": 0.9, "lowpass": 2000, "envelope": {"attack": 0.002, "decay": 0.85, "sustain": 0.0, "release": 0.04}},
        {"wave": "noise", "duration": 0.15, "lowpass": 5000, "gain_db": -8, "envelope": {"attack": 0.001, "release": 0.14}},
        {"wave": "sine", "freq": 110, "freq_end": 35, "duration": 0.5, "gain_db": -3, "envelope": {"attack": 0.002, "release": 0.3}}], {}),
    "game_hit": ("Short crunchy impact: player or enemy takes damage.", [
        {"wave": "noise", "duration": 0.07, "lowpass": 4000, "envelope": {"attack": 0.001, "release": 0.06}},
        {"wave": "square", "freq": 320, "freq_end": 110, "duration": 0.11, "lowpass": 2500, "gain_db": -4, "envelope": {"attack": 0.001, "release": 0.05}}], {}),
    "game_pickup": ("Bright upward chirp: item picked up.", [
        {"wave": "sine", "freq": 800, "freq_end": 1700, "duration": 0.09, "envelope": {"attack": 0.001, "release": 0.04}},
        {"wave": "triangle", "freq": "E6", "start": 0.08, "duration": 0.12, "gain_db": -4, "envelope": {"attack": 0.002, "release": 0.09}}], {}),
    "game_select": ("Tiny square blip: menu cursor moves.", [
        {"wave": "square", "freq": 990, "duration": 0.035, "lowpass": 5000, "gain_db": -2, "envelope": {"attack": 0.001, "release": 0.015}}], {}),
    "game_over": ("Falling minor arpeggio that slows down, the last note sagging: game over "
                  "(deliberately not the chromatic 'sad trombone' slide).", [
        {"wave": "triangle", "sequence": [["A4", 0.22], ["E4", 0.26], ["C4", 0.32]], "envelope": {"attack": 0.004, "decay": 0.08, "sustain": 0.6, "release": 0.08}},
        {"wave": "triangle", "freq": "A3", "freq_end": 207.65, "start": 0.8, "duration": 0.85, "envelope": {"attack": 0.004, "decay": 0.3, "sustain": 0.4, "release": 0.4}},
        {"wave": "sine", "sequence": [["A3", 0.22], ["E3", 0.26], ["C3", 0.32], ["A2", 0.85]], "gain_db": -10, "envelope": {"attack": 0.004, "release": 0.2}}], {}),
    "game_level_complete": ("Short triumphant fanfare: level complete.", [
        {"wave": "triangle", "sequence": [["C5", 0.12], ["E5", 0.12], ["G5", 0.12], ["C6", 0.24], ["G5", 0.12], ["C6", 0.5]], "envelope": {"attack": 0.003, "decay": 0.05, "sustain": 0.7, "release": 0.1}},
        {"wave": "square", "sequence": [["C4", 0.36], ["G4", 0.36], ["C5", 0.74]], "lowpass": 2000, "gain_db": -12, "envelope": {"attack": 0.003, "release": 0.15}}], {}),
    "game_footstep": ("Muffled retro footstep.", [
        {"wave": "brown", "duration": 0.07, "lowpass": 900, "envelope": {"attack": 0.002, "release": 0.06}},
        {"wave": "noise", "duration": 0.02, "highpass": 2000, "gain_db": -16, "envelope": {"attack": 0.001, "release": 0.018}}], {}),
    "game_teleport": ("Warbling upward sweep: teleport or portal.", [
        {"wave": "sine", "freq": 200, "freq_end": 2400, "duration": 0.6, "vibrato": {"rate_hz": 28, "depth_cents": 180}, "envelope": {"attack": 0.01, "release": 0.25}},
        {"wave": "triangle", "freq": 400, "freq_end": 4800, "duration": 0.6, "gain_db": -12, "vibrato": {"rate_hz": 28, "depth_cents": 180}, "envelope": {"attack": 0.01, "release": 0.25}}], {}),
}

# Match perceived loudness (momentary max, defined for any length) without ever limiting: sounds too short or
# peaky to reach the target stop at the peak ceiling instead, which keeps clicks and blips light and undistorted.
FINISH = [
    {"op": "fade_out", "seconds": 0.004},
    {"op": "normalize_lufs", "lufs": -16, "measure": "momentary_max", "ceiling_db": -1.0},
]
CHECKS = [
    {"tool": "audio_analyze", "field": "levels.clipped_samples", "expect": 0},
    {"tool": "audio_analyze", "field": "levels.true_peak_dbtp", "max": -1.0},
    {"tool": "audio_analyze", "field": "levels.lufs_momentary_max", "max": -15.9},
    {"tool": "audio_analyze", "field": "silence.leading_s", "max": 0.005},
    {"tool": "audio_analyze", "field": "edges.end_amplitude", "max": 0.01},
]


def main():
    assets = []
    for name, (desc, layers, extra) in SOUNDS.items():
        # Seed from the name so every rebuild is identical (Python's hash() is randomized per run).
        spec = {"sample_rate": SR, "seed": sum(map(ord, name)), "layers": layers, **extra}
        tmp = "{tmp}/" + name + ".wav"
        assets.append({
            "file": f"{name}.wav",
            "description": desc,
            "steps": [
                {"tool": "audio_synthesize", "args": {"spec": spec, "output": tmp, "overwrite": True}},
                {"tool": "audio_process", "args": {"path": tmp, "operations": FINISH, "output": "{out}", "overwrite": True}},
            ],
            "checks": CHECKS,
        })
    recipes = {
        "pack": {"name": "audio-mcp UI and retro game sounds", "version": "0.1.0-draft",
                 "description": "Short interface and retro game sound effects, synthesized from scratch with audio-mcp.",
                 "made_with": "https://github.com/mshark1/audio-mcp"},
        "assets": assets,
    }
    Path(__file__).with_name("recipes.json").write_text(json.dumps(recipes, indent=1) + "\n", encoding="utf-8")
    print(f"{len(assets)} recipes written")


if __name__ == "__main__":
    main()
