# Statement generation — prompt gen-v1 (2026-10-23)

You are writing items for a reading game: a player reads one scientific abstract and judges four statements
about it. For every abstract in the batch file write exactly **four** statements.

## Labels (exactly this mix per abstract)

- `supported` × 2 — a result the abstract reports (what the data showed), paraphrased in your own words.
  At least one of the two must be quantitative when the abstract has numbers (a value, a ratio, a
  percentage, a count, a direction with magnitude). Never copy a sentence verbatim; change the wording and
  the sentence structure while keeping the meaning exact.
- `contradicted` × 1 — take a real result and alter **one** thing precisely so the abstract directly
  contradicts it: the direction of an effect, the comparison group, the population or condition, the
  magnitude by a clearly non-trivial factor, or "significant" ↔ "not significant". It must read as plausible.
  Do not simply insert "not" into a methods sentence; do not alter things the abstract does not state.
- `not_addressed` × 1 — plausible, on-topic, the kind of claim a reader might assume (a mechanism, a
  clinical implication, a comparison the study did not make, a generalisation to another population), but
  the abstract **neither states nor clearly implies it, and does not refute it either**. If a careful
  reader could argue it is implied or refuted, it is not a good item — pick another.

## Rules

- Statements are declarative, ≤ 30 words, self-contained (name groups and measures the way the abstract
  does), no hedges ("might", "could"), no "the authors say". "The study found …" is fine.
- Shuffle the order of the four labels for each abstract; do not use a fixed pattern.
- Use only the abstract. What the abstract says is the truth for the game, even if you know otherwise.
- The title is deliberately not given to you; the player will not see it before answering.
- `evidence` is a **character-exact substring of the abstract text** (copy-paste; at most 300 characters)
  that settles the label. For `not_addressed` quote the closest sentence and say in `note` why it does
  not settle the statement. Join the abstract's sections with a single space when you look for substrings.
- `note` is one sentence a player will read after answering: why the label is what it is.

## Output

Write **one file**, the output path given in your instructions, valid JSON, nothing else:

```json
{"batch": "gen_00", "prompt_version": "gen-v1",
 "items": [
   {"n": 0, "id": "pmid:12345678",
    "statements": [
      {"k": 1, "text": "…", "label": "supported", "evidence": "…", "note": "…"},
      {"k": 2, "text": "…", "label": "not_addressed", "evidence": "…", "note": "…"},
      {"k": 3, "text": "…", "label": "supported", "evidence": "…", "note": "…"},
      {"k": 4, "text": "…", "label": "contradicted", "evidence": "…", "note": "…"}
    ]}
 ]}
```

Every item of the batch must appear once, with its `n` and `id` copied from the batch file. Before you
finish, re-read your file with Read and check: valid JSON; 4 statements per item; label counts 2/1/1;
every `evidence` string occurs verbatim in that abstract's joined text. Fix anything that fails. Do not
write anything else anywhere.
