# Schema — Abstract Reader

Every file the pipeline reads or writes, field by field. All JSON is UTF-8; `src/` is provenance and is committed;
`docs/` holds the page, its data file and these notes; GitHub Pages serves `/docs`.

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
`n_chars`, `structured`, `has_results`, `pub_types[]`, `url` (PubMed or doi.org), `doi_url`, `is_open_access`,
`cited_by` (Europe PMC citedByCount), `query_field` (the `FIELDS` key the record was fetched under; equals `field`
unless that key maps onto another field with `"as"`: `rnadev` → `smallrna`, D23). `FIELDS[...]` may carry
`require` (one of these words must be in the abstract), `exclude` (none of these may be, `NOT (...)`) and `as`.
`header.journals` = the exact journal titles/abbreviations in the query (`--journals top | top2 | leading`, D23;
`header.journals_arg` keeps the argument); with `leading`, records whose returned title is not in
`pipeline/journals.py` are dropped as `journal_not_listed`. Raw API records per query: `src/raw/<field>_<source>[_<suffix>].json`.

## `src/corpus.json` — `pipeline/select_corpus.py`

`header`: `selected_utc`, `seed`, `n`, `preprint_share`, `candidates_fetched_utc`, `stats` {by_field, by_source,
by_year, by_server, structured, title_duplicates_removed}; after `--append` runs also `additions[]` {label,
selected_utc, seed, n, fields, journals, preprint_share, n_range} and after `repair_text.py` `repaired_utc`,
`repaired_n`, `excluded_n[]` (D14). `items[]`: candidate fields plus `n` (0-based position; the item's key
everywhere downstream), `added` (label of the addition, absent for the first 560), `excluded` (reason string on an
off-topic abstract the merge skips), and for repaired abstracts `text_repaired`, `text_before_repair`. Fields:
`cfdna`, `te`, `cancergen`, `evogen`, `evodevo`, `smallrna`. `header.additions[].spread` = year | journal (how the draw cycled).
Items added through `select_landmark.py apply` (D18, D23) carry `query_field`, `cited_by` and `added`; the addition
records `method` and `picks` {query_field: {keep[], drop[], file}}. Retagged items keep `field_was` (D22).

`src/reflips.json` (D13): `from_rule`, `to_rule`, `files[]`, `n[]`, `count`, `kind` {n: reworded | moved | dropped},
`check_batches[]`.

## `src/candidates_landmark.json`, `src/landmark_shortlist.json`, `src/landmark/shortlist_<field>.json`, `src/landmark_pick_<field>.json` (D18)

Candidates fetched with `--sort cited --min-numbered 1 --start 2016-01-01` carry `cited_by` (Europe PMC
citedByCount). `select_landmark.py shortlist` writes the rule-filtered top N per field: `fields` {field: [{rank,
id, cited_by, year, journal, title, abstract_start}]}, `dropped` {in_corpus, tool_title, off_field}. A curation
agent (prompt landmark-v1) writes per field {field, prompt_version, keep[] (ids, ranked), drop[] {id, reason},
notes}. `select_landmark.py apply` appends the kept ids to the corpus with `added` = the label and records
`header.additions[].picks`.

D23 reuses the same shapes under `src/d23/`: `shortlist_cited.json` + `cited/shortlist_<qfield>.json` (top 70 by
citations), `shortlist_pool.json` + `pool/shortlist_<qfield>.json` (`sample_seed` 20261023005, a year-spread sample
of 120), `pick_cited_<qfield>.json`, `pick_pool_<qfield>.json` (prompt curate-d23-v1). Candidates:
`src/candidates_leading.json` (relevance), `src/candidates_leading_cited.json` (CITED desc).

D24 (recent leading-journal papers, all fields) uses `src/candidates_recent_cited.json` (CITED desc, 2023-01-01 onwards,
leading journals; rnadev records relabelled `query_field = smallrna` with `query_field_was`; `header.merged_from`
records the second, wider fetch for cancergen, evogen and evodevo), `src/d24/shortlist_recent.json` +
`src/d24/shortlists/shortlist_<field>.json` (100 most-cited per field) and `src/d24/pick_<field>.json` (prompt
curate-recent-v1, 50 kept per field).

## `private/` — working notes, not published (D25)

`private/DIARY.md`, `private/LOG.md`, `private/DECISIONS.md`: the working versions of the records, with timestamps and
the requests that drove each step. The directory is listed in `.gitignore`; the public versions are `docs/LOG.md` and
`docs/DECISIONS.md` (same content in a formal register, no personal names or quotations). There is no public diary.

## `pipeline/journals.py` — the leading-journal list (D23)

`LEADING` [(display name, NLM abbreviation)], `ALIASES` {Europe PMC title → display name} for titles that `canon()`
does not reduce by itself (PNAS, BMJ, Lancet), `QUERY_TOKENS` (the abbreviations, for `JOURNAL:`), `canon(title)`
(lower-case, parenthetical and ": official journal …" tail removed, "&" → "and", leading "the" dropped),
`leading_name(title)` → display name | None, `is_leading(title)`, `display(title)` (list name, else the cleaned
title). `python3 pipeline/journals.py` self-checks the list.

## `src/batches/gen_<NN>[a-c].json` — `pipeline/make_batches.py gen`

`batch`, `items[]`: `n`, `id`, `year`, `field`, `source`, `sections`, `text` (sections joined by one space — the
authority for evidence substrings). No title, authors or journal: generators and checkers never see them.
A batch split after a failed run is renamed `_gen_<NN>_unsplit.json.bak` and replaced by `gen_<NN>a…`.

## `src/generated/gen_<NN>[a-c].json` — written by a generator agent

`batch`, `prompt_version` (gen-v1 | gen-v2 | gen-v3 | gen-v4 | gen-v5 — the prompt file under `pipeline/prompts/`),
`items[]`: `n`, `id`, `statements[]` (exactly 4): `k` (1–4, stable id within the abstract), `label`, `evidence`
(character-exact substring of `text`, ≤ 300 chars), `note` (one sentence shown after answering), and the text in
one of three forms:
- `text` — gen-v1 (all labels), gen-v3/v4 supported and not_addressed statements;
- `basis` + `alter` {`from`, `to`, `kind` ∈ direction | group | magnitude | condition | significance} — gen-v2
  contradicted item; the shown text is `basis` with `from` → `to` applied once (`validate.compose`);
- `text` + `flip: true` — gen-v3: a true statement with exactly one direction word; the shown text has that word
  swapped by `validate.FLIP_PAIRS` and the item plays as `contradicted` (`validate.label_of`).
gen-v4 and gen-v5 files carry only true statements (3 supported + 1 not_addressed, no `flip`; v5 asks for a comparative
word whenever the abstract makes a comparison, D17); the pipeline marks one
supported statement (ascending `k`) as the flip (`validate.effective`), so the contradicted item is recomputed from
the file every time and stored nowhere else. Which one depends on the file's top-level `flip_rule`: absent /
`"exactly-one"` (first corpus) = the first with exactly one direction word from `FLIP_PAIRS`; `"first-of-any"`
(second corpus as first checked, D11) = the first with any direction word from the wider `FLIP_PAIRS_V2`, first
occurrence swapped; `"first-of-any-v2"` (second corpus as published, D13) = the same over eligible words only
(idioms, negated words and pairs whose opposite is present are skipped; "most X" → "few X", a/an fixed);
`"first-of-any-v3"` (third corpus on) = v2 plus "more" + adverb → "less". `flip_rule_history[]` keeps the rules a
file was on before. An abstract with no such statement has no contradicted item.

## `src/batches/check_<P>_<NN>.json` — `pipeline/make_batches.py check`

`batch`, `pass` (A | B | C | R), `source_batch` (`reflip:<rule>` for a re-check batch, D13), `supersedes` (true on a
re-check batch: its verdicts replace earlier ones for the same abstracts), `items[]`: the generator's view plus `statements[]` {`j` (shuffled
position 1–4, per pass, seeded), `k` (the generator's id), `text` (as the player will see it — composed/flipped)}.
No labels, notes or evidence.

## `src/checks/check_<P>_<NN>.json` — written by a checker agent

`batch`, `pass`, `prompt_version` (check-v1), `items[]`: `n`, `id`, `verdicts[]` {`j`, `label`, `confidence`
1–3, `evidence` (substring, optional), `flag` (absent | ambiguous | ill_formed), `reason` (with a flag)}.

## `src/items.json` — `pipeline/merge_checks.py`

`header`: `merged_utc`, `passes`, `rule` {min_votes 2, min_statements 3, drop_if}, `stats` {abstracts_generated,
abstracts_excluded, abstracts_kept, statements_generated, statements_kept, dropped {disagreement | ill_formed | ambiguous |
unchecked: n}, agreement {unanimous, majority}, kept_by_label, dropped_by_label, abstracts_dropped_too_few,
checker_label_agreement_pairwise {agree, differ}, kept_by_field, kept_by_source, statements_per_abstract}.
`items[]`: corpus metadata (`n`, `id`, `field`, `source`, `server`, `pmid`, `doi`, `title`, `authors`, `journal`,
`year`, `date`, `url`, `doi_url`, `sections`, `added` = label of the corpus addition or null, `text_repaired`),
`generated_by` (batch), `prompt_version`, `statements[]` {`k`,
`text` (as shown), `label` (as played), `evidence`, `note`, `agreement` (unanimous | majority), `checks` {A/B/C:
{label, confidence, flag}}, `alter` {kind, basis, from?, to?} for a composed or flipped item}.

## `docs/data.json` — `pipeline/build_site.py` (served by GitHub Pages from `/docs`)

`header`: `built`, `n_items`, `n_statements`, `by_field`, `by_source`, `years` ("2016–2026"), `merged_utc`,
`passes`, `rule`, `stats` (from items.json), `repo_url`, `site_url`, `top_journals`, `leading_journals[]` (display
names of the leading journals present) and `n_leading` (D23), `sources`, `generation`.
`items[]`: public fields only — `n`, `id`, `field`, `source`, `server`, `pmid`, `doi`, `title`, `authors`,
`journal` (display form, `journals.display`), `year`, `date`, `url`, `doi_url`, `sections`, `added`, `tier`
(`leading` for a journal article whose journal is in `pipeline/journals.py`, else null — the "Leading journals"
chip), `statements[]` {`k`, `text`, `label`, `evidence`, `note`, `agreement`, `altered` (kind, only on a
composed/flipped item)}. Checker details stay out.

## Browser storage (per viewer, never shared)

`ar.filt` {field, source (all | journal | leading | preprint), journal} · `ar.tally` {n, right, streak, best, byLabel} · `ar.seen` [item ids] ·
`ar.saved` [{id, n, title, authors[], journal, year, doi, url, source, saved_at}] — the reading list (D12) ·
`ar.prefs` {titleFirst} — show the title before answering (D19; default true since D23).
