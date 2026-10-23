# Independent check — prompt check-v1 (2026-10-23)

You are one of three independent checkers for a reading game. For each abstract in the batch file you get the
abstract text and four statements, in random order, **without** the labels the writer intended. Judge every
statement yourself, from the abstract alone, and record your verdict. You never see the other checkers' work.

## Labels

- `supported` — the abstract states this result, or it follows from what the abstract states with no
  additional assumption.
- `contradicted` — the abstract states something that is incompatible with this statement (a different
  direction, group, magnitude, condition, or significance).
- `not_addressed` — the abstract neither states nor clearly implies it, and does not contradict it either.

## How to judge

- Use only the abstract. Do not use your own knowledge of the field; what the abstract says is the truth here.
- Be strict about implication: "clearly implied" means a careful reader could not reasonably read the
  abstract and conclude otherwise. A plausible extrapolation is `not_addressed`.
- Judge the statement as written. If it contains two claims and one is supported while the other is not in
  the abstract, the statement is `not_addressed` unless the unsupported part is contradicted.
- `confidence`: 3 = certain, 2 = fairly sure, 1 = a coin flip.
- `flag` (optional): `ambiguous` when the statement can honestly be read two ways, or when the abstract's own
  wording leaves the point unsettled; `ill_formed` when the statement is ungrammatical, not self-contained
  (refers to something the abstract does not define), or not about the abstract's content. Leave it out
  otherwise. Add a one-sentence `reason` whenever you set a flag.
- `evidence`: the character-exact substring of the abstract (≤ 300 characters) that decided your verdict;
  for `not_addressed` the closest passage. Join the sections with a single space when matching.

## Output

Write **one file**, the output path given in your instructions, valid JSON, nothing else:

```json
{"batch": "check_A_00", "pass": "A", "prompt_version": "check-v1",
 "items": [
   {"n": 0, "id": "pmid:12345678",
    "verdicts": [
      {"j": 1, "label": "supported", "confidence": 3, "evidence": "…"},
      {"j": 2, "label": "not_addressed", "confidence": 2, "evidence": "…", "flag": "ambiguous", "reason": "…"},
      {"j": 3, "label": "contradicted", "confidence": 3, "evidence": "…"},
      {"j": 4, "label": "supported", "confidence": 3, "evidence": "…"}
    ]}
 ]}
```

Every item of the batch must appear once with its `n` and `id`, and every statement `j` must get exactly one
verdict. The label mix is **not** fixed — do not assume two of anything. Before finishing, re-read your file
with Read and check that it is valid JSON and complete. Do not write anything else anywhere.
