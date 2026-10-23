#!/usr/bin/env python3
"""Validate generated and check files against the corpus and the schema (docs/SCHEMA.md).

    python3 pipeline/validate.py gen            # every src/generated/gen_NN.json
    python3 pipeline/validate.py check          # every src/checks/check_<pass>_NN.json
Exit 1 when any file has a fatal problem; warnings are printed but do not fail.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CORPUS = os.path.join(ROOT, "src", "corpus.json")
GEN_DIR = os.path.join(ROOT, "src", "generated")
CHECK_DIR = os.path.join(ROOT, "src", "checks")
BATCH_DIR = os.path.join(ROOT, "src", "batches")
LABELS = ("supported", "contradicted", "not_addressed")
MIX = Counter({"supported": 2, "contradicted": 1, "not_addressed": 1})
MAX_WORDS = 32
MAX_EVIDENCE = 320


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def load_corpus():
    with open(CORPUS, encoding="utf-8") as f:
        items = json.load(f)["items"]
    return {it["n"]: it for it in items}


def text_of(item):
    return " ".join(s["text"] for s in item["sections"])


# gen-v3: the pipeline makes the contradicted item itself by swapping one direction word in a true statement the
# generator marked with "flip": true. Pairs are symmetric; the model never writes an altered sentence.
FLIP_PAIRS = [("higher", "lower"), ("greater", "smaller"), ("increased", "decreased"), ("increase", "decrease"), ("increases", "decreases"),
              ("longer", "shorter"), ("enriched", "depleted"), ("upregulated", "downregulated"), ("overexpressed", "underexpressed"),
              ("positively", "negatively"), ("improved", "worsened"), ("elevated", "reduced"), ("faster", "slower"), ("earlier", "later"),
              ("hypermethylated", "hypomethylated"), ("hypermethylation", "hypomethylation"), ("superior", "inferior"),
              ("outperformed", "underperformed"), ("gained", "lost"), ("more", "fewer"), ("above", "below")]
FLIP = {}
for _a, _b in FLIP_PAIRS:
    FLIP[_a] = _b
    FLIP[_b] = _a
FLIP_RE = re.compile(r"\b(" + "|".join(sorted(FLIP, key=len, reverse=True)) + r")\b", re.I)


def flip_words(text):
    return [m for m in FLIP_RE.finditer(text or "")]


# "more" before an adjective or adverb flips to "less" ("more accurate" -> "less accurate"), before a noun to "fewer"
ADJ_AFTER_MORE = {"accurate", "sensitive", "specific", "likely", "frequent", "common", "abundant", "stable", "severe", "efficient",
                  "effective", "precise", "robust", "pronounced", "prevalent", "rapid", "often", "variable", "diverse", "complex",
                  "aggressive", "active", "conserved", "similar", "distinct", "heterogeneous", "homogeneous", "informative", "reliable",
                  "consistent", "strongly", "closely", "highly", "than"}


def flip(text):
    """Swap the single direction word in text for its opposite, keeping capitalisation. Returns (flipped, from, to, error)."""
    hits = flip_words(text)
    if len(hits) != 1:
        return None, None, None, "flip statement has %d direction words (needs exactly 1)" % len(hits)
    m = hits[0]
    w = m.group(1)
    rep = FLIP[w.lower()]
    if w.lower() == "more":
        nxt = re.match(r"\s+([A-Za-z-]+)", text[m.end():])
        nw = nxt.group(1).lower() if nxt else ""
        if nw in ADJ_AFTER_MORE or nw.endswith("ly"):
            rep = "less"
    if w[0].isupper():
        rep = rep[0].upper() + rep[1:]
    return text[:m.start()] + rep + text[m.end():], w, rep, None


def effective(statements, prompt_version):
    """The statements as the game plays them. gen-v4 writes only true statements; the pipeline turns the first supported
    one (by k) that carries exactly one direction word into the contradicted item by marking it flip (deterministic,
    recorded nowhere else — recomputed from the generated file every time). Other versions pass through."""
    out = [dict(s) for s in statements]
    if prompt_version == "gen-v4":
        for s in sorted(out, key=lambda x: x.get("k", 0)):
            if s.get("label") == "supported" and len(flip_words(s.get("text") or "")) == 1:
                s["flip"] = True
                break
    return out


def label_of(statement):
    """The label a statement carries in the game: a gen-v3 flip statement is the contradicted item."""
    return "contradicted" if statement.get("flip") else statement.get("label")


def compose(statement):
    """The statement text the player sees. gen-v1: text as written. gen-v2: basis with alter.from -> alter.to applied
    once. gen-v3 flip statement: text with its one direction word swapped. Returns (text, error)."""
    if statement.get("flip"):
        flipped, _, _, err = flip(statement.get("text") or "")
        return flipped, err
    if statement.get("text"):
        return statement["text"], None
    basis, alter = statement.get("basis"), statement.get("alter") or {}
    if not basis or not alter.get("from") or alter.get("to") is None:
        return None, "no text and no basis/alter"
    if basis.count(alter["from"]) != 1:
        return None, "alter.from occurs %d times in basis" % basis.count(alter["from"])
    if alter["from"] == alter["to"]:
        return None, "alter.to equals alter.from"
    if alter.get("kind") not in ("direction", "group", "magnitude", "condition", "significance", None):
        return None, "alter.kind %r" % alter.get("kind")
    return basis.replace(alter["from"], alter["to"]), None


def validate_gen_file(path, corpus, batch_items):
    fatal, warn = [], []
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except ValueError as e:
        return ["invalid JSON: %s" % e], []
    if doc.get("prompt_version") not in ("gen-v1", "gen-v2", "gen-v3", "gen-v4"):
        warn.append("prompt_version %r" % doc.get("prompt_version"))
    v3 = doc.get("prompt_version") == "gen-v3"
    v4 = doc.get("prompt_version") == "gen-v4"
    seen = set()
    for it in doc.get("items", []):
        n = it.get("n")
        if n not in corpus:
            fatal.append("item n=%r not in corpus" % n); continue
        if n in seen:
            fatal.append("item n=%r twice" % n); continue
        seen.add(n)
        if it.get("id") != corpus[n]["id"]:
            fatal.append("n=%d id mismatch %r" % (n, it.get("id")))
        sts = it.get("statements") or []
        if len(sts) != 4:
            fatal.append("n=%d has %d statements" % (n, len(sts))); continue
        if v4:
            if Counter(s.get("label") for s in sts) != Counter({"supported": 3, "not_addressed": 1}):
                fatal.append("n=%d gen-v4 label mix %s (needs 3 supported + 1 not_addressed)" % (n, dict(Counter(s.get("label") for s in sts))))
            if any(s.get("flip") for s in sts):
                fatal.append("n=%d gen-v4 must not mark flip statements" % n)
            sts = effective(sts, "gen-v4")
            if not any(s.get("flip") for s in sts):
                warn.append("n=%d no supported statement with exactly one direction word: no contradicted item for this abstract" % n)
        elif Counter(label_of(s) for s in sts) != MIX:
            fatal.append("n=%d label mix %s" % (n, dict(Counter(label_of(s) for s in sts))))
        if v3:
            flips = [s for s in sts if s.get("flip")]
            if len(flips) != 1:
                fatal.append("n=%d has %d flip statements (needs exactly 1)" % (n, len(flips)))
            if any(s.get("label") == "contradicted" for s in sts):
                fatal.append("n=%d gen-v3 must not write a contradicted statement" % n)
            for s in sts:
                if not s.get("flip") and s.get("label") == "supported" and len(flip_words(s.get("text") or "")) > 1:
                    warn.append("n=%d k=%r plain supported statement carries %d direction words" % (n, s.get("k"), len(flip_words(s.get("text")))))
        text = norm(text_of(corpus[n]))
        old_text = norm(corpus[n].get("text_before_repair") or "")       # D8: statements written against the damaged text
        for s in sts:
            k = s.get("k")
            stext, err = compose(s)
            if err:
                fatal.append("n=%d k=%r %s" % (n, k, err)); continue
            if not isinstance(stext, str) or not stext.strip():
                fatal.append("n=%d k=%r empty text" % (n, k)); continue
            if s.get("label") == "contradicted" and doc.get("prompt_version") == "gen-v2" and s.get("text"):
                fatal.append("n=%d k=%r gen-v2 contradicted item must use basis+alter, not text" % (n, k))
            if len(stext.split()) > MAX_WORDS:
                warn.append("n=%d k=%r %d words" % (n, k, len(stext.split())))
            ev = s.get("evidence") or ""
            if not ev:
                fatal.append("n=%d k=%r no evidence" % (n, k))
            elif norm(ev) not in text:
                if old_text and norm(ev) in old_text:
                    warn.append("n=%d k=%r evidence matches only the pre-repair text (re-checked by pass R)" % (n, k))
                else:
                    fatal.append("n=%d k=%r evidence not verbatim: %r" % (n, k, ev[:60]))
            elif len(ev) > MAX_EVIDENCE:
                warn.append("n=%d k=%r evidence %d chars" % (n, k, len(ev)))
            if not s.get("note"):
                warn.append("n=%d k=%r no note" % (n, k))
            if s.get("label") == "supported":
                # verbatim copying: the statement should not be a substring of the abstract
                if norm(s.get("text") or stext).rstrip(".") in text:
                    warn.append("n=%d k=%r supported statement copied verbatim" % (n, k))
    missing = sorted(set(batch_items) - seen)
    if missing:
        fatal.append("missing items n=%s" % missing)
    return fatal, warn


def validate_check_file(path, corpus, batch):
    fatal, warn = [], []
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except ValueError as e:
        return ["invalid JSON: %s" % e], []
    expect = {it["n"]: {s["j"] for s in it["statements"]} for it in batch["items"]}
    seen = set()
    for it in doc.get("items", []):
        n = it.get("n")
        if n not in expect:
            fatal.append("n=%r not in batch" % n); continue
        seen.add(n)
        js = set()
        for v in it.get("verdicts") or []:
            j = v.get("j")
            js.add(j)
            if v.get("label") not in LABELS:
                fatal.append("n=%d j=%r bad label %r" % (n, j, v.get("label")))
            if v.get("confidence") not in (1, 2, 3):
                warn.append("n=%d j=%r confidence %r" % (n, j, v.get("confidence")))
            if v.get("flag") not in (None, "", "ambiguous", "ill_formed"):
                fatal.append("n=%d j=%r bad flag %r" % (n, j, v.get("flag")))
            ev = v.get("evidence") or ""
            if ev and norm(ev) not in norm(text_of(corpus[n])) and norm(ev) not in norm(corpus[n].get("text_before_repair") or ""):
                warn.append("n=%d j=%r evidence not verbatim" % (n, j))
        if js != expect[n]:
            fatal.append("n=%d verdict set %s != %s" % (n, sorted(js), sorted(expect[n])))
    missing = sorted(set(expect) - seen)
    if missing:
        fatal.append("missing items n=%s" % missing)
    return fatal, warn


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["gen", "check"])
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    corpus = load_corpus()
    bad = 0
    if a.what == "gen":
        for name in sorted(os.listdir(BATCH_DIR)):
            if not name.startswith("gen_"):
                continue
            with open(os.path.join(BATCH_DIR, name), encoding="utf-8") as f:
                batch_items = [it["n"] for it in json.load(f)["items"]]
            out = os.path.join(GEN_DIR, name)
            if not os.path.exists(out):
                print("%s: MISSING" % name); bad += 1; continue
            fatal, warn = validate_gen_file(out, corpus, batch_items)
            print("%s: %s · %d warnings" % (name, "OK" if not fatal else "%d FATAL" % len(fatal), len(warn)))
            for m in fatal:
                print("   FATAL", m)
            if not a.quiet:
                for m in warn[:12]:
                    print("   warn", m)
            bad += bool(fatal)
    else:
        for name in sorted(os.listdir(BATCH_DIR)):
            if not name.startswith("check_") or name.endswith(".map.json"):
                continue
            with open(os.path.join(BATCH_DIR, name), encoding="utf-8") as f:
                batch = json.load(f)
            out = os.path.join(CHECK_DIR, name)
            if not os.path.exists(out):
                print("%s: MISSING" % name); bad += 1; continue
            fatal, warn = validate_check_file(out, corpus, batch)
            print("%s: %s · %d warnings" % (name, "OK" if not fatal else "%d FATAL" % len(fatal), len(warn)))
            for m in fatal:
                print("   FATAL", m)
            if not a.quiet:
                for m in warn[:8]:
                    print("   warn", m)
            bad += bool(fatal)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
