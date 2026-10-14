# Evaluating models on the perception benchmark

Two ways to run the same 193 items, so the results can be compared directly:

- **A. Native audio model**: the model hears the audio itself (Gemini, GPT-4o audio, Qwen-Omni, Audio Flamingo, ...).
- **B. Tool-using LLM agent**: a text LLM that can't hear, but can call [audio-mcp](https://github.com/mshark1/audio-mcp)
  tools on the file.

Both produce a predictions file, one JSON object per line, which `score.py` grades:

```json
{"id": "pitch.note_name.01", "answer": "E2"}
```

No model results are reported in this repository. The only results here are the random baseline and the rule-based
tool ceiling (see README.md).

## Rules for a fair run

1. **Hide the file names.** Several reference files have their answer in their name (`tone_A4_440Hz_-12dBFS.wav`).
   Copy each item's audio to an opaque name (`clip_001.wav`) or send the raw bytes, and never show the path or the
   `provenance` and `answer` fields to the model. `baselines/audio_mcp_tools.py` shows one way to do the copying.
2. **One item per conversation**, no shared context between items, no few-shot examples taken from `items.jsonl`.
3. **Two-clip items** (`audio` has two files: tasks `pitch.higher` and `loudness.louder`): present clip A, then
   clip B. Either send them as two separate audio inputs, labelled "Clip A" and "Clip B" in the text, or
   concatenate them with 0.5 s of silence between them (SonicBench's convention for comparisons) and say so in
   the prompt. Report which method you used.
4. **Don't resample or re-encode** if you can avoid it. If the API forces it (many accept only 16 kHz or compressed
   audio), say so: items about sample peak, true peak, clipping, DC offset and loop seams depend on the exact
   samples, and a lossy encode can change their answers. Such results aren't comparable with lossless runs.
5. Record the model name and version, the date, temperature (0 recommended), and the number of retries for answers
   that couldn't be parsed (at most one, with the reminder "Answer only in the requested format").

## A. Native audio model: prompt templates

Use one template per answer type. `{question}` is the item's `question` field, verbatim; it already states the
allowed range or options.

**System / preamble (all items)**

```
You are taking a listening test. Listen to the audio carefully and answer the question.
Reply with the answer only, in the exact format requested, with no explanation.
```

**choice** (`answer_type: "choice"`, options in `options`)

```
{question}
Options: {options joined with " | "}
Answer with exactly one of the options.
```

Expected output: one option, e.g. `B`, `yes`, `60 Hz`, `near zero`, `single note`.

**numeric** (`answer_type: "numeric"`, unit in `unit`)

```
{question}
Answer with a single number in {unit}.
```

Expected output: a number, optionally with its unit: `-23.0`, `-23 LUFS`, `440 Hz`, `1.5`.

**note** (`answer_type: "note"`)

```
{question}
Answer with one note name only.
```

Expected output: `F#3` (sharps or flats both fine: `Gb3` scores the same).

**note_sequence** (`answer_type: "note_sequence"`)

```
{question}
Answer with the note names only, separated by spaces.
```

Expected output: `E4 D4 C4 D4 E4 E4 E4`.

### What the scorer accepts

`bench.py` normalizes answers before grading, so harmless formatting doesn't cost points:

| Answer type | Accepted | Scored as |
|---|---|---|
| choice | case and spacing ignored; `yes/no` also `true/false`; A/B also `first/second`, `1/2`; a lone letter `a`, `b`, `c` picks options by position; a bare number matches the one option containing it (`60` gives `60 Hz`) | exact match with the answer |
| numeric | first number in the text; `kHz` converted to Hz; `ms` converted to s; Unicode minus signs; for Hz items a note name (`A4`) is converted to its frequency | within the item's `tolerance` (`abs` in the unit, or `rel` as a fraction of the answer) |
| note | scientific pitch notation, `#`/`b`/`♯`/`♭`, any case; a frequency with `Hz` is mapped to the nearest note | same MIDI note (enharmonics equal; octave matters) |
| note_sequence | a list, or a string separated by spaces, commas, `-` or arrows | per-note position match: correct positions / max(true length, answer length) |

Anything that can't be parsed scores 0. Count the unparseable answers and report them separately, as SonicBench does
for abstentions.

## B. Tool-using LLM agent with audio-mcp

Give the agent the audio-mcp server (`pip install "audio-mcp>=0.2.0"`, then run `python -m audio_mcp` over MCP stdio) and
the blinded file path(s). Don't give it any other audio tools, and don't let it read the repository's manifests or
`items.jsonl`.

```
You can't hear audio directly, but you have audio analysis tools (audio-mcp). Use them to answer a question about
the audio file(s) below. When you are done, reply with the answer only, in the exact format requested.

File(s): {blinded path, or "Clip A: {path_a}" and "Clip B: {path_b}"}
{question}
{the same answer-format line as in section A}
```

Log every tool call (name, arguments, and the result size) along with the final answer. Report:

- the score (from `score.py`), next to the native-audio score on the same items;
- the number of tool calls per item, and which tools were used;
- items where the agent's answer differs from the **tool ceiling** (`baselines/results/audio_mcp_tools.jsonl`).
  Where the ceiling is right and the agent is wrong, the agent misread or misused the tools. Where both are wrong,
  the tool itself is the limit (see "Tool misses" in README.md).

## Scoring

```bash
python perception-benchmark/score.py my_predictions.jsonl --name "model X, native audio" --json my_score.json
```

The table shows each category and task, with the analytic chance level next to each score.
