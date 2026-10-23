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
# one look at the page: python3 -m http.server in site/ + Playwright screenshots at 1100 px light and 390 px dark — no overflow, no console errors
```

## 2026-10-23 15:14 — delivery

```bash
tar --exclude='__pycache__' --exclude='.DS_Store' -czf /mnt/user-data/outputs/abstract-game-1514.tar.gz -C <scratchpad> abstract-game
# bridge: tarball → ~/work/abstract-game/_incoming.tar.gz; on the Mac side: tar -xzf … --strip-components=1; sha256 compared
# artifact: site/artifact.html + files {"data.json": site/data.json}
# GitHub Pages: README "Publish on GitHub Pages" (git init, gh repo create <org>/abstract-game --public, Pages from main:/site)
```

## 2026-10-23 15:23 — GitHub Pages can only serve / or /docs

```bash
git mv site/index.html docs/index.html && git mv site/data.json docs/data.json && git mv site/artifact.html build/artifact.html
#   build_site.py, README, SCHEMA, DECISIONS D2, tests updated for the new paths
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game
python3 -m unittest discover -s tests -v         # 12 OK
# Mac (Maja): git add -A && git commit -m "page served from docs/" && git push ; Settings → Pages → main, folder /docs
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
# 9 checker agents (one batch each, written in chunks); first launch hit the usage limit (reset 19:40), resumed
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
