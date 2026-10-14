# Contributing sounds

New sounds and fixes are welcome, from people and from AI agents. Everything here is public domain (CC0), so every
contribution has to be something that *can* be given away freely.

## Design rules

1. **Synthesize from scratch.** No recordings, samples or excerpts, not even "royalty-free" ones: their licenses
   rarely allow re-licensing as CC0.
2. **Don't recreate named or recognizable sounds.** No "the Mario coin", "the Zelda chime", a console start-up
   sound, a ringtone or a sound trademark, even approximately and even as an homage. Describe each sound by what it
   *does* ("bright metallic chime for collecting an item"), never by what it imitates ("classic coin sound"). If
   you're an AI, watch for this especially: recalling a famous sound while writing a recipe is easy to do without
   noticing. It happened once in this repo (see `sfx-retro-ui/README.md`).
3. **Every sound is a recipe.** Add it to the pack's recipe generator or `recipes.json` as audio-mcp tool calls,
   so anyone can rebuild it and see exactly how it was made.
4. **Pass the checks**:
   ```bash
   python tools/build.py <pack>              # technical checks (clipping, true peak, edges, loudness)
   python tools/similarity_check.py <pack>   # melodic resemblance to famous jingles and sound marks
   python tools/review.py <pack>             # set consistency
   ```
   A similarity match fails the check unless a person has listened and recorded why it's acceptable in
   `REVIEWED`, with a reason in plain words.
5. **A person listens before release.** Tools verify levels, edges and consistency; whether a sound is pleasant and
   fits its purpose is a human judgment. Say in your PR who listened.

## Reference signals

Test signals have to be correct rather than pleasant: add `checks` that pin each file to its intended values,
and, where possible, an independent check in `tools/verify_independent.py` that uses no audio-mcp code.

## Reporting a resemblance

If any sound here reminds you of an existing sound, please open an issue naming both. It will be reviewed by ear
and replaced if the resemblance is real.
