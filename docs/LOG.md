# Execution log — Abstract Reader

Exact commands, in order. Paths are relative to the project root unless absolute. Agent steps are the
Read-prompt → Read-batch → Write-output runs described in docs/DECISIONS.md D5–D6.

## 2026-10-23 14:15–14:25 — corpus

```bash
curl -sS "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=...&resultType=core&format=json&pageSize=3"   # reachability + record shape
python3 pipeline/fetch_candidates.py --exclude ~/work/pilltrackerapp/tasks/bank
#  cfdna_journal 741/1000 kept · cfdna_preprint 253 · te_journal 598 · te_preprint 265 · cancergen_journal 714 · cancergen_preprint 229 → n=2800
#  dropped: no_results 1861 · server 1076 (not bioRxiv/medRxiv) · length 204 · duplicate 32 · title_type 23 · pub_type 3 · metadata 1
python3 pipeline/select_corpus.py --n 560 --preprint-share 0.3 --seed 20261023
#  by_field cancergen 187 / te 186 / cfdna 187 · journal 392 / preprint 168 · bioRxiv 110 / medRxiv 58 · structured 243 · title dups removed 59
python3 pipeline/make_batches.py gen --size 35          # 16 batches gen_00 … gen_15 (2.0 MB)
```

## 2026-10-23 14:25–14:55 — generation (agents) and prompt revisions

```bash
# one agent per batch: Read pipeline/prompts/gen-v1.md + src/batches/gen_NN.json → Write src/generated/gen_NN.json
# stopped by a content classifier before writing: gen_02, gen_12, gen_14, gen_15 (gen-v1); then gen_02a (v1 half)
python3 pipeline/split_batch.py gen_02a 2
python3 pipeline/split_batch.py gen_12 3
python3 pipeline/split_batch.py gen_14 3
python3 pipeline/split_batch.py gen_15 3
# gen-v2 (basis + alter): 02aa 12c 14a 14b 14c 15a written · 02ab 12a 12b 15b 15c stopped
# gen-v3 (flip-marked true statement): 12a 12b 15c written · 15b declined · 02ab stopped
# gen-v4 (true statements only; pipeline picks the flip): 15b 02ab written
sed -i 's/transposor/transposon/' src/generated/gen_05.json      # typo reported by the generator
#  gen_10 n=384: id copied with the wrong DOI prefix → set to the batch's id (python one-liner, json load/dump)
python3 pipeline/validate.py gen          # 25 files OK; 560 abstracts; versions v1 438 · v2 67 · v3 35 · v4 20
python3 -m unittest discover -s tests -v  # 11 OK
```

## 2026-10-23 14:46–15:13 — checks (agents), corrections, merge, build

```bash
python3 pipeline/make_batches.py check --passes A B C --seed 7     # 57, then +15 = 72 check batches
# one agent per pass and one to four generation batches:
#   Read pipeline/prompts/check-v1.md + src/batches/check_P_NN.json → Write src/checks/check_P_NN.json
#   (≤ 20 agents at once; a checker reads a 35-abstract batch in pages of ~350 lines)
# 14:52 generator ids stripped from every check input (atomic rewrite; mapping kept in check_P_NN.map.json);
#   make_batches.py writes both files from now on and leaves existing check batches alone (--force to rewrite)
python3 -m unittest discover -s tests -v         # 11 OK (end-to-end test reads the map file)
python3 pipeline/validate.py check               # 72 OK (2 with evidence-not-verbatim warnings: A_10, A_14c)
# 15:15 tag stripper fixed in fetch_candidates.py (bare "<" in prose was treated as markup, D8)
cp src/corpus.json src/_corpus_before_repair.json.bak
python3 pipeline/repair_text.py                  # 13 abstracts repaired from src/raw → src/repairs.json; check_R_00 built (pass R)
# agent: check-v1 on src/batches/check_R_00.json → src/checks/check_R_00.json
python3 pipeline/merge_checks.py --passes A B C  # 560 kept · 2201/2240 statements · dropped ambiguous 36, ill_formed 3 · pairwise differ 12/6720
python3 pipeline/build_site.py                   # site/data.json 2.27 MB · site/artifact.html (body fragment for the artifact) — moved to docs/ + build/ at 15:25, see below
python3 -m unittest discover -s tests -v         # 12 OK (+ the more→less/fewer flip test)
# page inspection: python3 -m http.server in site/ + Playwright screenshots at 1100 px light and 390 px dark — no overflow, no console errors
```

## 2026-10-23 15:14 — delivery

```bash
tar --exclude='__pycache__' --exclude='.DS_Store' -czf /mnt/user-data/outputs/abstract-game-1514.tar.gz -C <scratchpad> abstract-game
# bridge: tarball → ~/work/abstract-game/_incoming.tar.gz; on the local machine: tar -xzf … --strip-components=1; sha256 compared
# artifact: site/artifact.html + files {"data.json": site/data.json}
# GitHub Pages: README "Publish on GitHub Pages" (git init, gh repo create <org>/abstract-game --public, Pages from main:/site)
```

## 2026-10-23 15:23 — GitHub Pages can only serve / or /docs

```bash
git mv site/index.html docs/index.html && git mv site/data.json docs/data.json && git mv site/artifact.html build/artifact.html
#   build_site.py, README, SCHEMA, DECISIONS D2, tests updated for the new paths
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game
python3 -m unittest discover -s tests -v         # 12 OK
# on the local machine: git add -A && git commit -m "page served from docs/" && git push ; Settings → Pages → main, folder /docs
```

## 2026-10-23 15:20–17:10 — second corpus: evolutionary genomics + top journals (D10, D11)

```bash
python3 pipeline/fetch_candidates.py --fields evogen --suffix evogen --out src/candidates_evogen.json --exclude <bank>     # 762 kept
python3 pipeline/fetch_candidates.py --fields cfdna te cancergen evogen --sources journal --journals top --suffix top --out src/candidates_top.json --exclude <bank>   # 716 kept
cp src/corpus.json src/_corpus_v1_560.json.bak
python3 pipeline/select_corpus.py --append --candidates src/candidates_evogen.json --n 219 --preprint-share 0.3 --seed 20261023001 --fields evogen --label evogen-2026-10-23
python3 pipeline/select_corpus.py --append --candidates src/candidates_top.json --n 86 --preprint-share 0 --seed 20261023002 --fields cfdna te cancergen evogen --journals Nature Cell "Genome Biology" "Nature Communications" --label top-journals-2026-10-23
python3 pipeline/make_batches.py gen --size 20 --start 560 --first-batch 16        # gen_16 … gen_31 (305 abstracts)
# 16 generator agents, gen-v4; then "flip_rule": "first-of-any" written into each new generated file (D11)
python3 pipeline/validate.py gen                                                   # 41 files OK
python3 pipeline/make_batches.py check --passes A B C --seed 7                     # +48 check batches (check_P_16 … check_P_31)
# 24 checker agents (two batches each; A_20/A_21 re-run singly after a classifier stop), ≤ 20 at once
python3 pipeline/validate.py check                                                 # 121 OK
```

## 2026-10-23 19:30–19:58 — flip rule v2, re-check, exclusions, merge (D13–D15)

```bash
cp -r src/generated src/_bak/generated_before_reflip
python3 pipeline/make_batches.py reflip --from-rule first-of-any --to-rule first-of-any-v2 --seed 7   # 38 abstracts → check_{A,B,C}_F00..F02; src/reflips.json
# 9 checker agents (one batch each, written in chunks); first launch reached the usage limit (reset 19:40), resumed
python3 pipeline/validate.py check                                                 # 130 OK
#  corpus: n 753, 838, 849 marked "excluded" (D14); docs/index.html: statements shuffled on display (D15); smallrna field label
python3 pipeline/merge_checks.py --passes A B C      # 865 generated · 3 excluded · 861 kept · 3373/3448 statements reach the page · dropped ill_formed 13, ambiguous 60 · too few 1 (n=859) · pairwise differ 14/10344
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game   # docs/data.json 3.5 MB
python3 -m unittest discover -s tests -v             # 16 OK (12 pipeline + 4 headless page tests: journal filter, shuffle, streak/best/persistence, reading list)
```

## 2026-10-23 19:42–19:52 — third corpus: small RNA + top-league journals 2020– (D16)

```bash
python3 pipeline/fetch_candidates.py --fields smallrna --sources journal preprint --suffix rna --out src/candidates_rna.json --exclude <bank>      # 1060 kept
python3 pipeline/fetch_candidates.py --fields cfdna te cancergen evogen smallrna --sources journal --journals top2 --start 2020-01-01 --suffix top2 --out src/candidates_top2.json --exclude <bank>   # 1919 kept
cp src/corpus.json src/_corpus_v2_865.json.bak
python3 pipeline/select_corpus.py --append --candidates src/candidates_rna.json --n 60 --preprint-share 0.3 --seed 20261023003 --fields smallrna --label third-smallrna
python3 pipeline/select_corpus.py --append --candidates src/candidates_top2.json --n 75 --preprint-share 0 --seed 20261023004 --fields cfdna te cancergen evogen smallrna --spread journal --label third-top2   # corpus 1000
python3 pipeline/make_batches.py gen --size 15 --start 865 --first-batch 32        # gen_32 … gen_40
# 9 generator agents, gen-v4, outputs written in chunks
```

## 2026-10-23 19:52–20:10 — third corpus: generation, checks, merge, build (D16, D17)

```bash
# 9 generator agents (gen_32 … gen_40, gen-v4, chunked writes); then "flip_rule": "first-of-any-v3" written into each file
python3 pipeline/validate.py gen                                                   # 50 files OK (51 new abstracts without a direction word → no contradicted item, D17)
python3 pipeline/make_batches.py check --passes A B C --seed 7                     # +27 check batches (check_P_32 … check_P_40, 15 abstracts each)
# 27 checker agents, one batch each, ≤ 20 at once
python3 pipeline/validate.py check                                                 # 157 OK
python3 pipeline/merge_checks.py --passes A B C      # 1000 generated · 3 excluded · 996 kept · 3902/3988 statements · dropped ill_formed 14, ambiguous 70 · too few 1 · pairwise differ 20/11964
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game   # docs/data.json 4.0 MB, years 2020–2026; "Science (New York, N.Y.)" shown as "Science"
python3 -m unittest discover -s tests -v             # 17 OK
```

## 2026-10-23 20:23–20:55 — landmark corpus (D18–D21) and page work (D19, D20, logo)

```bash
python3 pipeline/fetch_candidates.py --fields cfdna te cancergen evogen smallrna --sources journal --sort cited --min-numbered 1 --start 2016-01-01 --page-size 300 --suffix landmark --out src/candidates_landmark.json --exclude <bank>
python3 pipeline/fetch_candidates.py --fields evogen --sources journal --sort cited --min-numbered 1 --start 2016-01-01 --page-size 300 --pages 3 --suffix landmark2 --out src/candidates_landmark_evogen.json --exclude <bank>   # evogen widened to 900 records, merged into candidates_landmark.json
python3 pipeline/select_landmark.py shortlist --per-field 70      # src/landmark_shortlist.json + src/landmark/shortlist_<field>.json; dropped off_field 790, tool_title 159, in_corpus 9
# 5 curation agents (Opus, extra effort; prompt landmark-v1) → src/landmark_pick_<field>.json: cfdna 40, cancergen 40, evogen 40, smallrna 40, te 32
cp src/corpus.json src/_corpus_v3_1000.json.bak
python3 pipeline/select_landmark.py apply --label landmark-2016-2026 --n 40     # +192 → corpus 1192
python3 pipeline/make_batches.py gen --size 15 --start 1000 --first-batch 41    # gen_41 … gen_53
# 13 generator agents (Opus, extra effort, prompt gen-v5); classifier stops on gen_47, gen_50, gen_51, gen_53 →
python3 pipeline/split_batch.py gen_47 3 ; … gen_50 3 ; … gen_51 3 ; … gen_53 3   # parts written one item at a time
#  n=1139 (MRX34 phase-1 trial) removed from gen_50a and marked excluded in the corpus (D21)
#  "flip_rule": "first-of-any-v3" written into gen_41 … gen_53c
python3 pipeline/validate.py gen                                                 # 71 files OK; 24 of 191 landmark abstracts without a direction word
python3 pipeline/make_batches.py check --passes A B C --seed 7                   # +63 check batches
# page: journal/year/first author in the eyebrow + optional title (D19); Share my score card (D20); Kuzman Consulting
#   K-mark and banner cropped from kuzman_consulting_logo.jpg (docs/assets/, embedded as data URIs)
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game
```

## 2026-10-23 20:56–21:05 — landmark merge, retag, deploy

```bash
#  corpus: n 764, 775, 780 re-tagged evogen → cancergen (field overlap, D22)
python3 pipeline/validate.py check                 # 220 OK (first + second + third + landmark)
python3 pipeline/merge_checks.py --passes A B C    # 1191 generated · 3 excluded · 1187 kept · 4647 statements · dropped ill_formed 18, ambiguous 84, disagreement 1 · pairwise differ 22/14256
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game   # docs/data.json, years 2016–2026
python3 -m unittest discover -s tests -v           # 17 OK
```

## 2026-10-23 21:13–21:36 — D23: evo-devo and pure-biology small RNA from leading journals, journal tier, page

```bash
# 21:13 requirement: pure-biology piRNA/miRNA papers (TE regulation, development) and an evo-devo / comparative-genomics slice, added, nothing removed;
#       21:14 requirement: higher share of Q1-journal papers, fewer papers from arbitrary venues; 21:16 requirement: a Q1-only journal filter; 21:24 requirement: Instagram hint removed, title before abstract
# 21:21 pipeline/journals.py — 82 leading journals (display name, NLM abbreviation), canon()/is_leading()/display(); self-check: python3 pipeline/journals.py
#       fetch_candidates.py: FIELDS rnadev (as smallrna) and evodevo with require + exclude; --journals leading; keep() drops journal_not_listed;
#       queries > 4000 chars go to Europe PMC searchPOST (GET returned nothing; POST to /search returns 405)
BANK=<verify2 copy of the trial bank, 936 PMIDs>
python3 pipeline/fetch_candidates.py --fields rnadev evodevo --sources journal --journals leading --start 2016-01-01 --pages 2 --min-numbered 1 --suffix leading --out src/candidates_leading.json --exclude $BANK            # 21:24: rnadev 1715 kept of 2000 (hitCount 3210), evodevo 1478 of 2000 (5426)
python3 pipeline/fetch_candidates.py --fields rnadev evodevo --sources journal --journals leading --start 2016-01-01 --sort cited --page-size 300 --pages 1 --min-numbered 1 --suffix leading_cited --out src/candidates_leading_cited.json --exclude $BANK   # 21:25: 248 + 231
# select_landmark.py generalised: query_field grouping, --sample-seed (year-spread sample instead of most-cited), --out, --split-dir, --pick-glob, --method
python3 pipeline/select_landmark.py shortlist --candidates src/candidates_leading_cited.json --per-field 70 --out src/d23/shortlist_cited.json --split-dir src/d23/cited          # 21:26: 70 + 70; dropped off_field 183, tool_title 45, in_corpus 14
python3 pipeline/select_landmark.py shortlist --candidates src/candidates_leading.json --per-field 120 --sample-seed 20261023005 --out src/d23/shortlist_pool.json --split-dir src/d23/pool   # 120 + 120; dropped off_field 1090, tool_title 175, in_corpus 33
# 4 curation agents (Opus 4.8, extra effort; prompt curate-d23-v1) → src/d23/pick_cited_{rnadev,evodevo}.json (25 kept / 45 dropped each, 21:28–21:29),
#   src/d23/pick_pool_{rnadev,evodevo}.json (55 kept / 65 dropped each, 21:30–21:31)
cp src/corpus.json src/_corpus_v4_1192.json.bak
python3 pipeline/select_landmark.py apply --candidates src/candidates_leading_cited.json --pick-glob "src/d23/pick_cited_*.json" --label d23-leading-cited --n 25 --method "…"   # +50 (evodevo 25, smallrna 25)
python3 pipeline/select_landmark.py apply --candidates src/candidates_leading.json --pick-glob "src/d23/pick_pool_*.json" --label d23-leading-pool --n 55 --method "…"            # +103 (evodevo 51, smallrna 52; 7 pool picks already present) → corpus 1345
python3 pipeline/make_batches.py gen --size 10 --start 1192 --first-batch 54      # 21:31: gen_54 … gen_69 (16 batches)
# page (21:28): FIELD evodevo; "Leading journals" chip (filt.source = leading ↔ data.json tier); About paragraph on the list; Instagram hint removed;
#   prefs.titleFirst default true. build_site.py: journals.display() for names, tier per item, header.leading_journals / n_leading
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game    # 462 leading of 946 journal abstracts (before the new slices)
# tests: test_pipeline +2 (D23 query/field/journal post-filter; journals canon/display/tier), test_page +2 (leading-journals chip over 12 picks; title shown, hint gone) — 16 + 6 OK
# validate.py --only <batch …> so each generator/checker validates its own file
# 16 generator agents (Opus 4.8, extra effort, gen-v5, flip rule first-of-any-v3, chunked writes); gen_58 stopped by the classifier immediately →
python3 pipeline/split_batch.py gen_58 3                                           # 21:35: gen_58a (4), gen_58b (4), gen_58c (2), written one item at a time
```

## 2026-10-23 21:36–21:52 — D23 generation, checks, merge, deploy

```bash
# 16 generators completed 21:36–21:45 (gen_54 … gen_69 incl. 58a/b/c); one generator replaced "AMP-activated protein kinase" in a statement after
#   seeing the flip "AMP-repressed" → validate.py IDIOMS_V2 += amp-activated (no existing statement text contains it; v2/v3 compositions unchanged)
python3 pipeline/validate.py gen --only gen_54 … gen_69            # 18 OK; 9 of 153 abstracts without a direction word (no contradicted item)
python3 pipeline/make_batches.py check --passes A B C --seed 7     # +54 check batches (check_P_54 … check_P_69, 10 abstracts each; 68's three re-made after gen_68 completed)
# 54 checker agents (Opus 4.8, extra effort, check-v1, chunked writes), 21:40–21:50, waves of ≤ 20; validate.py check --only <batch> by each agent
python3 pipeline/validate.py gen ; python3 pipeline/validate.py check     # 89 gen files OK · 274 check files OK
python3 pipeline/merge_checks.py --passes A B C                    # 21:50: 1344 generated · 3 excluded · 1340 kept · 5258 statements · dropped ill_formed 18, ambiguous 85, disagreement 1
#   · pairwise 16070 agree / 22 differ (the 54 new checks: 0 differ) · D23 slice: 153 abstracts, 611 of 612 statements kept (1 ambiguous), 9 without a contradicted item
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game   # 1340 / 5258, years 2016–2026, leading 615 of 1098 journal abstracts (61 journals)
python3 -m unittest discover -s tests                              # 22 OK (16 pipeline + 6 page)
# delivery: tar (no .git, no src/_bak) → split 24 MB → device_commit_files → on the local machine: cat _incoming4.* > _incoming4.tgz; tar --overwrite -xzf … --strip-components=1
```

## 2026-10-23 22:04–22:05 — README for players (requirement: README addressed only to users of the app/site)

```bash
# README.md rewritten for players (play, keys, filters, leading journals, sources, privacy, reporting); the repository layout, local
#   serving, GitHub Pages, corpus rebuild/extension and flip-rule sections moved verbatim to docs/PIPELINE.md
```

## 2026-10-24 — D24: recent, most-cited leading-journal layer (requirement: 50 more per field from 2023–2026 leading journals, ranked by citations)

```bash
BANK=<trial-bank exclusion list, 936 PMIDs>
python3 pipeline/fetch_candidates.py --fields cfdna te cancergen evogen evodevo smallrna rnadev --sources journal --journals leading \
  --start 2023-01-01 --sort cited --page-size 400 --pages 1 --min-numbered 1 --suffix recent_cited --out src/candidates_recent_cited.json --exclude $BANK
python3 pipeline/fetch_candidates.py --fields cancergen evogen evodevo --sources journal --journals leading \
  --start 2023-01-01 --sort cited --page-size 400 --pages 2 --min-numbered 1 --suffix recent_cited2 --out src/candidates_recent_cited2.json --exclude $BANK
# rnadev records relabelled query_field=smallrna so the small-RNA field has one shortlist
python3 pipeline/select_landmark.py shortlist --candidates src/candidates_recent_cited.json --per-field 100 --out src/d24/shortlist_recent.json --split-dir src/d24/shortlists
# 6 curation agents (curate-recent-v1, written field definitions) → src/d24/pick_<field>.json; 50 kept per field, best fit first, citation order preserved
python3 pipeline/select_landmark.py apply --picks "src/d24/pick_*.json" --candidates src/candidates_recent_cited.json   # +300 abstracts, title-deduped, into src/corpus.json
python3 pipeline/make_batches.py gen --size 10            # gen_70 … gen_99 (one batch split into 89a/b/c after a content-classifier stop)
# 30 generators (gen-v5: true statements only, comparative word when the abstract compares), all leading-journal abstracts
python3 pipeline/validate.py gen                          # all gen_70–99 + 89a/b/c statement files OK
python3 pipeline/make_batches.py check --passes A B C --seed 7   # 96 blind-check batches (A/B/C × 32), labels stripped, statement order randomised
```

## 2026-10-24 02:44–03:46 — D24 three blind passes, merge, build, deploy

```bash
# 96 checker agents (check-v1, chunked writes), waves of ≤ 20; each ran validate.py check --only <batch> to OK
python3 pipeline/validate.py check                        # 370 check files OK, 0 FATAL (A/B/C 123 each + reflip); validated before merge — a file existing is not a file complete
python3 pipeline/merge_checks.py --passes A B C
#   abstracts 1644 generated · 3 excluded · 1 too few · 1640 kept · 6447 statements
#   dropped: ill_formed 19 · ambiguous 95 · disagreement 1 ; agreement unanimous 6446 · majority 1
#   pairwise checker verdicts 19666 agree / 26 differ (0.13%)
#   kept_by_field cancergen 329 · te 314 · cfdna 315 · evogen 315 · smallrna 241 · evodevo 126 ; journal 1398 · preprint 242
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game   # 1640 / 6447, years 2016–2026, leading tier 915 of 1398 journal abstracts
python3 -m unittest discover -s tests                     # 22 OK
# delivery: tar (no .git, no src/_bak) → split 24 MB → device_commit_files → on the local machine: cat parts > tgz; tar --overwrite -xzf … --strip-components=1
```

## 2026-10-24 — D26: epigenetics / genome-regulation field (requirement: top ~100 genome-regulation papers; 2016–2026 window plus up to 30 pre-2016 landmarks)

```bash
# field "epi" added to fetch_candidates.py (chromatin, histone marks, DNA methylation/TET, Polycomb, enhancers, 3D genome, X-inactivation, imprinting; cancer/clinical excluded)
BANK=<trial-bank exclusion list, 936 PMIDs>
python3 pipeline/fetch_candidates.py --fields epi --sources journal --journals leading --start 2016-01-01 --end 2026-12-31 --sort cited --page-size 400 --pages 2 --min-numbered 1 --suffix epi_recent  --out src/candidates_epi_recent.json  --exclude $BANK   # 617 / 800
python3 pipeline/fetch_candidates.py --fields epi --sources journal --journals leading --start 2005-01-01 --end 2015-12-31 --sort cited --page-size 400 --pages 2 --min-numbered 1 --suffix epi_landmark --out src/candidates_epi_landmark.json --exclude $BANK   # 612 / 800
python3 pipeline/select_landmark.py shortlist --candidates src/candidates_epi_recent.json  --per-field 220 --out src/epi/shortlist_recent220.json --split-dir src/epi/sl_recent220   # recent pool deepened: top-120 strict pool was only ~47 clean findings (atlases/methods dominate the citation-top)
python3 pipeline/select_landmark.py shortlist --candidates src/candidates_epi_landmark.json --per-field 60  --out src/epi/shortlist_landmark.json  --split-dir src/epi/sl_landmark
# 3 curation agents (curate-epi-v1): recent strict → 70 genuine-finding papers; landmark → 30 pre-2016 classics
python3 pipeline/select_landmark.py apply --candidates src/candidates_epi_recent.json  --pick-glob src/epi/pick_recent.json  --label epi-recent-2016-2026  --n 70
python3 pipeline/select_landmark.py apply --candidates src/candidates_epi_landmark.json --pick-glob src/epi/pick_landmark.json --label epi-landmark-2005-2015 --n 30   # corpus → 1745 items (100 epi, n 1645–1744)
python3 pipeline/make_batches.py gen --size 10 --start 1645 --first-batch 100   # gen_100 … gen_109
python3 pipeline/validate.py gen                                                # epi gen files OK (3 abstracts without a contradicted item, D17)
python3 pipeline/make_batches.py check --passes A B C --seed 7                   # +30 blind-check batches
python3 pipeline/validate.py check                                              # 400 check files OK, 0 FATAL (whole set validated before merge)
python3 pipeline/merge_checks.py --passes A B C
#   abstracts 1744 gen / 1740 kept ; statements 6964 gen / 6838 kept ; dropped ill_formed 19 · ambiguous 104 · disagreement 1
#   agreement unanimous 6837 · majority 1 ; pairwise 20862 agree / 30 differ (0.14%) ; by_field epi 100 ; leading tier 1015
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game   # 1740 / 6838, years 2005–2026
python3 -m unittest discover -s tests                                           # 24 OK
```

## 2026-10-24 — D27: visibility, PWA and visual design pass

```bash
# docs/: og.png (1200x630 preview), icon-192/512/512-maskable.png, robots.txt, sitemap.xml, manifest.webmanifest, sw.js
# docs/index.html: PAGES-ONLY head (meta description, canonical, Open Graph/Twitter cards, theme-color, favicon, manifest, JSON-LD);
#   hero lead + first-run intro; per-field colour+glyph system on chips/eyebrow; verdict glyphs on choices and pills; reveal sweep;
#   two-stage data-lite.json -> data.json loader; host-gated service-worker registration
# pipeline/build_site.py: strip the PAGES-ONLY block from the artifact; emit docs/data-lite.json (seeded, field-stratified slice)
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game
python3 -m unittest discover -s tests          # 26 OK
```

## 2026-10-24 — D28: timed Quiz mode

```bash
# docs/index.html: Play/Quiz tabs + timed-quiz engine (10 statements, per-question countdown, time+streak scoring, results screen, shareable card)
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game
python3 -m unittest discover -s tests          # 27 OK
```

## 2026-10-24 — D29: inflammaging / multi-omics-of-ageing field

```bash
# field "inflammaging" added to fetch_candidates.py (inflammaging, immunosenescence, senescence + SASP, ageing clocks,
#   NLRP3/cGAS-STING, clonal haematopoiesis, ageing atlases); ageing-anchor require; oncology excluded; patient/biomarker NOT excluded.
# Europe PMC REST was down (503/500) for ~1 h during the fetch — upstream; an auto-retry poller ran the fetches on recovery.
python3 pipeline/fetch_candidates.py --fields inflammaging --sources journal --journals leading --start 2016-01-01 --end 2026-12-31 --sort cited --page-size 400 --pages 2 --min-numbered 1 --suffix infl_recent   --out src/candidates_infl_recent.json   --exclude $BANK   # 691 kept
python3 pipeline/fetch_candidates.py --fields inflammaging --sources journal --journals leading --start 2000-01-01 --end 2015-12-31 --sort cited --page-size 400 --pages 2 --min-numbered 1 --suffix infl_landmark --out src/candidates_infl_landmark.json --exclude $BANK   # 370 kept
python3 pipeline/select_landmark.py shortlist --candidates src/candidates_infl_recent.json   --per-field 220 --split-dir src/infl/sl_recent
python3 pipeline/select_landmark.py shortlist --candidates src/candidates_infl_landmark.json --per-field 60  --split-dir src/infl/sl_landmark
# 2 curation agents (curate-inflammaging-v1): recent 220->70, landmark 60->30
python3 pipeline/select_landmark.py apply --candidates src/candidates_infl_recent.json   --pick-glob src/infl/pick_recent.json   --label infl-recent-2016-2026  --n 70
python3 pipeline/select_landmark.py apply --candidates src/candidates_infl_landmark.json --pick-glob src/infl/pick_landmark.json --label infl-landmark-2000-2015 --n 30   # corpus 1745 -> 1845
python3 pipeline/make_batches.py gen --size 10 --start 1745 --first-batch 110     # gen_110 … gen_119 (gen-v5, flip_rule first-of-any-v3)
python3 pipeline/make_batches.py check --passes A B C --seed 7                     # +30 check batches (check-v1, 3 blind passes)
python3 pipeline/merge_checks.py --passes A B C   # 1839 items / 7227 statements; pairwise 22058 agree / 34 differ; inflammaging 99
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game   # data.json 1839 items, years 2000-2026
python3 -m unittest discover -s tests             # 29 OK
```

## D30 — TE-chosen tag: the curated PairCompTE reading list (2026-10-26)

```
# source: /Users/majakuzman/work/PairCompTE/docs/paper/READING.md -> pipeline/sources/te_reading/READING_2026-10-26.md
# extract 78 DOIs; resolve DOI->record + abstract via Europe PMC (resultType=core); 1 parenthesised DOI (Nekrutenko 2001) fetched by hand
#   -> pipeline/sources/te_reading/{dois.txt, te_candidates.json}
# dedupe vs corpus: 1 already present (n=949, te) tagged in place; 77 new appended as field=te, source=te_reading, tags=["TE-chosen"], n 1845..1921
python3 pipeline/make_batches.py gen --start 1845 --first-batch 200 --size 26    # gen_200..gen_202 (77 items)
# 3 generator agents (gen-v5, Opus 4.8 xhigh); then stamp flip_rule=first-of-any-v3 on gen_200..202 (24/77 carry no contradicted item)
python3 pipeline/make_batches.py check --passes A B C --seed 7                    # +9 check batches (check-v1, 3 blind passes)
# 9 checker agents (Opus 4.8 xhigh), one per (pass,batch)
python3 pipeline/merge_checks.py --passes A B C   # items.json 1916 (all 77 kept: 74x4 + 4x3 statements); tags carried (merge_checks.py)
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game   # data.json 1916 items / 7531 statements / by_tag {TE-chosen:78}; years 1980-2026
python3 -m unittest discover -s tests             # expect OK
# republished artifact Version 13 (claude.ai) — page carries the ★ TE-chosen filter (filt.tag), build carries by_tag
```
