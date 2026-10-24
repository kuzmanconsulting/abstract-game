# curate-epi-v1 — curate the epigenetics / genome-regulation shortlist (D26, 2026-10-24)

You get a shortlist for the **epigenetics / genome regulation** field: papers from leading journals (see
pipeline/journals.py) that match the field's search terms, already stripped of reviews and of software/database
titles, each with rank, citation count, year, journal, title and the first 400 characters of the abstract, ordered
most-cited first. Pick the **N** papers (N is in your instructions) that best fit the field as defined below. Fit
comes first; among papers that fit, keep the citation order. Prefer breadth across the subfields below over many
papers on one mechanism: if several report the same kind of finding, keep the most-cited few and let others in.

Keep a paper when it reports original findings (data, experiments, analyses) about how the genome is regulated
through chromatin and related mechanisms.

**The field — the mechanism of genome regulation.** Keep findings about: chromatin structure and accessibility,
nucleosome positioning and chromatin remodelling; histone modifications and histone variants (writers, readers,
erasers; H3K27me3, H3K4me3, H3K9me3, H3K27ac and the rest); DNA methylation and demethylation (DNMT, TET, 5mC/5hmC,
CpG islands); Polycomb and Trithorax regulation; enhancers, super-enhancers and cis-regulatory elements and how they
control transcription; 3D genome organisation (topologically associating domains, chromatin loops, compartments,
CTCF, cohesin, Hi-C findings); X-chromosome inactivation and dosage compensation; genomic imprinting; heterochromatin
and position effects; epigenetic inheritance and reprogramming in development and stem cells; single-cell and
genome-wide epigenomics when the result is about a regulatory mechanism.

Drop a paper, with a one-line reason, when it is any of: a software, database, web server, pipeline, benchmark,
resource, atlas or reference-dataset paper whose result is a tool or a dataset rather than a finding (even if the
title does not say so); a review, perspective, guideline, consensus or commentary; a study where chromatin or
methylation is only a readout in a disease/clinical question and the genome-regulation mechanism is incidental; a
paper that merely uses the field's vocabulary (e.g. "epigenetic age" clocks used only as a biomarker); RNA-only
mechanism better placed in the small-RNA field (m6A on mRNA, miRNA biogenesis) unless it is about chromatin or DNA;
a near-duplicate of a paper already kept.

**If your instructions say this is the landmark set:** you are picking the pre-2016 classics that a student of genome
regulation should know — the foundational primary papers. Favour the papers that established a mechanism or a
genome-wide picture: ENCODE's functional-element maps, the first Hi-C and the discovery of topologically associating
domains, DNMT and TET mechanism, Polycomb/PRC2 mechanism and genome-wide targets, X-inactivation and Xist, genomic
imprinting, histone-mark genome maps, enhancer and chromatin-state maps. Breadth across these milestones beats many
papers on one of them. Still drop tools, resources, reviews and off-field papers by the same rules.

## Output

Write exactly this JSON to the output path given in your instructions, nothing else:

```json
{"field": "epi", "prompt_version": "curate-epi-v1",
 "keep": ["<id>", "..."],                  // exactly N ids when the shortlist allows, best fit first
 "drop": [{"id": "<id>", "reason": "<one line>"}, ...],   // every shortlisted id you did not keep
 "notes": "<two or three sentences on what the kept set covers and what it lacks>"}
```

Every id in `keep` and `drop` must come from the shortlist; every shortlisted id must appear in exactly one of the two
lists. Use only Read and Write/Edit; write the file in two or three steps so no single write is very long.
