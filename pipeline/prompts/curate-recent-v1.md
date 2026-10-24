# curate-recent-v1 — curate the recent leading-journal shortlist of one field (D24, 2026-10-23)

You get a shortlist for one field: the 100 most-cited papers of 2023–2026 from the leading-journal list
(pipeline/journals.py) that match the field's search terms, already stripped of reviews and of software/database
titles, each with rank, citation count, year, journal, title and the first 400 characters of the abstract. Pick the
**50** papers that best fit the field as defined below. Fit comes first; among papers that fit, keep the citation
order. Prefer breadth over one topic: if many papers report the same kind of finding, keep the most cited few and
let others in.

Keep a paper when it reports original findings (data, experiments, analyses) in the field.

Drop a paper, with a one-line reason, when it is any of: a software, database, web server, pipeline, benchmark,
resource or reference-genome paper whose result is a tool or a dataset rather than a finding (even if the title does
not say so); a review, perspective, guideline, consensus or commentary; an interventional clinical trial or a
treatment study in which the field's subject is incidental; a paper that merely uses the field's vocabulary; a
near-duplicate of a paper already kept.

## Field definitions

**cfdna — cell-free DNA / liquid biopsy.** Findings about cell-free nucleic acids themselves and their use:
ctDNA detection and quantification, fragmentomics (fragment size, end motifs, nucleosome footprints), methylation
and tissue-of-origin signals, minimal residual disease and early-detection studies, cell-free RNA, non-oncology
cfDNA (prenatal, transplant, sepsis). Observational, diagnostic and cohort studies qualify; drug trials that report a
ctDNA endpoint in passing do not.

**te — transposable elements.** Findings about transposable elements and other mobile genetic elements: TE biology
and regulation, TE-derived regulatory elements and genes, LINE-1/Alu/ERV activity, TE control by small RNAs or
KRAB-ZFPs, TEs in development, disease or genome evolution, CRISPR-associated transposons, TE annotation findings in
new genomes when the result is about the elements. A genome paper that mentions TEs once does not qualify.

**cancergen — cancer genomics.** Findings about the genomes of tumours: somatic mutations, mutational signatures,
copy-number and structural variation, clonal and tumour evolution, cancer genome landscapes, driver discovery,
ecDNA, whole-genome or multi-omics cohorts; functional genomics of cancer genes where the genomic finding is central.
Drug trials, imaging and purely clinical outcome studies do not qualify.

**evogen — evolutionary genomics (molecular evolution).** Findings about how genomes and genes evolve: selection
scans, molecular evolution, phylogenomics and species relationships, speciation genomics, population genomics,
gene duplication and horizontal transfer, experimental evolution, ancient DNA when the result is about evolutionary
history. Human disease genetics and single-species descriptive genomics without an evolutionary result do not
qualify. Tumour evolution belongs to cancergen, not here.

**evodevo — evo-devo / comparative genomics.** Findings about how development and genomes evolve across species:
cis-regulatory and enhancer evolution, gene regulatory networks compared across species, Hox and body-plan
evolution, novelty and co-option, convergent evolution at the genomic level, gene family expansion and loss,
consequences of whole-genome duplication, origin of new genes, comparative genomics that explains a trait. A
reference-genome paper stays only when its reported results are comparative or evolutionary findings. Viral or
pathogen evolution, single-species atlases without a comparison, and human disease genetics do not qualify.

**smallrna — small RNA / RNA biology.** Findings about RNA biology: microRNA, piRNA, siRNA and other small RNAs,
their biogenesis, targeting and roles in development, germline and transposon control; RNA modification (m6A and
others), RNA editing, RNA-binding proteins, alternative splicing, RNA decay, long non-coding and circular RNAs when
the finding is mechanistic. Clinical biomarker studies (circulating miRNA panels, prognostic signatures), RNA
therapeutics trials and RNA-targeting tools (Cas13 and the like) do not qualify.

## Output

Write exactly this JSON to the output path given in your instructions, nothing else:

```json
{"field": "<field key>", "prompt_version": "curate-recent-v1",
 "keep": ["<id>", "..."],                  // exactly 50 ids when the shortlist allows, best fit first
 "drop": [{"id": "<id>", "reason": "<one line>"}, ...],   // every shortlisted id you did not keep
 "notes": "<two or three sentences on what the kept set covers and what it lacks>"}
```

Every id in `keep` and `drop` must come from the shortlist; every shortlisted id must appear in exactly one of the two
lists. Use only Read and Write/Edit; write the file in two or three steps so no single write is very long.
