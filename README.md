# Abstract Reader

A reading game: one scientific abstract, four statements — does the abstract **support** each one, **contradict**
it, or **not address** it? On "Check answers" every statement is marked, the passage it rests on is highlighted in
the text, and the paper appears with title, authors, journal or preprint server, year, DOI and PubMed links.

Corpus: journal articles (PubMed) and bioRxiv/medRxiv preprints, 2023–2026, in cell-free DNA / liquid biopsy,
transposable elements / genome evolution and cancer genomics, fetched through Europe PMC. Statements were written
by Claude from the abstract text alone and kept only when at least two of three independent blind check passes
agreed with the label (docs/DECISIONS.md D5–D6).

```
abstract-game/
├── site/index.html          the game (one static page; fetches data.json next to it)
├── site/data.json           the published items (built, not hand-edited)
├── pipeline/
│   ├── fetch_candidates.py  Europe PMC → src/candidates.json (+ src/raw/)
│   ├── select_corpus.py     balanced, seeded selection → src/corpus.json
│   ├── make_batches.py      generation batches; blind check batches
│   ├── split_batch.py       split a batch into parts after a failed run
│   ├── validate.py          schema + evidence checks; compose / flip rules
│   ├── merge_checks.py      three passes → src/items.json
│   ├── build_site.py        src/items.json → site/data.json
│   └── prompts/             gen-v1…v4.md, check-v1.md (the exact instructions the agents got)
├── src/                     candidates, corpus, batches, generated, checks, items — provenance, all committed
├── tests/test_pipeline.py   python3 -m unittest discover -s tests -v
└── docs/                    DECISIONS.md · SCHEMA.md · DIARY.md · LOG.md
```

## Play locally

```bash
cd ~/work/abstract-game/site && python3 -m http.server 8000     # then http://localhost:8000/
```

(`data.json` is fetched, so the page needs http, not file://.)

## Publish on GitHub Pages

Pages is free for public repositories, personal or organisation. Once:

```bash
cd ~/work/abstract-game
git init && git add -A && git commit -m "Abstract Reader: first corpus"
gh repo create <org>/abstract-game --public --source=. --push        # or create it in the web UI and git push
gh api -X POST repos/<org>/abstract-game/pages -f build_type=legacy -f "source[branch]=main" -f "source[path]=/site"
```

or in the repository's Settings → Pages: *Deploy from a branch*, branch `main`, folder `/site`. The game is then at
`https://<org>.github.io/abstract-game/`. After every rebuild of `site/data.json`: commit and push.

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
python3 pipeline/build_site.py --repo-url https://github.com/<org>/abstract-game
python3 -m unittest discover -s tests -v
```

New fields go into `FIELDS` in `fetch_candidates.py`; a wider year window is `--start 2000-01-01`. Anything already
in `src/corpus.json` keeps its `n`; new abstracts are appended by a new selection run with a new seed, generated
and checked in their own batches, and merged with everything else.

## Scores

Statements answered, % correct, streak and best streak are kept in the browser (localStorage), per device, and can
be reset from "About the items". Nothing leaves the browser.
