# UI and retro game sounds

**24 short interface and retro-game sound effects**, synthesized from scratch with
[audio-mcp](https://github.com/mshark1/audio-mcp) by an AI agent using only its MCP tools. Public domain (CC0).

Every file passes the same technical checks: no clipping, true peak at or below -1 dBTP, no leading silence, a
clean (click-free) ending, and loudness matched across the set (momentary max loudness -16 LUFS; very short clicks
and taps sit lower by design rather than being limited). A person listened to the whole set before release.

| File | What it is | Length |
|---|---|---|
| `ui_click.wav` | Crisp, very short interface click. | 0.012 s |
| `ui_tap_soft.wav` | Soft, rounded tap for touch feedback. | 0.05 s |
| `ui_toggle_on.wav` | Two quick rising notes (G5 to C6): switch on. | 0.13 s |
| `ui_toggle_off.wav` | Two quick falling notes (C6 to G5): switch off. | 0.13 s |
| `ui_confirm.wav` | Bright three-note arpeggio (C5 E5 G5): action confirmed. | 0.3 s |
| `ui_success.wav` | Four-note rising arpeggio ending on a held octave: task complete. | 0.56 s |
| `ui_error.wav` | Low buzzy descending pair: something went wrong. | 0.33 s |
| `ui_warning.wav` | Two identical mid beeps: attention needed. | 0.24 s |
| `ui_notification.wav` | Soft two-partial bell: incoming notification. | 0.7 s |
| `ui_pop.wav` | Quick upward bubble pop: message or tooltip appears. | 0.08 s |
| `ui_whoosh.wav` | Airy noise swell: panel slides in. | 0.32 s |
| `ui_delete.wav` | Crumple-and-drop: item deleted. | 0.19 s |
| `game_coin.wav` | Bright metallic chime: coin or gem collected. One struck tone with a non-harmonic bell partial and a short upward glint (deliberately not a two-note square-wave melody). | 0.45 s |
| `game_jump.wav` | Upward square-wave sweep: player jumps. | 0.18 s |
| `game_powerup.wav` | Fast rising arpeggio over two octaves: power-up collected. | 0.465 s |
| `game_laser.wav` | Falling square-wave zap: laser shot. | 0.25 s |
| `game_explosion.wav` | Low noise blast with a sub thump: explosion. | 0.9 s |
| `game_hit.wav` | Short crunchy impact: player or enemy takes damage. | 0.11 s |
| `game_pickup.wav` | Bright upward chirp: item picked up. | 0.2 s |
| `game_select.wav` | Tiny square blip: menu cursor moves. | 0.035 s |
| `game_over.wav` | Falling minor arpeggio that slows down, the last note sagging: game over (deliberately not the chromatic 'sad trombone' slide). | 1.65 s |
| `game_level_complete.wav` | Short triumphant fanfare: level complete. | 1.46 s |
| `game_footstep.wav` | Muffled retro footstep. | 0.07 s |
| `game_teleport.wav` | Warbling upward sweep: teleport or portal. | 0.6 s |

## Provenance: how original are these?

These sounds were designed by an AI and synthesized from simple parameters (oscillators, noise, envelopes and
filters). No recordings or samples were used, and each sound's exact recipe is in `recipes.json`. That rules out
copied audio, but not *resemblance*: a recipe can still recreate a famous sound. Here's what we did about that.

- **One design was withdrawn for resembling a famous sound.** The first coin sound used the same two notes (B5 to
  E6), waveform and shape as the Super Mario Bros. coin. The AI that designed it had recalled that sound while
  writing the recipe. It was replaced with an original single-strike metallic chime. A first game-over sound used
  the chromatic "sad trombone" slide; that's a widely used trope rather than anyone's signature sound, but it was
  also replaced, with a falling minor arpeggio.
- **Every melodic sound is checked against famous jingles and sound trademarks** by note sequence
  (`tools/similarity_check.py`): game sounds such as Mario, Zelda and Final Fantasy, sound marks such as NBC and
  Intel, and common tropes. The withdrawn designs are kept in the check as a test that it catches them. One
  reviewed overlap remains: `game_powerup`'s rising arpeggio shares a four-note shape with the public-domain
  "Charge!" bugle call. The reasoning is recorded in the script.
- **Limits:** the reference list was written from memory and covers only famous sounds, and the check compares
  melodies, not rhythm or timbre. The non-melodic sounds (sweeps, noise bursts, strikes) are built from generic
  synthesis idioms.

**If a sound here reminds you of a specific existing sound, please open an issue.** We'll review it and replace it
if there's a real resemblance.

## Rebuild

```bash
python sfx-retro-ui/make_recipes.py && python tools/build.py sfx-retro-ui
python tools/review.py sfx-retro-ui            # loudness consistency survey + one-line description of each sound
python tools/similarity_check.py sfx-retro-ui  # melodic resemblance check
```
