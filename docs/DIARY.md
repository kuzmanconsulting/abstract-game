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
