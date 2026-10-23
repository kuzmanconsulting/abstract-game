# Statement generation — prompt gen-v3 (2026-10-23 14:45, replaces gen-v2)

Context: a **reading-comprehension game**. A player reads one scientific abstract and judges four short
statements about it; right after answering, every statement is shown with its label, the passage of the
abstract that decides it, and the paper's citation.

**You write only true statements.** Every statement you produce is either a faithful paraphrase of a result
the abstract reports, or a plausible claim the abstract does not address. The game's one "contradicted"
item per abstract is produced later by the pipeline, mechanically, by swapping one direction word in a true
statement you mark for it (higher ↔ lower, increased ↔ decreased, …). You never write, describe or
suggest an altered version.

For every abstract in the batch file write exactly **four** statements:

- `supported` × 3 — results the abstract reports (what the data showed), paraphrased in your own words.
  At least one must be quantitative when the abstract has numbers (a value, a ratio, a percentage, a count,
  a direction with magnitude). Never copy a sentence verbatim; change the wording and the sentence
  structure while keeping the meaning exact.
  **Exactly one** of the three carries `"flip": true`. That statement must contain **exactly one** word
  from this list, used in its directional sense, and no other word from the list:
  `higher, lower, greater, smaller, increased, decreased, increase, decrease, increases, decreases,
  longer, shorter, enriched, depleted, upregulated, downregulated, overexpressed, underexpressed,
  positively, negatively, improved, worsened, elevated, reduced, faster, slower, earlier, later,
  hypermethylated, hypomethylated, hypermethylation, hypomethylation, superior, inferior,
  outperformed, underperformed, gained, lost, more, fewer, above, below`.
  Choose a statement where swapping that one word for its opposite would produce a claim the abstract
  clearly contradicts (so avoid words whose swap would still be true or merely unaddressed).
- `not_addressed` × 1 — plausible, on-topic, the kind of claim a reader might assume (a mechanism, a
  clinical implication, a comparison the study did not make, a generalisation to another population), but
  the abstract **neither states nor clearly implies it, and does not refute it either**. If a careful
  reader could argue it is implied or refuted, pick another.

## Rules

- Statements are declarative, ≤ 30 words, self-contained (name groups and measures the way the abstract
  does), no hedges ("might", "could"), no "the authors say". "The study found …" is fine.
- Shuffle the order of the four for each abstract; do not use a fixed pattern.
- Use only the abstract. What the abstract says is the truth for the game, even if you know otherwise.
- The title is deliberately not given to you; the player will not see it before answering.
- `evidence` is a **character-exact substring of the abstract text** (copy-paste; at most 300 characters)
  that settles the label. For `not_addressed` quote the closest sentence and say in `note` why it does
  not settle the statement. Join the abstract's sections with a single space when you look for substrings.
- `note` is one sentence a player will read after answering: why the label is what it is. For the flip
  statement, state the result in the abstract's own terms (it is shown next to the altered version).

## Output

Write **one file**, the output path given in your instructions, valid JSON, nothing else:

```json
{"batch": "gen_12a", "prompt_version": "gen-v3",
 "items": [
   {"n": 420, "id": "pmid:12345678",
    "statements": [
      {"k": 1, "label": "supported", "text": "…", "evidence": "…", "note": "…"},
      {"k": 2, "label": "not_addressed", "text": "…", "evidence": "…", "note": "…"},
      {"k": 3, "label": "supported", "flip": true, "text": "…", "evidence": "…", "note": "…"},
      {"k": 4, "label": "supported", "text": "…", "evidence": "…", "note": "…"}
    ]}
 ]}
```

Every item of the batch must appear once, with its `n` and `id` copied from the batch file. Before you
finish, re-read your file with Read and check: valid JSON; 4 statements per item; 3 supported (exactly one
with `"flip": true`, containing exactly one list word) + 1 not_addressed; every `evidence` string occurs
verbatim in that abstract's joined text. Fix anything that fails. Do not write anything else anywhere.
