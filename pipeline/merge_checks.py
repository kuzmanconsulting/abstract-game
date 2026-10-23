#!/usr/bin/env python3
"""Merge the generator's statements with the three blind check passes into src/items.json (docs/DECISIONS.md D3).

Keep rule per statement: at least 2 of the 3 checkers give the generator's label, no checker flags it
`ill_formed`, and fewer than 2 flag it `ambiguous`. Agreement is recorded (unanimous / majority) together with
every checker's label and confidence, so a later tightening to unanimous-only is a filter, not a re-run.
Keep rule per abstract: at least 3 surviving statements.

    python3 pipeline/merge_checks.py --passes A B C
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from validate import compose, label_of, flip, effective  # noqa: E402
CORPUS = os.path.join(ROOT, "src", "corpus.json")
GEN_DIR = os.path.join(ROOT, "src", "generated")
CHECK_DIR = os.path.join(ROOT, "src", "checks")
BATCH_DIR = os.path.join(ROOT, "src", "batches")
OUT = os.path.join(ROOT, "src", "items.json")
MIN_STATEMENTS = 3
MIN_VOTES = 2


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_generated():
    gen = {}
    for name in sorted(os.listdir(GEN_DIR)):
        if name.startswith("gen_") and name.endswith(".json"):
            doc = load_json(os.path.join(GEN_DIR, name))
            for it in doc["items"]:
                gen[it["n"]] = {"batch": doc["batch"], "prompt_version": doc.get("prompt_version"), "flip_rule": doc.get("flip_rule", "exactly-one"),
                                "statements": it["statements"]}
    return gen


def load_checks(passes):
    """n -> pass -> k -> verdict  (the check batch file maps the shuffled j back to the generator's k)."""
    out = defaultdict(dict)
    batches = []
    for name in sorted(os.listdir(BATCH_DIR)):
        if not name.startswith("check_") or name.endswith(".map.json"):
            continue
        batch = load_json(os.path.join(BATCH_DIR, name))
        if batch["pass"] in passes and os.path.exists(os.path.join(CHECK_DIR, name)):
            batches.append((name, batch))
    # a superseding batch (re-flipped abstracts, D13) replaces the verdicts given on the earlier wording, so it is read last
    for name, batch in sorted(batches, key=lambda nb: bool(nb[1].get("supersedes"))):
        p = batch["pass"]
        doc = load_json(os.path.join(CHECK_DIR, name))
        jkmap = load_json(os.path.join(BATCH_DIR, name[:-5] + ".map.json"))["jk"]
        verdicts = {it["n"]: {v["j"]: v for v in it.get("verdicts", [])} for it in doc.get("items", [])}
        for it in batch["items"]:
            jk = {int(j): k for j, k in jkmap[str(it["n"])].items()}
            vs = verdicts.get(it["n"], {})
            if batch.get("supersedes") and it["n"] in out and p in out[it["n"]]:
                out[it["n"]].setdefault("_superseded", {})[p] = out[it["n"]][p]
            out[it["n"]][p] = {jk[j]: v for j, v in vs.items() if j in jk}
    return out


def decide(statement, checks, passes):
    labels = {p: (checks.get(p) or {}).get("label") for p in passes}
    confs = {p: (checks.get(p) or {}).get("confidence") for p in passes}
    flags = {p: (checks.get(p) or {}).get("flag") for p in passes}
    votes = sum(1 for p in passes if labels[p] == statement["label"])
    n_checked = sum(1 for p in passes if labels[p] is not None)
    ill = any(flags[p] == "ill_formed" for p in passes)
    amb = sum(1 for p in passes if flags[p] == "ambiguous")
    keep = n_checked == len(passes) and votes >= MIN_VOTES and not ill and amb < 2
    why = None if keep else ("unchecked" if n_checked < len(passes) else "ill_formed" if ill else "ambiguous" if amb >= 2 else "disagreement")
    return {"keep": keep, "why_dropped": why, "votes": votes, "agreement": "unanimous" if votes == len(passes) else "majority" if keep else None,
            "checks": {p: {"label": labels[p], "confidence": confs[p], "flag": flags[p]} for p in passes}}


def merge(passes, repair_pass="R"):
    corpus = {it["n"]: it for it in load_json(CORPUS)["items"]}
    gen = load_generated()
    checks = load_checks(list(passes) + ([repair_pass] if repair_pass else []))
    items, stats = [], {"abstracts_generated": len(gen), "abstracts_kept": 0, "statements_generated": 0, "statements_kept": 0,
                        "dropped": Counter(), "agreement": Counter(), "kept_by_label": Counter(), "dropped_by_label": Counter(),
                        "abstracts_dropped_too_few": 0, "checker_label_agreement_pairwise": Counter()}
    stats["abstracts_excluded"] = 0
    for n in sorted(gen):
        src = corpus[n]
        if src.get("excluded"):                                # D14: off-topic abstracts marked in the corpus
            stats["abstracts_excluded"] += 1
            continue
        kept = []
        for s in effective(gen[n]["statements"], gen[n]["prompt_version"], gen[n]["flip_rule"]):
            stats["statements_generated"] += 1
            s = dict(s, label=label_of(s))                       # a gen-v3 flip statement plays as the contradicted item
            d = decide(s, {p: (checks.get(n, {}).get(p) or {}).get(s["k"], {}) for p in passes}, passes)
            if src.get("text_repaired") and repair_pass:          # D8: a repaired abstract also needs the re-check pass to agree
                r = (checks.get(n, {}).get(repair_pass) or {}).get(s["k"], {})
                d["checks"][repair_pass] = {"label": r.get("label"), "confidence": r.get("confidence"), "flag": r.get("flag")}
                if r.get("label") != s["label"] or r.get("flag") == "ill_formed":
                    if d["keep"]:
                        d["keep"], d["why_dropped"], d["agreement"] = False, ("unchecked" if r.get("label") is None else "repair_recheck"), None
            labs = [d["checks"][p]["label"] for p in passes]
            for i in range(len(passes)):
                for j in range(i + 1, len(passes)):
                    stats["checker_label_agreement_pairwise"]["agree" if labs[i] == labs[j] else "differ"] += 1
            if d["keep"]:
                stats["statements_kept"] += 1
                stats["agreement"][d["agreement"]] += 1
                stats["kept_by_label"][s["label"]] += 1
                row = {"k": s["k"], "text": compose(s)[0], "label": s["label"], "evidence": s["evidence"], "note": s.get("note"),
                       "agreement": d["agreement"], "checks": d["checks"]}
                if s.get("alter"):
                    row["alter"] = {"kind": (s["alter"] or {}).get("kind"), "basis": s.get("basis")}
                elif s.get("flip"):
                    _, w_from, w_to, _ = flip(s["text"], s.get("flip_rule", "exactly-one"))
                    row["alter"] = {"kind": "direction", "basis": s["text"], "from": w_from, "to": w_to}
                kept.append(row)
            else:
                stats["dropped"][d["why_dropped"]] += 1
                stats["dropped_by_label"][s["label"]] += 1
        if len(kept) < MIN_STATEMENTS:
            stats["abstracts_dropped_too_few"] += 1
            continue
        stats["abstracts_kept"] += 1
        items.append({"n": n, "id": src["id"], "field": src["field"], "source": src["source"], "server": src.get("server"), "text_repaired": bool(src.get("text_repaired")), "added": src.get("added"),
                      "pmid": src.get("pmid"), "doi": src.get("doi"), "title": src["title"], "authors": src["authors"],
                      "journal": src["journal"], "year": src["year"], "date": src.get("date"), "url": src.get("url"), "doi_url": src.get("doi_url"),
                      "sections": src["sections"], "generated_by": gen[n]["batch"], "prompt_version": gen[n]["prompt_version"],
                      "statements": kept})
    # did generators shuffle labels over k? share of abstracts per batch whose label-by-k pattern equals the batch's
    # most common pattern (1.0 = every abstract the same order). Checkers never saw labels, and from the stripped
    # batches not k either; the passes run before 14:55 saw k, so this is the size of that possible leak.
    pat = defaultdict(Counter)
    for n, g in gen.items():
        sts = effective(g["statements"], g["prompt_version"], g["flip_rule"])
        pat[g["batch"]][tuple(label_of(s) for s in sorted(sts, key=lambda x: x["k"]))] += 1
    stats["k_order_leak"] = {b: round(c.most_common(1)[0][1] / sum(c.values()), 2) for b, c in sorted(pat.items())}
    stats = {k: (dict(v) if isinstance(v, Counter) else v) for k, v in stats.items()}
    stats["kept_by_field"] = dict(Counter(it["field"] for it in items))
    stats["kept_by_source"] = dict(Counter(it["source"] for it in items))
    stats["statements_per_abstract"] = dict(Counter(len(it["statements"]) for it in items))
    return items, stats


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", nargs="+", default=["A", "B", "C"])
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    items, stats = merge(a.passes)
    header = {"merged_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "passes": a.passes, "rule": {"min_votes": MIN_VOTES, "min_statements": MIN_STATEMENTS,
              "drop_if": ["any ill_formed", ">=2 ambiguous", "fewer than 3 checks", "repaired abstract: pass R disagrees"]}, "stats": stats}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"header": header, "items": items}, f, ensure_ascii=False, indent=0)
    print(json.dumps(stats, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
