# UI and retro game sounds (DRAFT, not yet published)

**24 short interface and retro-game sound effects**, synthesized from scratch with
[audio-mcp](https://github.com/mshark1/audio-mcp) by an AI agent using only its MCP tools. Intended license: CC0.

**Status: awaiting a human listening review.** The tools can verify the technical side, and every file passes:
no clipping, true peak at or below -1 dBTP, no leading silence, a clean (click-free) ending, and loudness matched
across the set (momentary max loudness -16 LUFS, spread 1.0 dB). Whether a sound is *pleasant* and *fits its name*
is a judgment the tools can't make, so a person has to listen before anything is published.

## Listening checklist

Mark each one **keep**, **tweak** (say what's off: too harsh, too long, wrong mood...) or **drop**.

| File | Intended as | Length | Verdict |
|---|---|---|---|
| `ui_click.wav` | Crisp, very short interface click. | 0.012 s | |
| `ui_tap_soft.wav` | Soft, rounded tap for touch feedback. | 0.05 s | |
| `ui_toggle_on.wav` | Two quick rising notes (G5 to C6): switch on. | 0.13 s | |
| `ui_toggle_off.wav` | Two quick falling notes (C6 to G5): switch off. | 0.13 s | |
| `ui_confirm.wav` | Bright three-note arpeggio (C5 E5 G5): action confirmed. | 0.3 s | |
| `ui_success.wav` | Four-note rising arpeggio ending on a held octave: task complete. | 0.56 s | |
| `ui_error.wav` | Low buzzy descending pair: something went wrong. | 0.33 s | |
| `ui_warning.wav` | Two identical mid beeps: attention needed. | 0.24 s | |
| `ui_notification.wav` | Soft two-partial bell: incoming notification. | 0.7 s | |
| `ui_pop.wav` | Quick upward bubble pop: message or tooltip appears. | 0.08 s | |
| `ui_whoosh.wav` | Airy noise swell: panel slides in. | 0.32 s | |
| `ui_delete.wav` | Crumple-and-drop: item deleted. | 0.19 s | |
| `game_coin.wav` | Classic two-tone coin pickup (B5 to E6). | 0.38 s | |
| `game_jump.wav` | Upward square-wave sweep: player jumps. | 0.18 s | |
| `game_powerup.wav` | Fast rising arpeggio over two octaves: power-up collected. | 0.465 s | |
| `game_laser.wav` | Falling square-wave zap: laser shot. | 0.25 s | |
| `game_explosion.wav` | Low noise blast with a sub thump: explosion. | 0.9 s | |
| `game_hit.wav` | Short crunchy impact: player or enemy takes damage. | 0.11 s | |
| `game_pickup.wav` | Bright upward chirp: item picked up. | 0.2 s | |
| `game_select.wav` | Tiny square blip: menu cursor moves. | 0.035 s | |
| `game_over.wav` | Slow descending phrase with a wobbling last note: game over. | 1.74 s | |
| `game_level_complete.wav` | Short triumphant fanfare: level complete. | 1.46 s | |
| `game_footstep.wav` | Muffled retro footstep. | 0.07 s | |
| `game_teleport.wav` | Warbling upward sweep: teleport or portal. | 0.6 s | |

Things to listen for: harshness or fizz in the bright sounds; whether `ui_click` (deliberately quieter, 12 ms) is
too faint; whether the arpeggios feel cheerful rather than cheesy; and whether `game_explosion` has enough weight.

## Rebuild

```bash
python sfx-retro-ui/make_recipes.py && python tools/build.py sfx-retro-ui
python tools/review.py sfx-retro-ui      # set-level loudness survey + one-line description of each sound
```
