#!/usr/bin/env python3
"""Split src/corpus.json into generation batches (src/batches/gen_NN.json) and, after generation, into blind check
batches (src/batches/check_<pass>_NN.json) in which the statements are shuffled and their labels removed.

    python3 pipeline/make_batches.py gen --size 35
    python3 pipeline/make_batches.py check --passes A B C --seed 7
"""
import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CORPUS = os.path.join(ROOT, "src", "corpus.json")
BATCH_DIR = os.path.join(ROOT, "src", "batches")
GEN_DIR = os.path.join(ROOT, "src", "generated")
sys.path.insert(0, HERE)
from validate import compose, effective  # noqa: E402  (gen-v2 altered statements are composed from basis + alter; gen-v4 flips are chosen here)


def abstract_text(item):
    return " ".join(s["text"] for s in item["sections"])


def public_view(item):
    """What a generator or checker sees: no title, no authors, no journal — only the text and the year/field."""
    return {"n": item["n"], "id": item["id"], "year": item["year"], "field": item["field"], "source": item["source"],
            "sections": item["sections"], "text": abstract_text(item)}


def gen_batches(items, size):
    os.makedirs(BATCH_DIR, exist_ok=True)
    names = []
    for b in range(0, len(items), size):
        name = "gen_%02d" % (b // size)
        with open(os.path.join(BATCH_DIR, name + ".json"), "w", encoding="utf-8") as f:
            json.dump({"batch": name, "items": [public_view(it) for it in items[b:b + size]]}, f, ensure_ascii=False, indent=0)
        names.append(name)
    return names


def check_batches(items, passes, seed, size, force=False):
    """One check batch per generation batch and pass; statements shuffled per pass, labels/notes/evidence removed.
    Existing check batch files are left alone unless force (a checker may be reading them)."""
    by_n = {it["n"]: it for it in items}
    os.makedirs(BATCH_DIR, exist_ok=True)
    names = []
    gen_files = sorted(f for f in os.listdir(GEN_DIR) if f.startswith("gen_") and f.endswith(".json"))
    for gf in gen_files:
        with open(os.path.join(GEN_DIR, gf), encoding="utf-8") as f:
            gen = json.load(f)
        num = gf[len("gen_"):-len(".json")]
        for p in passes:
            rng = random.Random("%s:%s:%d" % (p, num, seed))
            out, jk = [], {}
            for g in gen["items"]:
                it = by_n[g["n"]]
                sts = effective(g["statements"], gen.get("prompt_version"))
                order = list(range(len(sts)))
                rng.shuffle(order)
                # the checker gets j and text only; the j -> k mapping goes to a side file it never reads (k is the
                # generator's id and, when a generator did not shuffle, correlates with the label)
                out.append({**public_view(it), "statements": [{"j": j + 1, "text": compose(sts[i])[0]} for j, i in enumerate(order)]})
                jk[str(g["n"])] = {str(j + 1): sts[i]["k"] for j, i in enumerate(order)}
            name = "check_%s_%s" % (p, num)
            path = os.path.join(BATCH_DIR, name + ".json")
            if os.path.exists(path) and not force:
                continue
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"batch": name, "pass": p, "source_batch": gen["batch"], "items": out}, f, ensure_ascii=False, indent=0)
            with open(os.path.join(BATCH_DIR, name + ".map.json"), "w", encoding="utf-8") as f:
                json.dump({"batch": name, "pass": p, "jk": jk}, f)
            names.append(name)
    return names


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["gen", "check"])
    ap.add_argument("--size", type=int, default=35)
    ap.add_argument("--passes", nargs="+", default=["A", "B", "C"])
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--force", action="store_true", help="check: rewrite existing check batch files")
    a = ap.parse_args(argv)
    with open(CORPUS, encoding="utf-8") as f:
        items = json.load(f)["items"]
    names = gen_batches(items, a.size) if a.what == "gen" else check_batches(items, a.passes, a.seed, a.size, a.force)
    print("%d new batches%s" % (len(names), (": %s … %s" % (names[0], names[-1])) if names else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
