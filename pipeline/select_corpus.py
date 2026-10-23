#!/usr/bin/env python3
"""Pick the generation corpus from src/candidates.json: N abstracts, equal thirds per field, a fixed preprint share
inside each field, spread over the years, seeded. Titles are deduplicated across sources so a preprint and its
later journal version cannot both be drawn.

    python3 pipeline/select_corpus.py --n 560 --preprint-share 0.3 --seed 20261023
"""
import argparse
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CANDIDATES = os.path.join(ROOT, "src", "candidates.json")
OUT = os.path.join(ROOT, "src", "corpus.json")


def title_key(t):
    return re.sub(r"[^a-z0-9]+", "", (t or "").lower())[:80]


def spread_pick(pool, k, rng):
    """k items from pool, cycling over years so no year dominates; random within a year."""
    by_year = defaultdict(list)
    for c in pool:
        by_year[c["year"]].append(c)
    for lst in by_year.values():
        rng.shuffle(lst)
    years = sorted(by_year)
    out = []
    while len(out) < k and any(by_year[y] for y in years):
        for y in years:
            if by_year[y] and len(out) < k:
                out.append(by_year[y].pop())
    return out


def select(candidates, n, preprint_share, seed):
    rng = random.Random(seed)
    seen_titles, uniq = set(), []
    for c in sorted(candidates, key=lambda c: (c["source"] != "journal", c["id"])):   # journal version wins over its preprint
        k = title_key(c["title"])
        if k in seen_titles:
            continue
        seen_titles.add(k)
        uniq.append(c)
    fields = sorted({c["field"] for c in uniq})
    per_field = [n // len(fields) + (1 if i < n % len(fields) else 0) for i in range(len(fields))]
    chosen = []
    for field, quota in zip(fields, per_field):
        pool = [c for c in uniq if c["field"] == field]
        n_pre = round(quota * preprint_share)
        pre = spread_pick([c for c in pool if c["source"] == "preprint"], n_pre, rng)
        jour = spread_pick([c for c in pool if c["source"] == "journal"], quota - len(pre), rng)
        chosen.extend(pre + jour)
    rng.shuffle(chosen)
    for i, c in enumerate(chosen):
        c["n"] = i
    return chosen, len(candidates) - len(uniq)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=560)
    ap.add_argument("--preprint-share", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=20261023)
    ap.add_argument("--candidates", default=CANDIDATES)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    with open(a.candidates, encoding="utf-8") as f:
        cand = json.load(f)
    chosen, dup_titles = select(cand["candidates"], a.n, a.preprint_share, a.seed)
    stats = {"n": len(chosen), "by_field": dict(Counter(c["field"] for c in chosen)), "by_source": dict(Counter(c["source"] for c in chosen)),
             "by_year": dict(sorted(Counter(c["year"] for c in chosen).items())), "by_server": dict(Counter(c["server"] for c in chosen if c["server"])),
             "structured": sum(1 for c in chosen if c["structured"]), "title_duplicates_removed": dup_titles}
    header = {"selected_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "seed": a.seed, "n": a.n, "preprint_share": a.preprint_share,
              "candidates_fetched_utc": cand["header"]["fetched_utc"], "stats": stats}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"header": header, "items": chosen}, f, ensure_ascii=False, indent=0)
    print(json.dumps(stats, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
