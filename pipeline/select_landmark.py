#!/usr/bin/env python3
"""Landmark papers (D18): the most-cited primary research papers of the last ten years in each field.

Step 1 — shortlist (this script, rule-based, reproducible):
    python3 pipeline/select_landmark.py shortlist --candidates src/candidates_landmark.json --per-field 70
  From the citation-sorted candidates (fetch_candidates.py --sort cited), drop what is already in the corpus, drop
  tool/database/resource papers by title pattern, require a field term in the title or two in the abstract, and keep
  the top N per field by Europe PMC citedByCount → src/landmark_shortlist.json (rank, citations, year, journal,
  title, first 400 characters of the abstract, id).

Step 2 — curation (one agent per field, pipeline/prompts/landmark-v1.md): from the shortlist pick the 40 most
  important primary research papers for the field, excluding anything the regex missed (tools, resources, reviews,
  off-field) → src/landmark_pick_<field>.json {"field", "keep": [ids], "drop": [{"id", "reason"}]}.

Step 3 — apply:
    python3 pipeline/select_landmark.py apply --label landmark-2016-2026
  Appends the picked candidates to src/corpus.json (new n, `added` label, `cited_by` kept) and records the picks in
  the corpus header.
"""
import argparse
import glob
import json
import os
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from select_corpus import title_key, spread_pick  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("fetch_candidates", os.path.join(HERE, "fetch_candidates.py"))
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)

CORPUS = os.path.join(ROOT, "src", "corpus.json")
SHORTLIST = os.path.join(ROOT, "src", "landmark_shortlist.json")
PICK = os.path.join(ROOT, "src", "landmark_pick_%s.json")

# software, databases, web servers, resources, benchmarks — highly cited, but not findings about the field
TOOL_TITLE = re.compile(r"\b(v\d+(\.\d+)?|\d+\.\d+|version|release|update|database|web server|webserver|server|portal|resource|"
                        r"software|program|package|toolkit|tool|tools|pipeline|workflow|framework|platform|browser|catalog|catalogue|"
                        r"encyclop(a)?edia|compendium|atlas|benchmark|benchmarking|algorithm|approximation|annotation|annotating|"
                        r"user[- ]friendly|open[- ]access|implementation|guidelines?|recommendations?|consensus statement|"
                        r"protocol|standard|standards|best practices?|r package|python|bioconductor)\b", re.I)
TOOL_NAME_COLON = re.compile(r"^[A-Za-z0-9_.+-]{2,25}\s*[:—-]\s")   # "RepeatModeler2: automated …", "TIMER: a web server …"


def field_terms(field):
    out = []
    for t in fc.FIELDS[field]["terms"]:
        t = t.strip('"').rstrip("*").lower()
        if t:
            out.append(t)
    return out


def relevant(c, terms):
    title = (c.get("title") or "").lower()
    text = " ".join(s["text"] for s in c["sections"]).lower()
    in_title = any(t in title for t in terms)
    hits = sum(1 for t in terms if t in text)
    return in_title or hits >= 2


def qfield(c):
    """The query a candidate was fetched under (fetch_candidates FIELDS key); differs from c["field"] when the query maps
    onto another field with "as" (rnadev → smallrna, D23)."""
    return c.get("query_field") or c["field"]


def shortlist(candidates_path, per_field, out=SHORTLIST, sample_seed=None, split_dir=None):
    """sample_seed=None: the top per_field by citations (landmark, D18). With a seed: a seeded year-spread sample of per_field
    from the filtered pool instead (D23: a relevance-ranked pool from leading journals, curated afterwards by an agent)."""
    with open(candidates_path, encoding="utf-8") as f:
        cand = json.load(f)["candidates"]
    with open(CORPUS, encoding="utf-8") as f:
        corpus = json.load(f)
    have_ids = {it["id"] for it in corpus["items"]}
    have_titles = {title_key(it["title"]) for it in corpus["items"]}
    result, dropped = {}, Counter()
    for field in sorted({qfield(c) for c in cand}):
        terms = field_terms(field)
        pool = []
        for c in cand:
            if qfield(c) != field:
                continue
            if c["id"] in have_ids or title_key(c["title"]) in have_titles:
                dropped["in_corpus"] += 1
                continue
            if TOOL_TITLE.search(c["title"] or "") or TOOL_NAME_COLON.match(c["title"] or ""):
                dropped["tool_title"] += 1
                continue
            if not relevant(c, terms):
                dropped["off_field"] += 1
                continue
            pool.append(c)
        if sample_seed is None:
            pool.sort(key=lambda c: -(c.get("cited_by") or 0))
            picked = pool[:per_field]
        else:
            picked = spread_pick(pool, per_field, random.Random(sample_seed), "year")
            picked.sort(key=lambda c: (c["year"], c["id"]))
        result[field] = [{"rank": i + 1, "id": c["id"], "cited_by": c.get("cited_by"), "year": c["year"], "journal": c["journal"],
                          "title": c["title"], "abstract_start": " ".join(s["text"] for s in c["sections"])[:400]}
                         for i, c in enumerate(picked)]
    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"built_utc": built, "candidates": os.path.relpath(candidates_path, ROOT), "per_field": per_field,
                   "sample_seed": sample_seed, "dropped": dict(dropped), "fields": result}, f, ensure_ascii=False, indent=1)
    if split_dir:                                   # one file per field for the curation agents
        os.makedirs(split_dir, exist_ok=True)
        for field, rows in result.items():
            with open(os.path.join(split_dir, "shortlist_%s.json" % field), "w", encoding="utf-8") as f:
                json.dump({"field": field, "built_utc": built, "items": rows}, f, ensure_ascii=False, indent=1)
    return result, dropped


def apply(candidates_path, label, n_per_field=40, pick_glob=None, method=None):
    with open(candidates_path, encoding="utf-8") as f:
        rows = json.load(f)["candidates"]
    cand = {(qfield(c), c["id"]): c for c in rows}          # a paper can be a candidate in two fields; the pick's field wins
    any_field = {c["id"]: c for c in rows}
    with open(CORPUS, encoding="utf-8") as f:
        corpus = json.load(f)
    have_ids = {it["id"] for it in corpus["items"]}
    have_titles = {title_key(it["title"]) for it in corpus["items"]}
    start = len(corpus["items"])
    added, picks = [], {}
    for path in sorted(glob.glob(pick_glob or (PICK % "*"))):
        with open(path, encoding="utf-8") as f:
            pick = json.load(f)
        field = pick["field"]                                # the query field; the corpus field follows FIELDS[...]["as"]
        keep = [i for i in pick["keep"] if i in any_field and i not in have_ids and title_key(any_field[i]["title"]) not in have_titles][:n_per_field]
        picks[field] = {"keep": keep, "drop": pick.get("drop", []), "file": os.path.relpath(path, ROOT)}
        for i in keep:
            c = dict(cand.get((field, i)) or any_field[i])
            c["query_field"] = field
            c["field"] = fc.FIELDS.get(field, {}).get("as", field)
            c["n"] = start + len(added)
            c["added"] = label
            added.append(c)
            have_ids.add(i)
            have_titles.add(title_key(c["title"]))
    corpus["items"].extend(added)
    corpus["header"].setdefault("additions", []).append({"label": label, "selected_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                         "n": len(added), "fields": sorted(picks), "method": method or ("most-cited 2016–2026 (Europe PMC CITED desc), "
                                                         "rule shortlist + agent curation (D18)"), "picks": picks,
                                                         "n_range": [start, start + len(added) - 1] if added else None})
    with open(CORPUS, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=0)
    return added


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["shortlist", "apply"])
    ap.add_argument("--candidates", default=os.path.join(ROOT, "src", "candidates_landmark.json"))
    ap.add_argument("--per-field", type=int, default=70)
    ap.add_argument("--n", type=int, default=40, help="apply: picks taken per field")
    ap.add_argument("--label", default="landmark-2016-2026")
    ap.add_argument("--out", default=SHORTLIST, help="shortlist: the combined shortlist file")
    ap.add_argument("--split-dir", default=None, help="shortlist: also write one shortlist_<field>.json per field here")
    ap.add_argument("--sample-seed", type=int, default=None, help="shortlist: a seeded year-spread sample instead of the most-cited (D23)")
    ap.add_argument("--pick-glob", default=None, help="apply: the pick files (default src/landmark_pick_*.json)")
    ap.add_argument("--method", default=None, help="apply: the method text recorded in the corpus header")
    a = ap.parse_args(argv)
    if a.what == "shortlist":
        result, dropped = shortlist(a.candidates, a.per_field, a.out, a.sample_seed, a.split_dir)
        print(json.dumps({f: len(v) for f, v in result.items()}), dict(dropped))
    else:
        added = apply(a.candidates, a.label, a.n, a.pick_glob, a.method)
        print(json.dumps({"added": len(added), "by_field": dict(Counter(c["field"] for c in added)),
                          "by_year": dict(sorted(Counter(c["year"] for c in added).items())),
                          "by_journal": dict(Counter(c["journal"] for c in added).most_common(10))}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
