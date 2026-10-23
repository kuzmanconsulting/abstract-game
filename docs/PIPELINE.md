# Pipeline and deployment — Abstract Reader

How the corpus is built, checked, published and extended. Players need none of this; it moved here from the README
on 2026-10-23 (Maja: "show only the readme for people using the app/site"). The reasoning behind every rule is in
`docs/DECISIONS.md`, the exact commands with times in `docs/LOG.md`, every file's fields in `docs/SCHEMA.md`.

## Repository layout

```
abstract-game/
├── docs/index.html          the game (one static page; fetches data.json next to it) — GitHub Pages serves /docs
├── docs/data.json           the published items (built, not hand-edited)
├── build/artifact.html      the same page as a body fragment, for the claude.ai artifact (built)
├── pipeline/
│   ├── fetch_candidates.py  Europe PMC → src/candidates.json (+ src/raw/)
│   ├── select_corpus.py     balanced, seeded selection → src/corpus.json
│   ├── make_batches.py      generation batches; blind check batches; reflip (re-check after a flip-rule change)
│   ├── split_batch.py       split a batch into parts after a failed run
│   ├── validate.py          schema + evidence checks; compose / flip rules
│   ├── merge_checks.py      three passes → src/items.json
│   ├── build_site.py        src/items.json → docs/data.json (+ build/artifact.html)
│   └── prompts/             gen-v1…v4.md, check-v1.md (the exact instructions the agents got)
├── src/                     candidates, corpus, batches, generated, checks, items — provenance, all committed
├── tests/                   test_pipeline.py (rules, merge) · test_page.py (headless browser: filters, shuffle, score, reading list)
│                            python3 -m unittest discover -s tests -v
└── docs/*.md                DECISIONS.md · SCHEMA.md · DIARY.md · LOG.md (served too, as plain text)
```

## Play locally

```bash
cd ~/work/abstract-game/docs && python3 -m http.server 8000     # then http://localhost:8000/
```

(`data.json` is fetched, so the page needs http, not file://.)

## Publish on GitHub Pages

Pages is free for public repositories, personal or organisation. Once:

```bash
cd ~/work/abstract-game
git init && git add -A && git commit -m "Abstract Reader: first corpus"
git remote add origin https://github.com/kuzmanconsulting/abstract-game.git && git push -u origin main
gh api -X POST repos/kuzmanconsulting/abstract-game/pages -f build_type=legacy -f "source[branch]=main" -f "source[path]=/docs"
```

or in the repository's Settings → Pages: *Deploy from a branch*, branch `main`, folder `/docs` (a branch deploy
can only serve the root or `/docs`, which is why the page lives there). The game is then at
`https://kuzmanconsulting.github.io/abstract-game/`. After every rebuild of `docs/data.json`: commit and push.

## Rebuild or extend the corpus

```bash
python3 pipeline/fetch_candidates.py --exclude ~/work/pilltrackerapp/tasks/bank   # drop everything in the trial banks
python3 pipeline/select_corpus.py --n 560 --preprint-share 0.3 --seed 20261023
python3 pipeline/make_batches.py gen --size 35
#   generation: one agent per src/batches/gen_*.json with pipeline/prompts/gen-v4.md → src/generated/
python3 pipeline/validate.py gen
python3 pipeline/make_batches.py check --passes A B C --seed 7
#   checks: one agent per src/batches/check_*.json with pipeline/prompts/check-v1.md → src/checks/
python3 pipeline/validate.py check
python3 pipeline/merge_checks.py --passes A B C
python3 pipeline/build_site.py --repo-url https://github.com/kuzmanconsulting/abstract-game
python3 -m unittest discover -s tests -v
```

New fields go into `FIELDS` in `fetch_candidates.py` (with a `require` list of words the abstract must contain — a
bare "speciation" also matches chemistry — and optionally `exclude` words and `as`, the field a second query feeds);
a wider year window is `--start 2000-01-01`; a journal-targeted fetch is `--journals top2`, `--journals leading`
(the list in `pipeline/journals.py`, enforced on the returned titles) or exact titles, with `--suffix … --out
src/candidates_….json`; a curated draw is `select_landmark.py shortlist [--sample-seed …] --split-dir …` → one
curation agent per shortlist → `select_landmark.py apply --pick-glob …` (D18, D23), and `select_corpus.py
--spread journal` cycles over journals when drawing so the small high-profile ones are not drowned by the big ones. Anything already in
`src/corpus.json` keeps its `n`; new abstracts are appended with `select_corpus.py --append --candidates … --n …
--fields … [--journals …] --label …`, batched with `make_batches.py gen --start <first new n> --first-batch <next
batch number>`, generated and checked in their own batches, and merged with everything else (see docs/LOG.md
15:20–16:30 for the second corpus).

## Changing the flip rule

The contradicted statement of a gen-v4 abstract is made by the pipeline (`validate.flip`), so a rule change changes
what players see. Never change a rule in place: add a new `flip_rule` name, run `make_batches.py reflip --from-rule
<old> --to-rule <new>`, which moves the files, lists the abstracts whose wording changes (`src/reflips.json`) and
builds superseding check batches for them, and send those through all passes before merging (docs/DECISIONS.md D13).

## Scores and the reading list

Statements answered, % correct, streak and best streak are kept in the browser (localStorage), per device, and can
be reset from "About the items". "Save for reading" (key S after the reveal) keeps a paper in a list at the top of
the page; the list copies out as plain citations, BibTeX or RIS. Nothing leaves the browser.
