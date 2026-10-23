# Abstract Reader

**Play:** https://kuzmanconsulting.github.io/abstract-game/

A reading game for people who read scientific papers. You get one abstract and four short statements about it.
For each statement, decide whether the abstract **supports** it, **contradicts** it, or **does not address** it —
judging from the text alone, not from what you know or expect. Then check your answers: every statement is marked,
the passage it rests on is highlighted in the abstract, and the paper appears with its title, authors, journal or
preprint server, year, DOI and PubMed links.

## How to play

- Read the abstract. Its journal, year, first author and title are shown above it (the title can be hidden until
  after you answer: "About the items" → *Title shown before answering*).
- Label each of the four statements. Keys **1 · 2 · 3** answer the next open statement (supported · contradicted ·
  not addressed); **Enter** checks the answers, and after the reveal **Enter** or **Space** goes to the next
  abstract; **Skip** drops the current one without scoring.
- After the reveal, each statement shows why its label is what it is. A "contradicted" statement is a true statement
  from the abstract with one direction word reversed; the reveal says which.
- **Score:** statements answered, % correct, current streak and best streak, kept in your browser only (per
  device). "Share my score" draws a card you can save or hand to your phone's share sheet. Reset from "About the items".
- **Reading list:** after the reveal, *Save for reading* (key **S**) keeps the paper in a list at the top of the
  page; copy the list out as plain citations, BibTeX or RIS. The list lives in this browser only.

## Choosing what to read

- **Fields:** cfDNA / liquid biopsy · transposable elements · cancer genomics · evolutionary genomics · evo-devo /
  comparative genomics · small RNA / RNA biology. A paper's field is the search it was found under; a few papers sit
  at the edge of two fields.
- **Sources:** journal articles indexed in PubMed and bioRxiv/medRxiv preprints (preprints have not been
  peer-reviewed; the page says so). *Leading journals* restricts play to a curated list of the fields' selective
  journals — the Nature, Cell and Science research families, PNAS, eLife, Genome Biology/Research, Nucleic Acids
  Research, Molecular Biology and Evolution, PLoS Genetics/Biology, Development, Current Biology, the EMBO journals,
  the leading cancer and medical journals, and the like. It is a curated list, not a bibliometric quartile.
- **Journal picker:** any single journal or preprint server in the current field and source selection, with counts.
- Abstracts are drawn at random from the selection; each one is shown once before any repeats.

## Where the items come from

Abstracts are journal articles and preprints from 2016–2026, fetched through Europe PMC: recent papers in each
field, a targeted share from the top journals, the most-cited primary research papers of the decade in each field,
and the evo-devo and small-RNA-biology slices drawn from leading journals only. The current counts by field and
source are in "About the items" on the page.

The statements were written from the abstract text alone and kept only when three independent blind checks (each
judging the statements without knowing the intended labels) agreed with the label. Abstracts are shown for reading
practice, each with its citation and links; they remain the work of their authors and publishers.

Nothing you do on the page leaves your browser: no accounts, no tracking, no server.

## A wrong label or a bad statement?

Open an issue at https://github.com/kuzmanconsulting/abstract-game/issues with the DOI and the statement number.

## For the curious

How the corpus is built, checked and published: `docs/PIPELINE.md`. The decisions behind every rule, with dates:
`docs/DECISIONS.md`. The data files, field by field: `docs/SCHEMA.md`.

Abstract Reader is made by [Kuzman Consulting](https://kuzmanconsulting.com), Zagreb.
