# curate-d23-v1 — curate one shortlist for the D23 additions (2026-10-23 21:13)

You get a shortlist for one query field: papers from leading journals (2016–2026) that match the field's search terms,
already stripped of reviews and of software/database titles, each with id, year, journal, title and the first 400
characters of the abstract. Pick the **N** papers (N is in your instructions) that best fit the field **as the owner of
the corpus defines it** below. Fit to the definition comes first; among papers that fit equally, prefer the better-known
result (citations are given when the shortlist is citation-ranked) and keep a spread of years and organisms.

## Field definitions

**rnadev — small RNA in development and transposon control** ("pure biology papers: piRNA, miRNA in transposon
regulation, in development and so on"). Keep papers whose findings are about the small-RNA pathways themselves:
piRNA/PIWI biology and piRNA biogenesis; transposon silencing by piRNAs, siRNAs, RdDM or KRAB-ZFPs; endo-siRNAs;
microRNAs in embryonic development, stem cells, differentiation, germline or the maternal-to-zygotic transition
(let-7, lin-4, miR-430 …); Argonaute/Dicer/Drosha mechanism; plant small RNAs (phasiRNA, mobile sRNAs, cross-kingdom
RNAi); RNAi inheritance. Drop: cancer or any clinical/patient/biomarker study; exosomal miRNAs in disease; CRISPR or
other genome-editing tools and method papers; RNA-targeting technologies (Cas13 and the like); resources; papers where
the small RNA is incidental to a developmental or chromatin finding.

**evodevo — evo-devo / comparative genomics** ("evolution… but like evo-devo evolution, comparative genomics"). Keep
papers whose findings are about how development and genomes evolve: cis-regulatory and enhancer evolution, gene
regulatory networks compared across species, Hox and body-plan evolution, evolutionary novelty and co-option,
convergent evolution at the genomic level, gene family expansion and loss, consequences of whole-genome duplication,
origin of new genes, comparative genomics across lineages that explains a trait. A reference-genome paper stays only
when its reported results are comparative/evolutionary findings rather than the assembly itself. Drop: SARS-CoV-2 and
other viral or pathogen evolution; databases, genome browsers, assemblies and methods; single-cell atlases of one
species without an evolutionary comparison; human disease genetics; microbiome ecology; molecular-evolution theory
without a developmental or comparative-genomic result (that slice exists already); anything with cancer or tumours.

## Output

Write exactly this JSON to the output path given in your instructions, nothing else:

```json
{"field": "<field key>", "prompt_version": "curate-d23-v1",
 "keep": ["<id>", "..."],                  // exactly N ids when the shortlist allows, best fit first
 "drop": [{"id": "<id>", "reason": "<one line>"}, ...],   // every shortlisted id you did not keep
 "notes": "<two or three sentences on what the kept set covers and what it lacks>"}
```

Every id in `keep` and `drop` must come from the shortlist; every shortlisted id must appear in exactly one of the two
lists. Use only Read and Write. Write the file in two or three Write/Edit steps if it is long.
