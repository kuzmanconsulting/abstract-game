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
sys.path.insert(0, HERE)
import journals  # noqa: E402  (pipeline/journals.py: the leading-journal list and display names, D23)
ITEMS = os.path.join(ROOT, "src", "items.json")
OUT = os.path.join(ROOT, "docs", "data.json")        # GitHub Pages (branch deploy) serves only / or /docs
# PubMed's catalogue title for the picker and the citation; the corpus keeps the raw string
JOURNAL_DISPLAY = {"Science (New York, N.Y.)": "Science"}     # superseded by journals.display() (D23); kept for the header's top_journals
PUBLIC_ITEM = ("n", "id", "field", "source", "server", "pmid", "doi", "title", "authors", "journal", "year", "date", "url", "doi_url", "sections", "added", "tags")
PUBLIC_STATEMENT = ("k", "text", "label", "evidence", "note", "agreement")


def public(item):
    out = {k: item.get(k) for k in PUBLIC_ITEM}
    out["journal"] = journals.display(out["journal"]) if out.get("journal") else out.get("journal")
    out["tier"] = "leading" if item.get("source") == "journal" and journals.is_leading(item.get("journal")) else None   # D23: the page's "Leading journals" filter
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
    import re
    with open(index_path, encoding="utf-8") as f:
        html = f.read()
    # the SEO/social/PWA head block is for the GitHub Pages site only (absolute github.io URLs, a manifest and icons
    # that are not published beside the artifact); drop it from the artifact body fragment.
    html = re.sub(r"<!--PAGES-ONLY.*?<!--/PAGES-ONLY-->\s*", "", html, flags=re.S)
    for tag in STRIP:
        html = html.replace(tag + "\n", "").replace(tag, "")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html.lstrip("\n"))
    return out_path


def site_url_from(repo_url):
    """https://github.com/<owner>/<repo> -> https://<owner>.github.io/<repo>/ (the GitHub Pages address on the share card)."""
    import re
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url or "")
    return "https://%s.github.io/%s/" % (m.group(1).lower(), m.group(2)) if m else None


def build(items_path=ITEMS, out_path=OUT, repo_url=None):
    with open(items_path, encoding="utf-8") as f:
        doc = json.load(f)
    items = [public(it) for it in doc["items"]]
    years = sorted({int(it["date"][:4]) if it.get("date") else it["year"] for it in items})
    header = {"built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "n_items": len(items),
              "n_statements": sum(len(it["statements"]) for it in items),
              "by_field": dict(Counter(it["field"] for it in items)), "by_source": dict(Counter(it["source"] for it in items)),
              "by_tag": dict(Counter(t for it in items for t in (it.get("tags") or []))),
              "years": ("%d–%d" % (years[0], years[-1])) if years else None,
              "merged_utc": doc["header"].get("merged_utc"), "passes": doc["header"].get("passes"), "rule": doc["header"].get("rule"),
              "stats": doc["header"].get("stats"), "repo_url": repo_url, "site_url": site_url_from(repo_url),
              "top_journals": sorted({journals.display(it["journal"]) for it in doc["items"] if (it.get("added") or "").endswith("top2") or it.get("added") == "top-journals-2026-10-23"}) or None,
              "leading_journals": sorted({it["journal"] for it in items if it.get("tier") == "leading"}),       # the curated list's members present in the corpus (D23)
              "n_leading": sum(1 for it in items if it.get("tier") == "leading"),
              "sources": "Europe PMC (SRC:MED journal articles; SRC:PPR bioRxiv/medRxiv preprints)",
              "generation": "Claude, prompts gen-v1/gen-v2; three independent blind check passes check-v1 (pipeline/prompts/)"}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"header": header, "items": items}, f, ensure_ascii=False, separators=(",", ":"))
    # a small, representative slice for instant first paint; the page loads this first, then swaps in the full set.
    # Stratified across fields so the first abstract and the field chips look right before the full corpus arrives.
    import random
    by_field = {}
    for it in items:
        by_field.setdefault(it["field"], []).append(it)
    rng = random.Random(42)
    lite = []
    for f_key in sorted(by_field):
        s = by_field[f_key][:]
        rng.shuffle(s)
        lite.extend(s[:8])
    rng.shuffle(lite)
    lite_header = dict(header)
    lite_header["lite"] = True
    lite_header["n_items_lite"] = len(lite)
    lite_path = os.path.join(os.path.dirname(out_path), "data-lite.json")
    with open(lite_path, "w", encoding="utf-8") as f:
        json.dump({"header": lite_header, "items": lite}, f, ensure_ascii=False, separators=(",", ":"))
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
