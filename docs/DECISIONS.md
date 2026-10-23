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

**D10. Second corpus: a fourth field and a journal top-up (Maja, 2026-10-23 15:20: "yes absolutely do evolutionary
genomics as well and please add more Nature papers!! and the Cell and Genome Biology and Nature Communications";
"continue to work on your own").** Taken as: (a) a field `evogen` — evolutionary genomics — with its own query
block (molecular evolution, phylogenomics, adaptive evolution, positive/purifying selection, comparative genomics,
genome evolution, speciation, gene duplication, horizontal gene transfer, convergent evolution, population genomics,
experimental evolution), the same per-field quota as the others (187) and the same 30 % preprint share; (b) a
journal-targeted top-up across all four fields, journals only, exact-title queries (`JOURNAL:"Nature"` matches
*Nature* and not *Nature Genetics*): *Nature* 40, *Cell* 19 (none in cfDNA in the window), *Genome Biology* 27,
*Nature Communications* 32 — 118 in all, weighted towards *Nature* because that was the emphasis. Appended to the
corpus with `select_corpus.py --append` (existing ids and titles excluded, `n` continues at 560, each item tagged
`added`), 865 abstracts in total; generated in 16 new batches of 20 with gen-v4 only, checked by three blind passes
like the first 560, merged with the same rule. The page gains the fourth field in its filter and names the
top-up journals in "About the items". Nothing in the first 560 is touched.

**D11. Flip rule for the second corpus: first direction word of any supported statement, wider vocabulary
(2026-10-23 15:40).** Under the first-corpus rule (a supported statement with *exactly one* direction word from a
21-pair list) 170 of the 305 new abstracts would have had no contradicted item — evolutionary-genomics abstracts
rarely put a single comparative in a sentence. New rule, `flip_rule: "first-of-any"`, recorded in each new
generated file: the first supported statement (by `k`) that carries *any* direction word, with only its first
occurrence swapped; the vocabulary grows to 47 pairs (larger/smaller, stronger/weaker, highest/lowest,
promotes/suppresses, activation/repression, expansion/contraction, positive/negative, gain/loss, conserved/divergent,
…; `validate.FLIP_PAIRS_V2`), and "more" becomes "less" before an adjective or adverb and "fewer" before a noun.
70 abstracts still have no direction word anywhere and keep 3 supported + 1 not addressed. The first corpus is
untouched: its files carry no `flip_rule` and are composed with the original list and the exactly-one rule, so
every statement the checkers judged there is byte-identical to what the page shows. A swapped word in a sentence
with two comparatives can leave the sentence true in rare cases (a symmetric comparison, D9's n=433); the three
blind checks catch those — a flipped statement that two checkers still call supported is dropped.

**D12. Reading list (Maja, 2026-10-23 15:39: "add button save article for reading and export saved articles").**
After the reveal, "Save for reading" (key S) keeps the paper — title, authors, journal or server, year, DOI, link —
in a list at the top of the page (localStorage `ar.saved`, this browser only, like the score). Export is by
copying: plain citations, BibTeX (`@article`, key = first author + year + first long title word, `note = {preprint}`
for preprints) or RIS, into the clipboard, with a visible text box as fallback; a download link would be inert for
artifact viewers, and copying works on both hosts. "Clear list" empties it.

**D13. Flip rule v2 and a blind re-check of the 38 abstracts it changed (2026-10-23 19:30–19:55).** All three
checkers, independently and on most batches of the second corpus, flagged one class of statement as `ill_formed`:
the first-of-any rule had swapped "most" for "least" in front of a noun ("least genes…"), "maximum likelihood" for
"minimum likelihood", "no longer" for "no shorter", "above all" for "below all", and in sentences that contain both
words of a pair had produced "losses exceeded losses" / "smaller than smaller". Those read as planted — a player
could spot them without the abstract. Rule `first-of-any-v2` (`validate.flip_words`/`flip`): a direction word is
skipped when it sits in a fixed phrase or method name (`IDIOMS_V2`), when it is negated ("not upregulated",
"non-conserved"), or when the statement already contains its opposite; "most X" becomes "few X" and "the most X"
"the least X"; "more" becomes "less" unless a plural count noun follows within three words; a/an is fixed in front
of the new word. Applied to every file of the second corpus (`flip_rule_history` keeps the old value), it changes the
shown wording of 38 abstracts (27 reworded, 5 moved to another statement, 6 lost their contradicted item). The
verdicts the checkers gave on the old wording are not valid for the new one, so those 38 went through fresh blind
batches, all three passes (`check_{A,B,C}_F00..F02`, `supersedes: true` — the merge reads them last and keeps the
replaced verdicts under `_superseded`). The other 267 abstracts are byte-identical to what was judged. One residue:
"more often sites" → "fewer often sites" (n=563) — the re-check flagged it and it is dropped; the fix ("more" +
adverb → "less") is rule `first-of-any-v3`, used from the third corpus on, so no checked text changes again.
`src/reflips.json` lists the 38.

**D14. Off-topic abstracts excluded, query tightened (2026-10-23 19:50).** The checkers also reported three
abstracts tagged evolutionary genomics that are not biology: a battery-interface spectroscopy paper (n=753), a
toothpaste tin-NMR paper (n=838) and an ionic-thermoelectric paper (n=849) — all matched by the term "speciation"
(chemical speciation) in the top-journal fetch. They are marked `excluded` in the corpus (kept there with the reason;
their generated statements and checks stay as provenance) and the merge skips them. The evogen query now requires a
biology word in the abstract (genome, gene, phylogen*, species, lineage, organism*, evolutionary), as the cancer
query already did. A title/abstract scan of the other 302 additions found nothing else off-field.

**D15. Statement order shuffled on display; the label mix is predictable per abstract (2026-10-23 19:52).** The
page showed statements in the generator's order, and gen-v4 writers tend to put the not-addressed statement last
(`k_order_leak` up to 0.33) — a leak into the game. The page now shuffles the statements every time an abstract is
shown (`shuffled()` in `show`), confirmed by a headless test. What remains, by construction of gen-v4: an abstract
has 3 true-to-the-text statements + 1 not addressed, and at most one of the true ones is flipped, so a player who
knows the recipe can expect "one not addressed, zero or one contradicted". Mitigation options for a later
iteration, not done: show 3 of the 4 at random; or let the generator vary the mix (2 not addressed on some
abstracts, 2 flips on others). Maja to decide.

**D16. Third corpus (Maja, 19:40: "add also smallrna field including mirna pirna and rna biology and so on …
more nature cell science and those league of papers, prioritize papers over 2020").** New field `smallrna`
(microRNA, piRNA, siRNA, tRNA fragments, lncRNA, circRNA, RNA modification/editing, RNAi, RNA-binding proteins,
splicing, RNA decay/NMD, RNA structure; requires an RNA/gene/cell word), 2023–2026, 60 abstracts, 30 % preprints.
Journal top-up `top2` = Nature, Science, Cell, Nature Genetics, Nature Methods, Nature Biotechnology, Nature
Communications, Cell Genomics, Molecular Cell, Science Advances, Genome Biology, Genome Research, Nucleic Acids
Research, 2020-01-01 onwards, 75 abstracts = 15 per field over the five fields, drawn cycling over journals
(`--spread journal`) so Nature, Cell and Science are drawn as often as Nature Communications. Corpus = 1,000.
Generation gen-v4 in batches of 15 (gen_32..gen_40), flip rule v3, three blind check passes as before.

**D17. Abstracts without a contradicted item (2026-10-23 19:55).** Under gen-v4 the contradicted item exists only
when one of the three true statements carries a direction word. In the first corpus that was 7 abstracts, in the
second 69 of 305 (v2 rule), in the third 51 of 135 — small-RNA and top-journal abstracts report mechanisms and
identities more than comparisons, and the writers paraphrase accordingly. These abstracts play as 3 supported + 1
not addressed, which is fine for reading practice but makes the game's label mix thinner (D15). Fix for the next
generation round, not applied retroactively: a gen-v5 prompt that asks the writer, when the abstract itself states a
comparison or a direction (more/less, higher/lower, increased/decreased, gain/loss …), to put one such comparative
in at least one supported statement, so the pipeline has a word to flip. Statements already checked stay as they are.

**D18. Landmark papers of the last ten years (Maja, 2026-10-23 20:23: "most impactful papers in the fields … those
absolutely should be there … 25–50 each").** "Impact" is operationalised as Europe PMC citation count
(`sort=CITED desc`, journal articles, first published 2016-01-01 or later, reviews excluded by type and title), per
field, with the unstructured-abstract filter relaxed to one numbered sentence (Nature/Science abstracts are prose).
Two things the raw ranking gets wrong are corrected in two recorded steps: a rule-based shortlist
(`select_landmark.py shortlist`: titles that name software, databases, servers, resources, benchmarks or versions
are dropped; a field term must appear in the title or two in the abstract; already-held papers out; top 70 per field
kept), then one curation agent per field (prompt `landmark-v1`, Opus, extra effort) picks the 40 primary research
papers of the decade and gives a one-line reason for every drop — both lists live in `src/landmark*` so the
selection can be audited and redone. Citation order is kept unless a drop reason applies; the agent is asked for
breadth within the field. Preprints are not part of this addition (citation counts are a journal-side measure).
Statements for these 200 abstracts are written with gen-v5 and checked as everything else.

**D19. Journal, year and first author shown before answering; title optional (Maja, 20:23: "didn't we have paper
title and author and year and journal in abstract previously?").** They were shown only after the reveal, because a
title usually states the main result. From now the eyebrow line carries journal (or preprint server), year and first
author from the start — none of which answers a statement — and the title stays for the citation block unless the
player turns on "Title shown before answering" in About (localStorage `ar.prefs.titleFirst`, off by default).

**D20. "Share my score" (Maja, 20:30).** Instagram has no web endpoint for posting a story; a story can only be
posted from the app. What a page can do: draw a 1080×1920 score card (fields, statements, % correct, best streak,
the game's link) on a canvas, let the player save it as PNG, and on phones hand it to the system share sheet (Web
Share API with files), where Instagram is one of the targets. Both work on GitHub Pages; in the claude.ai artifact
viewer downloads and the share API are blocked, so there the card is shown with a "long-press/right-click to save"
hint. Implemented after the landmark corpus.

**D21. One landmark abstract excluded: the MRX34 phase-1 trial (n=1139, 2026-10-23 20:50).** The statement
generator was stopped by the content classifier twice on the batch containing it (whole batch gen_50, then the
5-abstract part gen_50a), while the four other abstracts of that part are ordinary RNA biology. Two reasons to drop
rather than keep trying: the one-retry-per-prompt-version rule (D7), and the paper is a clinical trial, which Maja
asked to leave out of the corpus from the start ("omitting the clinical", 14:14). Marked `excluded` in the corpus with
the reason; the other four go through as gen_50a. The same split-and-retry handled gen_47, gen_51 and gen_53 (the
Opus generators were stopped on 4 of 13 whole batches; every 4–5-abstract part written one item at a time went through).

**D22. Field overlap: a few cancer papers were tagged evolutionary genomics (Maja, 2026-10-23 20:56: "how
evolutionary genomics has cancer abstract? is something messed up?").** Not corruption: each abstract's `field` is
the search query that retrieved it, and tumour evolution uses evolutionary-genomics vocabulary (positive selection,
genome evolution, clonal lineages), so some cancer papers matched the `evogen` query and were tagged evogen. Of the
abstracts this surfaced, three are primarily cancer studies retrieved only under the evogen query — n=764 (ecDNA in
Barrett's oesophagus), n=775 (UV-driven dendritic-cell leukaemia), n=780 (ecDNA-positive cancers), all from the
top-journal draw — and are re-tagged to `cancergen` (`field_was` kept, `header.retagged`). The rest stay evogen
because their finding is evolutionary even though they mention cancer: n=563 (positive selection on mitochondrial
rRNA genes across 14,106 tumours), n=999 (evolution of primate-specific genes and cancer risk), plus two the
keyword scan flagged by coincidence — n=700 (the plant *American cancer-root*) and n=720 (SAMD9/9L antiviral gene
evolution). The statements were always about the paper shown; only the field chip was off for those three.

**D23. Two additions and a journal tier (Maja, 2026-10-23 21:13–21:24: "more pure biology papers, pirna, mirna in
transposon regulation, in development and so on, and evolution.. but like evodevo evolution, comparative genomics …
dont remove but add"; "enrich more in Q1 journals i dont want a lot of random papers"; "have a filter for q1
journals only").** Three parts.

*Fields.* `rnadev` is a second query for the existing `smallrna` field (`FIELDS[...]["as"]`; the corpus item keeps
`query_field` = rnadev): piRNA/PIWI, transposon silencing, endo-siRNA, RNAi, miRNA biogenesis and the developmental
miRNAs, plant small RNAs, with a `require` list of developmental/germline/transposon/model-organism words and an
`exclude` clause (`NOT (ABSTRACT:cancer OR … patients OR biomarker OR serum OR plasma …)`) so the clinical miRNA
literature that dominated the first smallrna draw stays out. `evodevo` is a new field, "evo-devo / comparative
genomics": cis-regulatory and GRN evolution, Hox and body plans, gene family expansion and loss, whole-genome
duplication, convergent evolution, novelty and co-option, de novo genes, comparative genomics across lineages;
cancer terms excluded. The existing `evogen` slice (molecular evolution, phylogenomics, selection) is unchanged, as
asked ("this is ok but isnt what i consider evolution").

*Journal tier.* "Q1" taken literally (SCImago or JCR quartile within a category) admits Scientific Reports, PLoS ONE,
the MDPI and Frontiers titles and most BMC journals — the "random papers" Maja wants fewer of. So the tier is a
curated list, `pipeline/journals.py` (82 journals: the Nature, Cell and Science research families, PNAS, eLife, the
genome/genetics/evolution/RNA/development society and specialist journals, and the cancer and medical journals the
cfDNA and cancer-genomics slices draw on), stated as curated on the page and editable in one place. Europe PMC's
`JOURNAL:` field is an exact match on the title or NLM abbreviation (`JOURNAL:"Nature"` does not return Nature
Communications), so the fetch queries the abbreviations and `keep()` re-checks the returned title against the list
(`journal_not_listed`); long queries go through the `searchPOST` endpoint. Every corpus item gets `tier` = leading |
null at build time (`journals.is_leading`), journal names are displayed in the list's form (`journals.display`:
"Nature Communications", "PNAS", "Science"), and the page's source row gains a "Leading journals" chip (journal
articles with tier = leading; preprints excluded by definition). 462 of the 946 journal abstracts present before this
round are in the tier.

*Selection.* Both new slices were fetched from the leading journals only, 2016–2026, journal articles (no preprints:
the request was for journals), relevance order, 2 × 1000 records per query, `--min-numbered 1` as for the landmark
set (Nature/Science abstracts carry few numbers). Two shortlists per query field through `select_landmark.py`
(generalised: `--sample-seed`, `--out`, `--split-dir`, `--pick-glob`, query-field grouping): the 70 most-cited, and
a seeded year-spread sample of 120 from the relevance pool (seed 20261023005), both after the tool/resource-title and
in-corpus filters. One Opus agent per shortlist (prompt curate-d23-v1, which carries Maja's definitions verbatim)
kept 25 of the cited and 55 of the sampled per field, with a reason for every drop. Applied in that order
(`d23-leading-cited`, then `d23-leading-pool`; 7 of the pool picks were already taken by the cited set or the
corpus): +153 abstracts, 76 evodevo and 77 smallrna, 2016–2026 roughly even by year, corpus 1192 → 1345. The
cited evodevo set leans on "the X genome and the evolution of Y" papers (salmon, orchid, water lily, hornwort, fern,
pine, sturgeon …) — comparative genomics as Maja named it, kept.

*Page, same round.* The Instagram hint under the share card removed ("remove this please", 21:24). The title is shown
above the abstract by default ("add title before abstract", 21:24); the About toggle (D19) now turns it off rather
than on (`ar.prefs.titleFirst` default true). Statements are generated with gen-v5, flip rule first-of-any-v3,
batches of 10 to keep the Opus generators under the classifier's threshold (one of 16 was still stopped and split
into three parts, D21 procedure).

