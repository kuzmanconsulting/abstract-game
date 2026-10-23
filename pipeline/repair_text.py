#!/usr/bin/env python3
"""Repair corpus abstracts damaged by the first tag stripper (DECISIONS D8): re-parse them from the raw Europe PMC
records with the fixed parser, keep the damaged text beside the repaired one (`text_before_repair`,
`text_repaired: true`), write src/repairs.json, and build one extra blind check batch per 30 repaired abstracts
(pass "R", src/batches/check_R_NN.json + .map.json) from the generated statements — the merge then requires
pass R to agree as well for these abstracts.

    python3 pipeline/repair_text.py
"""
import glob
import importlib.util
import json
import os
import random
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from validate import compose, effective  # noqa: E402

spec = importlib.util.spec_from_file_location("fetch_candidates", os.path.join(HERE, "fetch_candidates.py"))
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)

CORPUS = os.path.join(ROOT, "src", "corpus.json")
RAW_DIR = os.path.join(ROOT, "src", "raw")
GEN_DIR = os.path.join(ROOT, "src", "generated")
BATCH_DIR = os.path.join(ROOT, "src", "batches")
REPAIRS = os.path.join(ROOT, "src", "repairs.json")


def joined(sections):
    return " ".join(s["text"] for s in sections)


def repair(corpus_path=CORPUS, raw_dir=RAW_DIR, out_repairs=REPAIRS, size=30, seed=11):
    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)
    raw = {}
    for path in glob.glob(os.path.join(raw_dir, "*.json")):
        with open(path, encoding="utf-8") as f:
            for r in json.load(f):
                raw[r.get("id")] = r
    repaired = []
    for it in corpus["items"]:
        rec = raw.get(it["epmc_id"])
        if not rec:
            continue
        new = fc.parse_abstract(rec.get("abstractText"))
        if joined(new) != joined(it["sections"]):
            if "text_before_repair" not in it:
                it["text_before_repair"] = joined(it["sections"])
            it["sections"] = new
            it["n_chars"] = len(joined(new))
            it["text_repaired"] = True
            repaired.append(it["n"])
    corpus["header"]["repaired_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    corpus["header"]["repaired_n"] = sorted(set(corpus["header"].get("repaired_n", []) + repaired))
    with open(corpus_path, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=0)
    with open(out_repairs, "w", encoding="utf-8") as f:
        json.dump({"repaired_utc": corpus["header"]["repaired_utc"], "n": repaired, "count": len(repaired),
                   "reason": "first parser deleted text between a bare '<' and the next '>' (D8)"}, f, indent=0)
    return corpus, repaired


def check_batches_for(corpus, ns, size=30, seed=11, pass_name="R"):
    """Blind check batches (pass R) for the repaired abstracts, from the generated statements, on the repaired text."""
    by_n = {it["n"]: it for it in corpus["items"]}
    gen = {}
    for path in sorted(glob.glob(os.path.join(GEN_DIR, "gen_*.json"))):
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        for it in doc["items"]:
            gen[it["n"]] = (doc.get("prompt_version"), it["statements"])
    names = []
    ns = sorted(ns)
    for b in range(0, len(ns), size):
        name = "check_%s_%02d" % (pass_name, b // size)
        rng = random.Random("%s:%d:%d" % (pass_name, b, seed))
        out, jk = [], {}
        for n in ns[b:b + size]:
            it = by_n[n]
            version, statements = gen[n]
            sts = effective(statements, version)
            order = list(range(len(sts)))
            rng.shuffle(order)
            out.append({"n": n, "id": it["id"], "year": it["year"], "field": it["field"], "source": it["source"],
                        "sections": it["sections"], "text": joined(it["sections"]),
                        "statements": [{"j": j + 1, "text": compose(sts[i])[0]} for j, i in enumerate(order)]})
            jk[str(n)] = {str(j + 1): sts[i]["k"] for j, i in enumerate(order)}
        with open(os.path.join(BATCH_DIR, name + ".json"), "w", encoding="utf-8") as f:
            json.dump({"batch": name, "pass": pass_name, "source_batch": "repaired", "items": out}, f, ensure_ascii=False, indent=0)
        with open(os.path.join(BATCH_DIR, name + ".map.json"), "w", encoding="utf-8") as f:
            json.dump({"batch": name, "pass": pass_name, "jk": jk}, f)
        names.append(name)
    return names


if __name__ == "__main__":
    corpus, ns = repair()
    print("repaired %d abstracts" % len(ns))
    print("check batches:", check_batches_for(corpus, ns))
