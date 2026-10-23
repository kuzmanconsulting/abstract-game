# Schema — Abstract Reader

Every file the pipeline reads or writes, field by field. All JSON is UTF-8; `src/` is provenance and is committed;
`site/` is what gets published.

## `src/candidates.json` — `pipeline/fetch_candidates.py`

`header`: `fetched_utc`, `api`, `window` [start, end], `queries` {`<field>_<source>`: Europe PMC query string},
`counts` {`<field>_<source>`: {fetched, kept}}, `dropped` {reason: n} (reasons: `server` = preprint not on
bioRxiv/medRxiv, `length` = outside 900–3200 chars, `no_results` = no Results-type heading and < 3 numbered
sentences, `metadata` = missing year/title/authors, `trial_bank` = PMID/DOI in the excluded banks, `pub_type`,
`title_type` = review/meta-analysis/protocol/erratum by type or title, `duplicate` = same DOI/id), `excluded_pmids`,
`excluded_dois`, `n`, `filters`.
`candidates[]`: `id` (`pmid:<n>` | `doi:<doi>` | `epmc:<id>`), `epmc_id`, `source` (journal | preprint), `server`
(bioRxiv | medRxiv | null), `pmid`, `doi`, `title`, `authors[]` (fullName), `author_string`, `journal` (journal
title, or the server for preprints), `year`, `date` (first publication date, YYYY-MM-DD), `field` (cfdna | te |
cancergen), `sections[]` {`label` | null, `text`} (structured abstracts keep their headings; otherwise one section),
`n_chars`, `structured`, `has_results`, `pub_types[]`, `url` (PubMed or doi.org), `doi_url`, `is_open_access`.
Raw API records per query: `src/raw/<field>_<source>.json`.

## `src/corpus.json` — `pipeline/select_corpus.py`

`header`: `selected_utc`, `seed`, `n`, `preprint_share`, `candidates_fetched_utc`, `stats` {by_field, by_source,
by_year, by_server, structured, title_duplicates_removed}. `items[]`: candidate fields plus `n` (0-based position;
the item's key everywhere downstream).

## `src/batches/gen_<NN>[a-c].json` — `pipeline/make_batches.py gen`

`batch`, `items[]`: `n`, `id`, `year`, `field`, `source`, `sections`, `text` (sections joined by one space — the
authority for evidence substrings). No title, authors or journal: generators and checkers never see them.
A batch split after a failed run is renamed `_gen_<NN>_unsplit.json.bak` and replaced by `gen_<NN>a…`.

## `src/generated/gen_<NN>[a-c].json` — written by a generator agent

`batch`, `prompt_version` (gen-v1 | gen-v2 | gen-v3 | gen-v4 — the prompt file under `pipeline/prompts/`),
`items[]`: `n`, `id`, `statements[]` (exactly 4): `k` (1–4, stable id within the abstract), `label`, `evidence`
(character-exact substring of `text`, ≤ 300 chars), `note` (one sentence shown after answering), and the text in
one of three forms:
- `text` — gen-v1 (all labels), gen-v3/v4 supported and not_addressed statements;
- `basis` + `alter` {`from`, `to`, `kind` ∈ direction | group | magnitude | condition | significance} — gen-v2
  contradicted item; the shown text is `basis` with `from` → `to` applied once (`validate.compose`);
- `text` + `flip: true` — gen-v3: a true statement with exactly one direction word; the shown text has that word
  swapped by `validate.FLIP_PAIRS` and the item plays as `contradicted` (`validate.label_of`).
gen-v4 files carry only true statements (3 supported + 1 not_addressed, no `flip`); the pipeline marks the first
supported statement (ascending `k`) with exactly one direction word as the flip (`validate.effective`), so the
contradicted item is recomputed from the file every time and stored nowhere else. An abstract with no such
statement has no contradicted item.

## `src/batches/check_<P>_<NN>.json` — `pipeline/make_batches.py check`

`batch`, `pass` (A | B | C), `source_batch`, `items[]`: the generator's view plus `statements[]` {`j` (shuffled
position 1–4, per pass, seeded), `k` (the generator's id), `text` (as the player will see it — composed/flipped)}.
No labels, notes or evidence.

## `src/checks/check_<P>_<NN>.json` — written by a checker agent

`batch`, `pass`, `prompt_version` (check-v1), `items[]`: `n`, `id`, `verdicts[]` {`j`, `label`, `confidence`
1–3, `evidence` (substring, optional), `flag` (absent | ambiguous | ill_formed), `reason` (with a flag)}.

## `src/items.json` — `pipeline/merge_checks.py`

`header`: `merged_utc`, `passes`, `rule` {min_votes 2, min_statements 3, drop_if}, `stats` {abstracts_generated,
abstracts_kept, statements_generated, statements_kept, dropped {disagreement | ill_formed | ambiguous |
unchecked: n}, agreement {unanimous, majority}, kept_by_label, dropped_by_label, abstracts_dropped_too_few,
checker_label_agreement_pairwise {agree, differ}, kept_by_field, kept_by_source, statements_per_abstract}.
`items[]`: corpus metadata (`n`, `id`, `field`, `source`, `server`, `pmid`, `doi`, `title`, `authors`, `journal`,
`year`, `date`, `url`, `doi_url`, `sections`), `generated_by` (batch), `prompt_version`, `statements[]` {`k`,
`text` (as shown), `label` (as played), `evidence`, `note`, `agreement` (unanimous | majority), `checks` {A/B/C:
{label, confidence, flag}}, `alter` {kind, basis, from?, to?} for a composed or flipped item}.

## `site/data.json` — `pipeline/build_site.py`

`header`: `built`, `n_items`, `n_statements`, `by_field`, `by_source`, `years` ("2023–2026"), `merged_utc`,
`passes`, `rule`, `stats` (from items.json), `repo_url`, `sources`, `generation`.
`items[]`: public fields only — `n`, `id`, `field`, `source`, `server`, `pmid`, `doi`, `title`, `authors`,
`journal`, `year`, `date`, `url`, `doi_url`, `sections`, `statements[]` {`k`, `text`, `label`, `evidence`, `note`,
`agreement`, `altered` (kind, only on a composed/flipped item)}. Checker details stay out.

## Browser storage (per viewer, never shared)

`ar.filt` {field, source, journal} · `ar.tally` {n, right, streak, best, byLabel} · `ar.seen` [item ids].
