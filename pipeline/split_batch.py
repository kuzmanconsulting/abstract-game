#!/usr/bin/env python3
"""Split one generation batch file into k smaller ones (gen_12 -> gen_12a, gen_12b, gen_12c); the original is renamed
to _<name>_unsplit.json.bak so the validator and the check batches see only the parts.

    python3 pipeline/split_batch.py gen_12 3
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BATCH_DIR = os.path.join(os.path.dirname(HERE), "src", "batches")


def split(name, k):
    path = os.path.join(BATCH_DIR, name + ".json")
    with open(path, encoding="utf-8") as f:
        batch = json.load(f)
    items = batch["items"]
    size = -(-len(items) // k)
    parts = []
    for i in range(k):
        part = items[i * size:(i + 1) * size]
        if not part:
            break
        pname = "%s%s" % (name, "abcdefgh"[i])
        with open(os.path.join(BATCH_DIR, pname + ".json"), "w", encoding="utf-8") as f:
            json.dump({"batch": pname, "items": part}, f, ensure_ascii=False, indent=0)
        parts.append((pname, len(part), part[0]["n"], part[-1]["n"]))
    os.rename(path, os.path.join(BATCH_DIR, "_%s_unsplit.json.bak" % name))
    return parts


if __name__ == "__main__":
    for p in split(sys.argv[1], int(sys.argv[2])):
        print("%s: %d items, n=%d..%d" % p)
