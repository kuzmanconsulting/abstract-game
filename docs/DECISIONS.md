# Decisions — Abstract Reader

Each entry: what was decided, why, what it rests on. Dates are Zagreb local time.

**D1. A separate project, a separate corpus (Maja, 2026-10-23 13:55 and 14:14: "make it completely separate", "I just
want to learn").** The Capsule Log evidence task is a sealed measurement instrument; a game played in public cannot
share its item bank, and Maja playing it would consume trial items. So: its own folder and repository
(`~/work/abstract-game`), its own corpus fetched fresh, and every PMID or DOI present in the trial banks dropped
at fetch time (`pipeline/fetch_candidates.py --exclude <bank dir>`; 828 identifiers at the time). Nothing here
reads the trial's data or code.

**D2. Static site, no server, no password (Maja, 2026-10-23 13:55: "it can be without password and so on"; 14:14:
"GitHub Pages").** Every answer is revealed on submit, so the page needs no backend: `docs/index.html` +
`docs/data.json` (a branch deploy on GitHub Pages serves only the root or `/docs`, so the page lives beside these
notes), hosted on GitHub Pages (free for public repositories, personal or organisation) and, for the first
look, as a claude.ai artifact. Scores stay in the player's browser (localStorage: statements answered, % correct,
streak, abstracts seen). A shared leaderboard would need a small backend (Cloudflare Worker + KV, or the artifact's
own database) and is deferred.

**D3. Statements as a three-way judgement, not a title question.** The trial's task asks one yes/no/maybe question
per abstract (the title turned into a question). For a learning game, four statements per abstract are richer and
let the reader check specific results: *supported* (a paraphrase of a reported result), *contradicted* (one precise
alteration of a reported result), *not addressed* (plausible, on topic, neither stated nor refuted). The whole
abstract is shown — nothing is withheld — because the skill being practised is careful reading, not inference from
a truncated text. This is the SciFact / "True-False-Not Given" shape (Wadden et al. 2020, EMNLP, for the
supports/refutes/not-enough-info split over abstracts).

**D4. Corpus: Europe PMC, 2023–2026, three fields, 30 % preprints (Maja, 2026-10-23 14:14).** Europe PMC gives one
record format for PubMed articles (`SRC:MED`) and bioRxiv/medRxiv preprints (`SRC:PPR`), keyword search over both
(the bioRxiv API has none), structured-abstract headings as `<h4>` tags, authors, DOI and journal. Fields: cfDNA /
liquid biopsy, transposable elements / genome evolution, cancer genomics (the clinical set of the trial was left
out by request). Filters: 900–3200 characters, a Results-type heading or ≥ 3 sentences with numbers (unstructured
abstracts), no reviews/editorials/letters, bioRxiv and medRxiv only among preprint servers, title-level
de-duplication across sources so a preprint and its journal version cannot both appear. 2,800 candidates →
560 selected (equal thirds per field, 30 % preprints inside each, spread over years, seed 20261023) → target ≥ 500
after checks. Years before 2023 are a stated wish for the next iteration (14:37) and only need a wider window.

**D5. Generation by Claude in batches, with three blind check passes (Maja, 2026-10-23 14:14: "three separate
parallel agents independent check passes").** A generator writes the statements for a batch of abstracts from the
text alone — no title, no authors, no journal — with a verbatim evidence passage and a one-sentence note per
statement (`pipeline/prompts/gen-*.md`). Three checkers, each with the same instructions but a different shuffle
and no access to the intended labels or to each other (`check-v1.md`), label every statement again. Merge rule
(`pipeline/merge_checks.py`): keep a statement when ≥ 2 of 3 checkers give the generator's label, none calls it
ill-formed and fewer than 2 call it ambiguous; keep an abstract with ≥ 3 surviving statements. Every checker's
label and confidence is stored with the item, so a stricter rule (unanimous only) is a filter, not a re-run.
All inputs, outputs and prompts are kept under `src/` for provenance.

**D6. How the contradicted item is made changed three times in one afternoon; the corpus records which way each
batch was made.** gen-v1 asked the generator to write the altered statement itself. Five of sixteen 35-abstract
batches were stopped by a content classifier before writing: a block of deliberately false claims about real,
citable papers reads as fabricated findings whatever the framing. gen-v2 had the generator write the true paraphrase
plus a one-phrase edit instruction (`alter: {from, to, kind}`) and the pipeline compose the sentence; several of
those batches were stopped too, and one checker-style reading of the file is that an edit instruction is still a
recipe. gen-v3 (the generator marks one true statement that carries exactly one direction word) was declined by one
generator on principle. gen-v4, in force from 14:55: **the generator writes only true statements** (3 supported +
1 not addressed) and the pipeline itself picks the first supported statement with exactly one direction word from
a fixed, published list (`validate.FLIP_PAIRS`: higher↔lower, increased↔decreased, enriched↔depleted, …) and swaps
it. The alteration is therefore a deterministic, auditable code rule applied to a true statement — the same
construction SciFact used for its refuted claims — and no model is asked to compose or design a false claim. An
abstract whose true statements carry no single direction word gets no contradicted item (3 supported + 1 not
addressed); the page copes with any mix. Batches that had already succeeded under gen-v1/gen-v2 are kept — every
statement went through the same three checks regardless of how it was made — and `prompt_version` is recorded per
batch and shown in `data.json`. The classifier friction itself is recorded in DIARY.md with times and counts; no
batch was retried more than once per prompt version.

**D7. What the player sees before and after.** Before: year ("Published 2025"), field, journal-or-preprint, the
abstract with its headings, four statements. The title is withheld until the reveal because titles state the
finding. After submit: each statement marked, its label, the note, "show in text" scrolling to the highlighted
evidence passage; then the citation block — title linked to the DOI, authors (first eight, expandable), journal or
server with "preprint, not peer-reviewed", DOI and PMID links, copy-citation. Keys 1·2·3 answer the next open
statement, Enter submits, Enter/Space advances. Filters: field, journals vs preprints, a journal/server picker with
counts (Maja, 14:37). Deep link `#a<n>` opens one abstract. Abstracts are the work of their authors and publishers
and are shown with full citation for reading practice; preprints are labelled as not peer-reviewed.

**D8. A parser defect found by the checkers, repaired without discarding the checks (2026-10-23 15:15).** Several
checkers reported abstracts that lose a clause after "p <" or "P <". Cause: the first tag stripper in
`fetch_candidates.py` treated any "<…>" as markup, so a bare "<" in prose swallowed everything up to the next ">".
13 of the 560 corpus abstracts were affected (not more, because the deletion needs a later ">"). Fix: only real
markup tags are stripped. Repair (`pipeline/repair_text.py`): the 13 abstracts were re-parsed from the raw records
kept in `src/raw/`, the damaged text is kept beside the repaired one (`text_before_repair`), and because their
statements were written and checked against the damaged text, each of those abstracts went through one extra blind
pass (R) on the repaired text; a statement survives there only if R also agrees with its label. One of the 13 is
instructive: the abstract literally contains "<TF-cluster, tissue> pairs", which the damaged text had reduced to
"pairs" — three checkers had flagged the statement as unsettled for exactly that reason.

**D9. What the agreement figures mean.** Three checkers plus the generator agreed unanimously on 2,201 of the 2,240
statements; the checkers differed from each other on 12 pairs out of 6,720. That is the agreement
of four readings by the same model family under the same instructions — it measures how clear-cut the items are,
not independence from that model's blind spots. The useful signal is the flags: 36 statements called ambiguous by
two or more checkers and 3 called ill-formed were dropped, and every flag reason is stored with the item. A human
spot check of a random 30 items is the obvious next quality step; the page's "report it" link collects the rest.
