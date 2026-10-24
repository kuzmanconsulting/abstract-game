import json, sys
batch_p, gen_p = sys.argv[1], sys.argv[2]
batch = json.load(open(batch_p))
gen = json.load(open(gen_p))
texts = {it["n"]: " ".join(s["text"] for s in it["sections"]) for it in batch["items"]}
ids = {it["n"]: it["id"] for it in batch["items"]}
errs = []
total_stmt = 0
flagged_no_contradicted = []  # rubric has no 'contradicted' label; track items lacking not_addressed
batch_ns = [it["n"] for it in batch["items"]]
gen_ns = [it["n"] for it in gen["items"]]
if batch_ns != gen_ns:
    errs.append(f"item n mismatch: batch {batch_ns} vs gen {gen_ns}")
for it in gen["items"]:
    n = it["n"]
    if it["id"] != ids.get(n):
        errs.append(f"n={n} id mismatch {it['id']} vs {ids.get(n)}")
    st = it["statements"]
    total_stmt += len(st)
    if len(st) != 4:
        errs.append(f"n={n} has {len(st)} statements")
    labels = [s["label"] for s in st]
    if labels.count("supported") != 3 or labels.count("not_addressed") != 1:
        errs.append(f"n={n} label counts: {labels}")
    if "not_addressed" not in labels:
        flagged_no_contradicted.append(n)
    txt = texts[n]
    for s in st:
        if s["evidence"] not in txt:
            errs.append(f"n={n} k={s['k']} evidence NOT substring: {s['evidence'][:60]!r}")
        wc = len(s["text"].split())
        if wc > 30:
            errs.append(f"n={n} k={s['k']} text {wc} words >30")
        for hedge in (" might ", " could ", " may "):
            if hedge in (" "+s["text"].lower()+" "):
                errs.append(f"n={n} k={s['k']} hedge {hedge!r}: {s['text']}")
print("items:", len(gen["items"]))
print("total statements:", total_stmt)
print("errors:", len(errs))
for e in errs: print("  ERR", e)
print("items lacking not_addressed:", flagged_no_contradicted)
