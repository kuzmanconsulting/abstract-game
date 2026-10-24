# Statement generation — prompt gen-v2 (2026-10-23, replaces gen-v1 for every batch generated after 14:40)

Context: this is a **reading-comprehension game**. A player reads one scientific abstract and judges four short
statements about it; right after answering, every statement is shown with its label, the passage of the
abstract that decides it, and the paper's citation. Nothing you write is presented as a finding — the one
"contradicted" item is a deliberately altered version of a real result and is always displayed with the
label and the correction. You never write a false sentence yourself: for the altered item you write the
**true** paraphrase and a one-phrase **edit instruction**; the pipeline applies the edit.

For every abstract in the batch file write exactly **four** statements.

## Labels (exactly this mix per abstract)

- `supported` × 2 — a result the abstract reports (what the data showed), paraphrased in your own words.
  At least one of the two must be quantitative when the abstract has numbers (a value, a ratio, a
  percentage, a count, a direction with magnitude). Never copy a sentence verbatim; change the wording and
  the sentence structure while keeping the meaning exact.
- `contradicted` × 1 — give `basis`: a true paraphrase of one real result (same rules as `supported`), and
  `alter`: `{"from": "<a phrase that occurs exactly once in basis>", "to": "<replacement>", "kind": "<direction|group|magnitude|condition|significance>"}`.
  The replacement must make the sentence incompatible with the abstract while keeping it grammatical and
  plausible (e.g. "higher" → "lower"; "in responders" → "in non-responders"; "by 2.3-fold" → "by 9-fold";
  "significantly" → "not significantly"). Do not write the altered sentence anywhere. Do not insert "not"
  into a methods sentence; alter a result.
- `not_addressed` × 1 — plausible, on-topic, the kind of claim a reader might assume (a mechanism, a
  clinical implication, a comparison the study did not make, a generalisation to another population), but
  the abstract **neither states nor clearly implies it, and does not refute it either**. If a careful
  reader could argue it is implied or refuted, pick another.

## Rules

- Statements are declarative, ≤ 30 words, self-contained (name groups and measures the way the abstract
  does), no hedges ("might", "could"), no "the authors say". "The study found …" is fine.
- Shuffle the order of the four labels for each abstract; do not use a fixed pattern.
- Use only the abstract. What the abstract says is the truth for the game, even if you know otherwise.
- The title is deliberately not given to you; the player will not see it before answering.
- `evidence` is a **character-exact substring of the abstract text** (copy-paste; at most 300 characters)
  that settles the label. For `not_addressed` quote the closest sentence and say in `note` why it does
  not settle the statement. Join the abstract's sections with a single space when you look for substrings.
- `note` is one sentence a player will read after answering: why the label is what it is. For the
  altered item, state what the abstract actually reports (the `basis` wording is fine).

## Output

Write **one file**, the output path given in your instructions, valid JSON, nothing else:

```json
{"batch": "gen_00a", "prompt_version": "gen-v2",
 "purpose": "reading-comprehension items; the contradicted item is composed by the pipeline from basis+alter and always shown with its label",
 "items": [
   {"n": 0, "id": "pmid:12345678",
    "statements": [
      {"k": 1, "label": "supported", "text": "…", "evidence": "…", "note": "…"},
      {"k": 2, "label": "not_addressed", "text": "…", "evidence": "…", "note": "…"},
      {"k": 3, "label": "contradicted", "basis": "…", "alter": {"from": "…", "to": "…", "kind": "direction"}, "evidence": "…", "note": "…"},
      {"k": 4, "label": "supported", "text": "…", "evidence": "…", "note": "…"}
    ]}
 ]}
```

Every item of the batch must appear once, with its `n` and `id` copied from the batch file. Before you
finish, re-read your file with Read and check: valid JSON; 4 statements per item; label counts 2/1/1;
every `evidence` string occurs verbatim in that abstract's joined text; every `alter.from` occurs exactly
once in its `basis`. Fix anything that fails. Do not write anything else anywhere.
