#!/usr/bin/env python3
"""Build docs/data.json from src/items.json: the public item set (what the page needs, nothing internal) plus a header
with provenance and counts. The page (docs/index.html) fetches it with a relative URL, so the same two files work on
GitHub Pages, as a published artifact (index + data.json as a supporting file) and under `python3 -m http.server`.

    python3 pipeline/build_site.py --repo-url https://github.com/<org>/abstract-game
"""
import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ITEMS = os.path.join(ROOT, "src", "items.json")
OUT = os.path.join(ROOT, "docs", "data.json")        # GitHub Pages (branch deploy) serves only / or /docs
PUBLIC_ITEM = ("n", "id", "field", "source", "server", "pmid", "doi", "title", "authors", "journal", "year", "date", "url", "doi_url", "sections", "added")
PUBLIC_STATEMENT = ("k", "text", "label", "evidence", "note", "agreement")


def public(item):
    out = {k: item.get(k) for k in PUBLIC_ITEM}
    out["statements"] = [{k: s.get(k) for k in PUBLIC_STATEMENT} for s in item["statements"]]
    for s, src in zip(out["statements"], item["statements"]):
        if src.get("alter"):
            s["altered"] = src["alter"].get("kind")      # what kind of change the contradicted item carries (shown after answering)
    return out


ARTIFACT = os.path.join(ROOT, "build", "artifact.html")
STRIP = ("<!doctype html>", '<html lang="en">', "<head>", "</head>", "<body>", "</body>", "</html>",
         '<meta charset="utf-8">', '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">')


def artifact_page(index_path=os.path.join(ROOT, "docs", "index.html"), out_path=ARTIFACT):
    """The same page as a body fragment for the claude.ai Artifact tool, which wraps it in its own document skeleton."""
    with open(index_path, encoding="utf-8") as f:
        html = f.read()
    for tag in STRIP:
        html = html.replace(tag + "\n", "").replace(tag, "")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html.lstrip("\n"))
    return out_path


def build(items_path=ITEMS, out_path=OUT, repo_url=None):
    with open(items_path, encoding="utf-8") as f:
        doc = json.load(f)
    items = [public(it) for it in doc["items"]]
    years = sorted({int(it["date"][:4]) if it.get("date") else it["year"] for it in items})
    header = {"built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "n_items": len(items),
              "n_statements": sum(len(it["statements"]) for it in items),
              "by_field": dict(Counter(it["field"] for it in items)), "by_source": dict(Counter(it["source"] for it in items)),
              "years": ("%d–%d" % (years[0], years[-1])) if years else None,
              "merged_utc": doc["header"].get("merged_utc"), "passes": doc["header"].get("passes"), "rule": doc["header"].get("rule"),
              "stats": doc["header"].get("stats"), "repo_url": repo_url,
              "top_journals": sorted({it["journal"] for it in doc["items"] if (it.get("added") or "").endswith("top2") or it.get("added") == "top-journals-2026-10-23"}) or None,
              "sources": "Europe PMC (SRC:MED journal articles; SRC:PPR bioRxiv/medRxiv preprints)",
              "generation": "Claude, prompts gen-v1/gen-v2; three independent blind check passes check-v1 (pipeline/prompts/)"}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"header": header, "items": items}, f, ensure_ascii=False, separators=(",", ":"))
    return header


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-url", default=None)
    ap.add_argument("--items", default=ITEMS)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    h = build(a.items, a.out, a.repo_url)
    print(json.dumps({k: h[k] for k in ("n_items", "n_statements", "by_field", "by_source", "years")}, indent=1))
    print("wrote", a.out, os.path.getsize(a.out), "bytes")
    print("wrote", artifact_page())
    return 0


if __name__ == "__main__":
    sys.exit(main())
