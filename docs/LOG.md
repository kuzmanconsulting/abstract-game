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
python3 pipeline/build_site.py                   # site/data.json 2.27 MB · site/artifact.html (body fragment for the artifact)
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
