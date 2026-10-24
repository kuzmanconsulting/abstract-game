# curate-inflammaging-v1 — curate the inflammaging / multi-omics-of-ageing shortlist (D29, 2026-10-24)

You get a shortlist for the **inflammaging / multi-omics of ageing** field: papers from leading journals (see
pipeline/journals.py) that match the field's search terms, already stripped of reviews and of software/database
titles, each with rank, citation count, year, journal, title and the first 400 characters of the abstract, ordered
most-cited first. Pick the **N** papers (N is in your instructions) that best fit the field as defined below. Fit
comes first; among papers that fit, keep the citation order. Prefer breadth across the subfields below over many
papers on one mechanism: if several report the same kind of finding, keep the most-cited few and let others in.

Keep a paper when it reports original findings (data, experiments, analyses) about the molecular biology of
ageing-associated inflammation and cellular ageing — ideally with a genomic, transcriptomic, epigenomic, proteomic,
metabolomic or multi-omic readout, though strong mechanistic cell/molecular findings without an omics layer also
belong.

**The field — the molecular biology of inflammaging and cellular ageing.** Keep findings about: inflammaging itself
(chronic, sterile, low-grade inflammation that rises with age) and its drivers; immunosenescence and immune ageing
(T-cell senescence, thymic involution, myeloid skewing, the ageing immune system by single-cell or omics); cellular
senescence and the senescence-associated secretory phenotype (SASP) — its induction, regulation, surveillance and
clearance; senolytics and senomorphics when the result is a mechanism or an in-vivo/omics effect, not a clinical
trial endpoint; the hallmarks of ageing when tied to inflammation or a molecular readout; biological-age and ageing
"clocks" built from omics (epigenetic/DNA-methylation clocks, proteomic clocks, inflammatory clocks such as iAge,
transcriptomic/metabolomic clocks) when the paper reports how the clock is built or what drives it; inflammasome
(NLRP3) and cGAS–STING / nucleic-acid-sensing pathways in ageing; clonal haematopoiesis and haematopoietic/stem-cell
ageing; single-cell and multi-omic atlases of ageing tissues when the result is a biological finding about ageing or
inflammation (not merely a resource); metabolic and mitochondrial contributions to inflammaging when the readout is
molecular.

Drop a paper, with a one-line reason, when it is any of: a software, database, web server, pipeline, benchmark,
resource, atlas or reference-dataset paper whose result is a tool or a dataset rather than a finding (even if the
title does not say so); a review, perspective, guideline, consensus or commentary; a clinical/epidemiological study
whose result is an association between an inflammatory marker (e.g. CRP, IL-6) and a disease or mortality outcome
with no ageing mechanism and no molecular/omics result — i.e. the ageing-inflammation vocabulary is incidental; a
drug or intervention trial reported by clinical endpoint rather than mechanism; a paper about an age-related disease
(a specific cancer, a single neurodegenerative cohort) where ageing/senescence is only background; an infection or
acute-inflammation study not about ageing; a near-duplicate of a paper already kept.

**If your instructions say this is the landmark set:** you are picking the pre-2016 classics that a student of
inflammaging and cellular ageing should know — the foundational primary papers. Favour the papers that named or
established a concept or mechanism: the original inflamm-aging formulation, the defining work on the SASP and
oncogene-induced/replicative senescence, senescence surveillance and clearance in vivo, the first senolytic
demonstrations, immunosenescence mechanisms, the cell-autonomous drivers of senescence (p16/p21, DNA-damage, SASP
regulation), and the foundational ageing-clock and hallmarks work where it is primary research. Breadth across these
milestones beats many papers on one of them. Still drop tools, resources, reviews and off-field papers by the same
rules.

## Output

Write exactly this JSON to the output path given in your instructions, nothing else:

```json
{"field": "inflammaging", "prompt_version": "curate-inflammaging-v1",
 "keep": ["<id>", "..."],                  // exactly N ids when the shortlist allows, best fit first
 "drop": [{"id": "<id>", "reason": "<one line>"}, ...],   // every shortlisted id you did not keep
 "notes": "<two or three sentences on what the kept set covers and what it lacks>"}
```

Every id in `keep` and `drop` must come from the shortlist; every shortlisted id must appear in exactly one of the two
lists. Use only Read and Write/Edit; write the file in two or three steps so no single write is very long.
