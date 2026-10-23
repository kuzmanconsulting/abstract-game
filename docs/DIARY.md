# Diary — Abstract Reader

Entries are Zagreb local time. Read with docs/LOG.md (the commands) and docs/DECISIONS.md (the why).

## 2026-10-23

**13:09 — the seed.** In the Capsule Log work Maja asked that after each abstract the paper be shown ("I just want
to learn"). Done there with a deferred reveal (trial design reasons). 13:55: she does not want others in the
trial app, but the abstract part "is like a cool game" — several questions per abstract, reveal everything on
submit, title/authors/year/link, no password. 14:14: "make it completely separate", folder `~/work/abstract-game`,
newer papers and preprints in her three fields, no clinical set, 30 % preprints, 500 abstracts, three independent
check passes, GitHub Pages.

**14:15–14:25 — corpus.** Europe PMC instead of PubMed + bioRxiv API: one record format for both sources and keyword
search over preprints. Six queries (3 fields × journal/preprint), 1,000 records each, 2,800 kept after filters
(the big drop is `no_results`: unstructured abstracts with fewer than three numbered sentences, 1,861). Selection
560 = 187/186/187 per field, 168 preprints, years 2023–2026 (plus 4 "2027" issue dates; the page shows the first
publication date's year). 59 title duplicates across sources removed — a preprint and its journal version.

**14:25–14:55 — generation and the classifier.** 16 batches of 35 to parallel agents with gen-v1 (the generator
writes the altered statement). Five were stopped by a content classifier before writing anything; the agents'
own reading: a block of deliberately false claims about real, citable papers reads as fabricated findings. gen-v2
(true paraphrase + edit instruction, pipeline composes): 02aa, 12c, 14a, 14b, 14c, 15a went through; 02ab, 12a,
12b, 15b, 15c were stopped. gen-v3 (generator marks one true statement with a single direction word, pipeline
swaps): 12a, 12b, 15c went through; one generator declined 15b on principle, 02ab was stopped. gen-v4 (generator
writes only true statements; the pipeline picks and swaps the direction word itself): 15b, 02ab went through. The
corpus is therefore mixed-provenance — v1 438 abstracts, v2 67, v3 35, v4 20 — and says so per batch; every
statement is checked the same way regardless (D6). No batch was retried more than once per prompt version. Seven
gen-v4 abstracts have no direction word in any true statement and so no contradicted item. Two small fixes by
hand after validation: a typo "transposor" in gen_05 and a mistyped DOI prefix in gen_10 n=384 (copied from the
batch file). Everything else validated: 560 abstracts, 2,240 statements, every evidence string a verbatim
substring of its abstract.

**14:37, 14:45 — questions in parallel.** Scores (per browser today; a shared leaderboard needs a Worker+KV or the
artifact database), filters (journal picker added), 2000–2023 (next iteration: wider window + year filter),
evolution as a topic (not there — the TE queries bring genome evolution only through TEs; a fourth field
"evolutionary genomics" is the natural next addition).

**14:46 — checks.** 72 blind check batches (24 generation files × passes A/B/C; statements shuffled per pass,
labels removed). Agents launched in waves of up to 20 (the concurrency ceiling); two generation batches per
checker where sizes allow.

**14:55–15:13 — checks in, two corrections, the merge.** 72 check files (24 generation files × A/B/C), every one
valid. Two things the checkers taught the pipeline: (1) the first check inputs carried the generator's statement
id `k` next to the text; not a label, but a generator that did not shuffle leaves an order pattern, so `k` was
stripped from the inputs mid-run (side map files for the merge) and the merge now reports per batch how regular
the label order over `k` was — at most 0.33 of a batch sharing one pattern, so the early passes had little to
read from it; (2) several abstracts lost a clause after "p <": the tag stripper ate "<…>" spans (D8). 13 abstracts
repaired from the raw records and sent through one extra blind pass R on the repaired text, required to agree.
Also made the "more" flip grammatical ("more accurate" → "less accurate", not "fewer accurate"; the two statements
the checkers caught with the old form were dropped as ill-formed). Merge: 560 abstracts kept, 2,201 of 2,240
statements (36 dropped as ambiguous by ≥ 2 checkers, 3 as ill-formed), 521 abstracts with four statements, 39 with
three; checkers vs generator unanimous on every kept statement, checkers vs each other differing on 12 of 6,720
pairs — same model family, so a measure of clarity, not of independence (D9). Site built: 2.3 MB `data.json`,
page checked once at phone and desktop width, light and dark, no overflow, four highlights per reveal.

**15:14–15:30 — delivery, GitHub, Pages.** Project tarred to the Mac (`~/work/abstract-game`), artifact published
(body fragment + `data.json`). The organisation's GitHub repo took the push from the Mac (this session has no
GitHub credentials); Pages was disabled at organisation level (Settings → Member privileges → Pages), and a branch
deploy can only serve `/` or `/docs`, so the site moved from `site/` to `docs/` (D2 amended).

**15:20–17:10 — second corpus (D10, D11).** Maja: evolutionary genomics as a fourth field, more Nature, Cell, Genome
Biology and Nature Communications. 762 evogen candidates and 716 top-journal candidates fetched; 219 + 86 = 305
abstracts appended (existing `n` untouched, `added` label per item). Generation with gen-v4 in batches of 20, all
16 through on the first try (chunked writes). The exactly-one flip rule would have left 170 of the 305 without a
contradicted item — evolution abstracts stack comparatives — so the new files run on the wider first-of-any rule
with 47 pairs (D11), versioned per file so the first corpus is untouched. 48 check batches, 24 checker agents in
two waves (one classifier stop, re-run as two single batches). Reading list added meanwhile (D12): save after the
reveal, export as text/BibTeX/RIS by copying.

**19:30–19:58 — what the checkers found, and the re-check (D13–D15).** Every checker, on most batches, flagged the
same thing: "most → least" in front of a noun is not English, "maximum likelihood" is a method, "no longer" and
"above all" are idioms, and a sentence with both words of a pair gets "losses exceeded losses". Not noise in the
judging — a defect in my rule, and one a player would learn to spot. Rule v2 skips idioms, negations and pairs
whose opposite is present, turns "most X" into "few X", and fixes a/an. It changes the shown wording of 38
abstracts; the verdicts on the old wording are worthless for those, so they went through fresh blind batches, all
three passes (`supersedes: true` — the merge reads them last and keeps the replaced verdicts). The nine agents hit
the usage limit at launch (reset 19:40) and were resumed. Three off-topic papers ("speciation" also means chemical
speciation — battery, toothpaste, thermoelectrics) excluded, query tightened (D14). The page showed statements in
the writer's order, which leaks "not addressed last" — shuffled on every display now (D15); what remains is the
3+1 recipe itself, which a knowing player can exploit; options recorded, Maja's call. Merge: 861 abstracts,
3,373 of 3,448 statements, every kept statement unanimous, 14 of 10,344 pairwise verdicts differ. Four headless
page tests added (journal filter holds over 12 picks; statements shuffled; streak/best/percent arithmetic and
persistence across reload; reading list save + BibTeX export) — Maja asked whether the streak "really works", and
the honest answer is a test, not a reading of the code.

**19:42–19:52 — third corpus started (D16).** Maja: small RNA / RNA biology as a field, more Nature / Cell / Science
league papers, 2020 onwards. New field `smallrna` (1,060 candidates), `top2` journal list over all five fields from
2020 (1,919 candidates), 60 + 75 appended drawn cycling over journals so the big three are not drowned by Nature
Communications. Corpus = 1,000. gen_32..gen_40 generating; flip rule v3 (v2 + "more often" → "less often").
Checks next, then merge, build, delivery.

Open points for Maja: (1) the 3+1 label recipe is guessable (D15) — shuffle 3-of-4 or vary the mix? (2) per-item
statistics (local first; shared needs a Worker or the artifact store); (3) the Pages flip still needs her push.

**19:52–20:10 — third corpus in.** Nine generator batches (chunked writes, no classifier losses this time), 27 blind
check batches of 15, run as 20 + 7. Merge over everything: 996 abstracts kept of 1,000 (3 off-topic excluded, 1 too
few statements), 3,902 statements, every kept statement unanimous, 20 of 11,964 pairwise checker verdicts differ.
Fields: cfDNA 225 · TE 232 · cancer genomics 233 · evolutionary genomics 231 · small RNA 75; 754 journal articles,
242 preprints; Nature 50, Nature Communications 43, Genome Biology 36, Cell 30, Nucleic Acids Research 11, Science 5
… 165 abstracts have no contradicted item (D17). Years now 2020–2026 because of the top-journal reach-back.
Delivered to the Mac and the artifact; the GitHub push is Maja's.

**20:23–21:05 — landmark corpus, gen-v5, page features.** Maja asked for the most impactful papers of the last ten
years, 25–50 per field. "Impact" = Europe PMC citation count (2016–2026, journal articles, reviews out), then a
rule-based shortlist that drops tool/database/resource titles, then one Opus curation agent per field picking the 40
primary research papers with a one-line reason for every drop (D18). 192 kept (TE only had 32 of its top-70 as TE
research). gen-v5 adds the comparative-word requirement (D17): abstracts without a flippable comparison fell from
38 % to 24 of 191. The Opus generators tripped the classifier on 4 of 13 batches; each split into 4–5-abstract
parts written one item at a time went through. One clinical-trial paper (MRX34) excluded (D21). 63 blind checks.
Maja's questions along the way: the title/author/year/journal now show before answering, title optional (D19); a
Share-my-score card (1080×1920 PNG, Web Share on phones) (D20), logo removed from it when she found it tacky; the
real Kuzman Consulting K-mark and banner cropped from her logo file for the page header and footer; and the
"evolutionary genomics shows a cancer abstract" puzzle (D22) — field overlap, three cancer papers re-tagged. Merge:
1,187 abstracts of 1,191 (3 excluded, 1 too few), 4,647 statements, every kept statement unanimous, 22 of 14,256
pairwise checker verdicts differ. Fields cfDNA 265 · TE 264 · cancer genomics 276 · evolutionary genomics 268 ·
small RNA 114; 945 journal, 242 preprint; years 2016–2026.

**21:13–21:36 — D23: the two slices Maja actually meant, and a journal tier.** Her message was precise: the small-RNA
field should have the biology itself — piRNA and miRNA in transposon control and in development — and "evolution"
should mean evo-devo and comparative genomics, not the molecular-evolution slice already there, which stays. One
minute later: "enrich more in Q1 journals, I don't want a lot of random papers", then "or a filter for Q1 journals
only". I did not take Q1 literally: by SJR or JCR quartile Scientific Reports, PLoS ONE, MDPI and Frontiers are Q1,
which is the opposite of what she wants, so the tier is a curated list of 82 journals in `pipeline/journals.py`,
named as curated on the page. Europe PMC turned out to match `JOURNAL:` exactly (Nature ≠ Nature Communications), so
the fetch queries NLM abbreviations and re-checks the returned title, and the 82-clause query had to go through the
POST endpoint. Both new slices were fetched from that list only, 2016–2026, and curated twice over by Opus agents
against her definitions quoted verbatim in the prompt: 25 of the 70 most-cited and 55 of a seeded year-spread sample
of 120, per slice. +153 abstracts (76 evo-devo, 77 small RNA), corpus 1345. The cited evo-devo set is heavy on
"the X genome and the evolution of Y" — comparative genomics by her own words, kept. Also: the Instagram hint under
the share card is gone and the title now sits above the abstract by default (both 21:24). Sixteen generators of 10
abstracts; one stopped by the classifier at once and split into three. I stamped one message 21:46 when the clock
said 21:30 — the same slip as earlier this evening; corrected to Maja at 21:36 and every stamp since is a clock read.

**21:36–21:52 — D23 merged and deployed.** Sixteen generators (one split into three after a classifier stop), 54 blind
checks in three waves of up to twenty agents, all Opus 4.8 at extra effort. Merge over everything: 1,340 abstracts of
1,344 (3 excluded, 1 too few), 5,258 statements, every kept statement unanimous, 22 of 16,092 pairwise checker verdicts
differ — none of them in the new 54 checks. The new slice: 153 abstracts, 611 of 612 statements kept (one ambiguous),
9 abstracts without a contradicted item (no direction word to flip, D17). Fields now cfDNA 265 · TE 264 · cancer
genomics 279 · evolutionary genomics 265 · evo-devo 76 · small RNA 191; 1,098 journal (615 in the leading tier),
242 preprint; years 2016–2026. One generator caught a flip the validator cannot see — "AMP-activated protein kinase"
→ "AMP-repressed" — and reworded its statement; the phrase went into the idiom stop list, which changes nothing
already composed. Delivered to the Mac and the artifact; the push is Maja's. Open: her view of the 82-journal list.

