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
