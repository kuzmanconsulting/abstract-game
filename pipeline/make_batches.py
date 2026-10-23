#!/usr/bin/env python3
"""Split src/corpus.json into generation batches (src/batches/gen_NN.json) and, after generation, into blind check
batches (src/batches/check_<pass>_NN.json) in which the statements are shuffled and their labels removed.

    python3 pipeline/make_batches.py gen --size 35
    python3 pipeline/make_batches.py check --passes A B C --seed 7
    python3 pipeline/make_batches.py reflip --from-rule first-of-any --to-rule first-of-any-v2 --seed 7   # D13
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


def gen_batches(items, size, start=0, first_batch=0):
    """Batches for items[start:], numbered from first_batch — so a corpus extension gets new batch files and the
    existing ones (and their generated/checked outputs) are left alone."""
    os.makedirs(BATCH_DIR, exist_ok=True)
    names = []
    items = items[start:]
    for b in range(0, len(items), size):
        name = "gen_%02d" % (first_batch + b // size)
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
                sts = effective(g["statements"], gen.get("prompt_version"), gen.get("flip_rule", "exactly-one"))
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


def reflip(items, old_rule, new_rule, passes, seed, size=13, label="F", reflips_path=None):
    """Move every generated file on `old_rule` to `new_rule` (D13) and build fresh blind check batches, all passes,
    for the abstracts whose shown statements change under the new rule (`supersedes: true` — the merge takes these
    verdicts instead of the ones given on the old wording). Files already on new_rule are left alone; the list of
    re-flipped abstracts goes to src/reflips.json."""
    from validate import label_of
    by_n = {it["n"]: it for it in items}
    affected, kinds, files = [], {}, []
    for gf in sorted(f for f in os.listdir(GEN_DIR) if f.startswith("gen_") and f.endswith(".json")):
        path = os.path.join(GEN_DIR, gf)
        with open(path, encoding="utf-8") as f:
            gen = json.load(f)
        if gen.get("flip_rule", "exactly-one") != old_rule:
            continue
        for g in gen["items"]:
            a = {s["k"]: (compose(s)[0], label_of(s)) for s in effective(g["statements"], gen.get("prompt_version"), old_rule)}
            b = {s["k"]: (compose(s)[0], label_of(s)) for s in effective(g["statements"], gen.get("prompt_version"), new_rule)}
            if a != b:
                affected.append(g["n"])
                ka = [k for k, (_, l) in a.items() if l == "contradicted"]
                kb = [k for k, (_, l) in b.items() if l == "contradicted"]
                kinds[str(g["n"])] = "moved" if ka and kb and ka != kb else "dropped" if ka and not kb else "reworded"
        gen["flip_rule"] = new_rule
        gen["flip_rule_history"] = gen.get("flip_rule_history", []) + [old_rule]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(gen, f, ensure_ascii=False, indent=1)
        files.append(gf)
    gen_by_n = {}
    for gf in sorted(f for f in os.listdir(GEN_DIR) if f.startswith("gen_") and f.endswith(".json")):
        with open(os.path.join(GEN_DIR, gf), encoding="utf-8") as f:
            gen = json.load(f)
        for g in gen["items"]:
            gen_by_n[g["n"]] = (gen, g)
    affected = sorted(affected)
    names = []
    for b in range(0, len(affected), size):
        num = "%s%02d" % (label, b // size)
        for p in passes:
            rng = random.Random("%s:%s:%d" % (p, num, seed))
            out, jk = [], {}
            for n in affected[b:b + size]:
                gen, g = gen_by_n[n]
                sts = effective(g["statements"], gen.get("prompt_version"), gen.get("flip_rule"))
                order = list(range(len(sts)))
                rng.shuffle(order)
                out.append({**public_view(by_n[n]), "statements": [{"j": j + 1, "text": compose(sts[i])[0]} for j, i in enumerate(order)]})
                jk[str(n)] = {str(j + 1): sts[i]["k"] for j, i in enumerate(order)}
            name = "check_%s_%s" % (p, num)
            with open(os.path.join(BATCH_DIR, name + ".json"), "w", encoding="utf-8") as f:
                json.dump({"batch": name, "pass": p, "source_batch": "reflip:%s" % new_rule, "supersedes": True, "items": out}, f, ensure_ascii=False, indent=0)
            with open(os.path.join(BATCH_DIR, name + ".map.json"), "w", encoding="utf-8") as f:
                json.dump({"batch": name, "pass": p, "jk": jk}, f)
            names.append(name)
    if reflips_path:
        with open(reflips_path, "w", encoding="utf-8") as f:
            json.dump({"from_rule": old_rule, "to_rule": new_rule, "files": files, "n": affected, "count": len(affected), "kind": kinds,
                       "check_batches": names, "reason": "D13: swapped quantifiers, idioms and negations read as ill-formed; re-flipped and re-checked"}, f, indent=1)
    return affected, names


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["gen", "check", "reflip"])
    ap.add_argument("--from-rule", default="first-of-any")
    ap.add_argument("--to-rule", default="first-of-any-v2")
    ap.add_argument("--size", type=int, default=35)
    ap.add_argument("--passes", nargs="+", default=["A", "B", "C"])
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--force", action="store_true", help="check: rewrite existing check batch files")
    ap.add_argument("--start", type=int, default=0, help="gen: first corpus position to batch (extension runs)")
    ap.add_argument("--first-batch", type=int, default=0, help="gen: number of the first batch file written")
    a = ap.parse_args(argv)
    with open(CORPUS, encoding="utf-8") as f:
        items = json.load(f)["items"]
    if a.what == "reflip":
        affected, names = reflip(items, a.from_rule, a.to_rule, a.passes, a.seed, min(a.size, 13), reflips_path=os.path.join(ROOT, "src", "reflips.json"))
        print("%d abstracts re-flipped: %s" % (len(affected), affected))
    else:
        names = gen_batches(items, a.size, a.start, a.first_batch) if a.what == "gen" else check_batches(items, a.passes, a.seed, a.size, a.force)
    print("%d new batches%s" % (len(names), (": %s … %s" % (names[0], names[-1])) if names else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
