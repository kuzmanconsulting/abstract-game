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
# the second corpus (flip rule "first-of-any", D11) uses a wider list; the first corpus keeps the list it was checked with
FLIP_PAIRS_V2 = FLIP_PAIRS + [
              ("larger", "smaller"), ("stronger", "weaker"), ("highest", "lowest"), ("most", "least"), ("maximum", "minimum"),
              ("promotes", "suppresses"), ("promoted", "suppressed"), ("activates", "represses"), ("activated", "repressed"),
              ("activation", "repression"), ("upregulation", "downregulation"), ("expansion", "contraction"), ("expanded", "contracted"),
              ("accelerated", "delayed"), ("accelerates", "delays"), ("positive", "negative"), ("gain", "loss"), ("gains", "losses"),
              ("older", "younger"), ("enhanced", "diminished"), ("enhances", "diminishes"), ("abundant", "scarce"), ("rarely", "frequently"),
              ("increasing", "decreasing"), ("ascending", "descending"), ("dominant", "recessive"), ("conserved", "divergent")]
def _table(pairs):
    d = {}
    for a, b in pairs:
        d[a] = b
        d[b] = a
    return d, re.compile(r"\b(" + "|".join(sorted(d, key=len, reverse=True)) + r")\b", re.I)


FLIP_SETS = {"exactly-one": _table(FLIP_PAIRS), "first-of-any": _table(FLIP_PAIRS_V2), "first-of-any-v2": _table(FLIP_PAIRS_V2),
             "first-of-any-v3": _table(FLIP_PAIRS_V2)}
V2_RULES = ("first-of-any-v2", "first-of-any-v3")   # v3 (third corpus): v2 plus "more often" -> "less often" (D13)
FLIP, FLIP_RE = FLIP_SETS["exactly-one"]
TRUE_ONLY_VERSIONS = ("gen-v4", "gen-v5")   # prompts that write only true statements; the pipeline makes the flip

# "first-of-any-v2" (D13): same vocabulary as "first-of-any", but a direction word is skipped when it is part of a
# fixed phrase or method name, when it is negated (a flipped negation is a double negative, not a contradiction),
# or when the statement already contains the word's opposite (swapping one of the two leaves "losses exceeded
# losses"). The swap itself also knows "most X" (quantifier -> "few X") from "the most X" (superlative -> "the
# least X"), "more <mass noun>" -> "less", and fixes "a"/"an" in front of the new word.
# "AMP-activated protein kinase" added 2026-10-23 21:50 (a gen_60 generator caught the flip "AMP-repressed"; no statement in any
# generated file contained the phrase at that time, so the v2/v3 compositions are unchanged — D23)
IDIOMS_V2 = re.compile(r"\b(no longer|above all|more or less|at the latest|amp-activated|maximum (?:likelihood|parsimony|entropy)|minimum (?:spanning|evolution)|"
                       r"(?:positive|negative)[- ](?:sense|strand|control|controls|feedback)|dominant[- ]negative|"
                       r"(?:false|true)[- ](?:positive|negative)s?|gram[- ](?:positive|negative)|triple[- ]negative|"
                       r"(?:er|pr|her2|hpv|ebv|hiv|mmr|pd-l1|receptor|node|margin|lymph node|ctdna|mrd)[- ](?:positive|negative))\b", re.I)
NEGATION_V2 = re.compile(r"(?:\b(?:no|not|non|never|without|neither|nor)\b[- ]?|\bnon-)\s*$", re.I)
ADJ_SUFFIX_V2 = ("ous", "ive", "ful", "able", "ible", "ant", "ent", "ly")


def flip_words(text, rule="exactly-one"):
    """The direction-word matches a rule may swap, in text order (for v2 only the eligible ones)."""
    hits = [m for m in FLIP_SETS[rule][1].finditer(text or "")]
    if rule not in V2_RULES:
        return hits
    table = FLIP_SETS[rule][0]
    idioms = [(m.start(), m.end()) for m in IDIOMS_V2.finditer(text or "")]
    low = (text or "").lower()
    words = set(re.findall(r"[a-z]+", low))
    out = []
    for m in hits:
        if any(a <= m.start() and m.end() <= b for a, b in idioms):
            continue
        if NEGATION_V2.search(text[:m.start()]):
            continue
        if table[m.group(1).lower()] in words:            # both members of the pair are in the statement
            continue
        out.append(m)
    return out


# "more" before an adjective or adverb flips to "less" ("more accurate" -> "less accurate"), before a noun to "fewer"
ADJ_AFTER_MORE = {"accurate", "sensitive", "specific", "likely", "frequent", "common", "abundant", "stable", "severe", "efficient",
                  "effective", "precise", "robust", "pronounced", "prevalent", "rapid", "often", "variable", "diverse", "complex",
                  "aggressive", "active", "conserved", "similar", "distinct", "heterogeneous", "homogeneous", "informative", "reliable",
                  "consistent", "strongly", "closely", "highly", "than"}


def flip(text, rule="exactly-one"):
    """Swap one direction word in text for its opposite, keeping capitalisation. Returns (flipped, from, to, error).
    "exactly-one": the statement must carry exactly one direction word; "first-of-any": the first of any number."""
    hits = flip_words(text, rule)
    if rule == "exactly-one" and len(hits) != 1:
        return None, None, None, "flip statement has %d direction words (needs exactly 1)" % len(hits)
    if not hits:
        return None, None, None, "flip statement has no direction word"
    m = hits[0]
    w = m.group(1)
    rep = FLIP_SETS[rule][0][w.lower()]
    nxt = re.match(r"\s+([A-Za-z-]+)", text[m.end():])
    nw = nxt.group(1).lower() if nxt else ""
    prv = re.search(r"([A-Za-z']+)\s*$", text[:m.start()])
    pw = prv.group(1).lower() if prv else ""
    adjective_next = nw in ADJ_AFTER_MORE or nw.endswith(ADJ_SUFFIX_V2 if rule in V2_RULES else "ly")
    if w.lower() == "more":
        if rule in V2_RULES:
            rep = "less"                                   # default; "fewer" only in front of a plural count noun
            for word in re.findall(r"[A-Za-z-]+", text[m.end():])[:3]:   # "more repetitive elements" -> fewer
                lw = word.lower()
                if lw in ("than", "of", "in", "to", "with", "for", "at", "by", "from", "among", "between", "across", "on") or lw.endswith("ly"):
                    break
                if rule == "first-of-any-v3" and lw in ADJ_AFTER_MORE:   # "more often sites" -> less often (v2 gave "fewer often")
                    break
                if lw.endswith("s") and not lw.endswith(("ous", "ss", "us", "is")):
                    rep = "fewer"
                    break
        elif adjective_next:
            rep = "less"                                   # "more accurate", "more often" -> less
    elif w.lower() == "most" and rule in V2_RULES:
        superlative = (pw in ("the", "at", "its", "their", "our", "'s") or pw.endswith("ed") or adjective_next
                       or nw in ("between", "among", "across", "from", "during", "when", "where", "in", "at", "on", "to", "for", "with", "by"))
        if not superlative:
            rep = "few"                                    # "most genes" -> "few genes"; "the most variable" -> "the least variable"
    if w[0].isupper():
        rep = rep[0].upper() + rep[1:]
    head = text[:m.start()]
    if rule in V2_RULES:                                   # "an increased" -> "a decreased", "a lower" -> "an upper"
        art = re.search(r"\b([Aa]n?)\s+$", head)
        if art:
            vowel = rep[0].lower() in "aeiou"
            want = ("an" if vowel else "a")
            if art.group(1).lower() != want:
                fixed = want if art.group(1).islower() else want.capitalize()
                head = head[:art.start(1)] + fixed + head[art.end(1):]
    return head + rep + text[m.end():], w, rep, None


def effective(statements, prompt_version, flip_rule="exactly-one"):
    """The statements as the game plays them. gen-v4 writes only true statements; the pipeline turns one supported
    statement (by k) into the contradicted item by marking it flip (deterministic, recorded nowhere else — recomputed
    from the generated file every time). Rules: "exactly-one" (first corpus): the first supported statement carrying
    exactly one direction word; "first-of-any" (second corpus, D11): the first supported statement carrying any
    direction word, and flip() swaps only its first occurrence; "first-of-any-v2" (D13): the same over the eligible
    direction words only (see flip_words). Other versions pass through."""
    out = [dict(s) for s in statements]
    if prompt_version in TRUE_ONLY_VERSIONS:
        for s in sorted(out, key=lambda x: x.get("k", 0)):
            n_words = len(flip_words(s.get("text") or "", flip_rule))
            if s.get("label") == "supported" and (n_words == 1 if flip_rule == "exactly-one" else n_words >= 1):
                s["flip"] = True
                s["flip_rule"] = flip_rule
                break
    return out


def label_of(statement):
    """The label a statement carries in the game: a gen-v3 flip statement is the contradicted item."""
    return "contradicted" if statement.get("flip") else statement.get("label")


def compose(statement):
    """The statement text the player sees. gen-v1: text as written. gen-v2: basis with alter.from -> alter.to applied
    once. gen-v3 flip statement: text with its one direction word swapped. Returns (text, error)."""
    if statement.get("flip"):
        flipped, _, _, err = flip(statement.get("text") or "", statement.get("flip_rule", "exactly-one"))
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
    if doc.get("prompt_version") not in ("gen-v1", "gen-v2", "gen-v3") + TRUE_ONLY_VERSIONS:
        warn.append("prompt_version %r" % doc.get("prompt_version"))
    v3 = doc.get("prompt_version") == "gen-v3"
    v4 = doc.get("prompt_version") in TRUE_ONLY_VERSIONS
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
            sts = effective(sts, doc.get("prompt_version"), doc.get("flip_rule", "exactly-one"))
            if not any(s.get("flip") for s in sts):
                warn.append("n=%d no supported statement with a direction word (rule %s): no contradicted item for this abstract" % (n, doc.get("flip_rule", "exactly-one")))
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
    ap.add_argument("--only", nargs="*", default=None, help="validate only these batch names (gen_54, check_A_54 …); a generator or checker checks its own file")
    a = ap.parse_args(argv)
    corpus = load_corpus()
    bad = 0
    only = set(a.only or [])
    if a.what == "gen":
        for name in sorted(os.listdir(BATCH_DIR)):
            if not name.startswith("gen_") or (only and name[:-5] not in only):
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
            if not name.startswith("check_") or name.endswith(".map.json") or (only and name[:-5] not in only):
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
