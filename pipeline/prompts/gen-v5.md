# Statement generation — prompt gen-v5 (2026-10-23 20:35)

Changes from gen-v4: the comparative rule below is a requirement, not a preference (D17); the two-sentence cap on
shared evidence; otherwise identical.

Context: items for a reading-comprehension exercise. A reader studies one scientific abstract and judges short
statements about it: does the abstract support the statement, or does it not address it? After answering,
every statement is shown with its label, the passage of the abstract it rests on, and the paper's citation.

For every abstract in the batch file write exactly **four true-to-the-text statements**:

- `supported` × 3 — results the abstract reports (what the data showed), each paraphrased in your own words.
  At least one must be quantitative when the abstract has numbers (a value, a ratio, a percentage, a count,
  a direction with magnitude). **Whenever the abstract states a direction or a comparison** — higher/lower,
  more/fewer, increased/decreased, longer/shorter, larger/smaller, enriched/depleted, gain/loss,
  positive/negative selection, promotes/suppresses, conserved/divergent, earlier/later, … — **at least one
  supported statement must carry that comparative word** (one word from the pair, in a sentence that is
  true as the abstract states it). Skip this only when the abstract makes no comparison at all. Never copy a
  sentence verbatim; change the wording and the sentence structure while keeping the meaning exact.
  Do not let two statements rest on the same sentence of the abstract unless the abstract has no other
  result sentence.
- `not_addressed` × 1 — plausible, on-topic, the kind of claim a reader might assume (a mechanism, a
  clinical implication, a comparison the study did not make, a generalisation to another population), but
  the abstract **neither states nor clearly implies it, and does not refute it either**. If a careful
  reader could argue it is implied or refuted, pick another.

## Rules

- Statements are declarative, ≤ 30 words, self-contained (name groups and measures the way the abstract
  does), no hedges ("might", "could"), no "the authors say". "The study found …" is fine.
- Shuffle the order of the four for each abstract; do not use a fixed pattern.
- Use only the abstract. What the abstract says is the truth here, even if you know otherwise.
- The title is deliberately not given to you; the reader will not see it before answering.
- `evidence` is a **character-exact substring of the abstract text** (copy-paste; at most 300 characters)
  that settles the label. For `not_addressed` quote the closest sentence and say in `note` why it does
  not settle the statement. Join the abstract's sections with a single space when you look for substrings.
- `note` is one sentence the reader sees after answering: why the label is what it is.

## Output

Write **one file**, the output path given in your instructions, valid JSON, nothing else:

```json
{"batch": "gen_41", "prompt_version": "gen-v5",
 "items": [
   {"n": 537, "id": "pmid:12345678",
    "statements": [
      {"k": 1, "label": "supported", "text": "…", "evidence": "…", "note": "…"},
      {"k": 2, "label": "not_addressed", "text": "…", "evidence": "…", "note": "…"},
      {"k": 3, "label": "supported", "text": "…", "evidence": "…", "note": "…"},
      {"k": 4, "label": "supported", "text": "…", "evidence": "…", "note": "…"}
    ]}
 ]}
```

Every item of the batch must appear once, with its `n` and `id` copied from the batch file. Before you
finish, re-read your file with Read and check: valid JSON; 4 statements per item; 3 supported + 1
not_addressed; every `evidence` string occurs verbatim in that abstract's joined text. Fix anything that
fails. Do not write anything else anywhere.
