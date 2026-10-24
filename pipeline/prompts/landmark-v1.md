# landmark-v1 — curate the landmark papers of one field

You get a shortlist for one field: the most-cited journal papers of 2016–2026 that mention the field's terms,
already stripped of reviews and of titles that look like software or databases, with rank, citation count, year,
journal, title and the first 400 characters of the abstract. Pick the **40** papers a researcher in this field
would call the important primary research papers of the decade — the ones a reading-practice corpus for this
field should contain.

Keep a paper when it reports original findings (data, experiments, analyses) in the field.

Drop a paper, with a one-line reason, when it is any of:
- a software, database, web server, pipeline, benchmark, resource or reference-genome paper (the result is a tool or a
  dataset, not a finding about the field) — even if its title does not say so;
- a review, perspective, guideline, consensus or commentary;
- off the field: a paper that merely uses the field's vocabulary (a cancer immunotherapy trial that mentions ctDNA
  in passing is not a cfDNA paper; a CRISPR tool that edits RNA is not a small-RNA biology paper; a genome assembly
  that mentions transposable elements once is not a TE paper);
- a near-duplicate of a paper you already kept (the same consortium's follow-up with the same result).

Within the field, prefer breadth over one topic: if ten papers report the same kind of finding, keep the two or
three most cited and let others in. Citation count is the default order; depart from it only for the reasons above.

Output — write exactly this JSON to the output path, nothing else:

```json
{"field": "<field key>", "prompt_version": "landmark-v1",
 "keep": ["<id>", "..."],                 // exactly 40 ids when the shortlist allows, in the order you would rank them
 "drop": [{"id": "<id>", "reason": "<one line>"}, ...],   // every shortlisted id you did not keep
 "notes": "<two or three sentences on what the kept set covers and what it lacks>"}
```

Every id in `keep` and `drop` must come from the shortlist; every shortlisted id must appear in exactly one of the
two lists. Use only Read and Write.
