#!/usr/bin/env python3
"""Tests for the item pipeline: fetch normalisation and filters, corpus selection, the gen-v2 composition rule, the
validators, the blind check batches (j -> k mapping), the merge rule and the public site data. Standard library.

    python3 -m unittest discover -s tests -v
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PIPE = os.path.join(ROOT, "pipeline")
sys.path.insert(0, PIPE)


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(PIPE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fetch = load("fetch_candidates")
select = load("select_corpus")
validate = load("validate")
make_batches = load("make_batches")
merge = load("merge_checks")
build_site = load("build_site")


def epmc_record(pmid="1", doi="10.1/x", abstract=None, source="MED", publisher=None, year="2025", title="A title.", pubtypes=("Journal Article",)):
    rec = {"id": pmid if source == "MED" else "PPR%s" % pmid, "source": source, "pmid": pmid if source == "MED" else None, "doi": doi, "title": title,
           "authorString": "Doe J, Roe R.", "authorList": {"author": [{"fullName": "Doe J"}, {"fullName": "Roe R"}]},
           "pubYear": year, "firstPublicationDate": "%s-03-04" % year, "pubTypeList": {"pubType": list(pubtypes)},
           "abstractText": abstract if abstract is not None else ("<h4>Background</h4> Some background. <h4>Results</h4> " + "We measured 12 samples and found 3 variants in 40% of cases. " * 18 + "<h4>Conclusions</h4> It works.")}
    if source == "MED":
        rec["journalInfo"] = {"journal": {"title": "Journal of Tests"}}
    else:
        rec["bookOrReportDetails"] = {"publisher": publisher or "bioRxiv"}
    return rec


class FetchNormalise(unittest.TestCase):
    def test_structured_abstract_is_split_on_h4_and_unescaped(self):
        secs = fetch.parse_abstract("<h4>Background</h4> A &amp; B. <h4>Results:</h4> Found <i>x</i> = 3. <h4>Conclusion</h4> Done.")
        self.assertEqual([s["label"] for s in secs], ["Background", "Results", "Conclusion"])
        self.assertEqual(secs[0]["text"], "A & B.")
        self.assertEqual(secs[1]["text"], "Found x = 3.")
        self.assertTrue(fetch.has_results(secs))

    def test_unstructured_abstract_needs_three_numbered_sentences(self):
        one = fetch.parse_abstract("Plain text without any numbers. Still none here.")
        self.assertEqual(one[0]["label"], None)
        self.assertFalse(fetch.has_results(one))
        many = fetch.parse_abstract("We saw 12 cases. Of these, 3 had X. The rate was 40%. Fine.")
        self.assertTrue(fetch.has_results(many))

    def test_normalise_and_keep_rules(self):
        c = fetch.normalise(epmc_record(), "cfdna", "journal")
        self.assertEqual((c["id"], c["pmid"], c["journal"], c["year"], c["source"], c["server"]), ("pmid:1", "1", "Journal of Tests", 2025, "journal", None))
        self.assertEqual(c["url"], "https://pubmed.ncbi.nlm.nih.gov/1/")
        self.assertTrue(c["structured"] and c["has_results"])
        self.assertIsNone(fetch.keep(c, set(), set()))
        self.assertEqual(fetch.keep(c, {"1"}, set()), "trial_bank")
        self.assertEqual(fetch.keep(c, set(), {"10.1/x"}), "trial_bank")
        p = fetch.normalise(epmc_record(pmid="2", doi="10.1/p", source="PPR", publisher="Research Square"), "te", "preprint")
        self.assertEqual(fetch.keep(p, set(), set()), "server")
        p2 = fetch.normalise(epmc_record(pmid="3", doi="10.1/q", source="PPR", publisher="medRxiv"), "te", "preprint")
        self.assertEqual((p2["id"], p2["journal"], p2["server"], p2["url"]), ("doi:10.1/q", "medRxiv", "medRxiv", "https://doi.org/10.1/q"))
        self.assertIsNone(fetch.keep(p2, set(), set()))
        short = fetch.normalise(epmc_record(pmid="4", doi="10.1/s", abstract="<h4>Results</h4> Short 1 2 3."), "te", "journal")
        self.assertEqual(fetch.keep(short, set(), set()), "length")
        rev = fetch.normalise(epmc_record(pmid="5", doi="10.1/r", pubtypes=("Journal Article", "Review")), "te", "journal")
        self.assertEqual(fetch.keep(rev, set(), set()), "pub_type")
        rev2 = fetch.normalise(epmc_record(pmid="6", doi="10.1/t", title="A systematic review of X"), "te", "journal")
        self.assertEqual(fetch.keep(rev2, set(), set()), "title_type")

    def test_query_mentions_every_filter(self):
        q = fetch.build_query("cfdna", "journal", "2023-01-01", "2026-10-23")
        for part in ("SRC:MED", "FIRST_PDATE:[2023-01-01 TO 2026-10-23]", "HAS_ABSTRACT:y", 'NOT PUB_TYPE:"Review"', 'ABSTRACT:"cell-free DNA"'):
            self.assertIn(part, q)
        q2 = fetch.build_query("cancergen", "preprint", "2023-01-01", "2026-10-23")
        self.assertIn("SRC:PPR", q2); self.assertNotIn("PUB_TYPE", q2); self.assertIn("ABSTRACT:cancer", q2)


def cand(n, field, source, year, title=None):
    return {"id": "pmid:%d" % n, "field": field, "source": source, "year": year, "title": title or "Title %d" % n, "sections": [{"label": None, "text": "t"}]}


class Selection(unittest.TestCase):
    def test_balanced_fields_preprint_share_and_title_dedupe(self):
        pool = []
        k = 0
        for field in ("cfdna", "te", "cancergen"):
            for source in ("journal", "preprint"):
                for year in (2023, 2024, 2025, 2026):
                    for _ in range(30):
                        k += 1; pool.append(cand(k, field, source, year))
        pool.append(cand(9999, "te", "preprint", 2025, title="Title 5"))        # same title as a journal item -> dropped
        chosen, dups = select.select(pool, 120, 0.3, seed=1)
        self.assertEqual(len(chosen), 120)
        self.assertEqual(dups, 1)
        from collections import Counter
        self.assertEqual(Counter(c["field"] for c in chosen), {"cfdna": 40, "te": 40, "cancergen": 40})
        self.assertEqual(Counter(c["source"] for c in chosen), {"journal": 84, "preprint": 36})
        years = Counter(c["year"] for c in chosen)
        self.assertTrue(max(years.values()) - min(years.values()) <= 6, years)
        self.assertEqual([c["n"] for c in chosen], list(range(120)))
        again, _ = select.select(pool, 120, 0.3, seed=1)
        self.assertEqual([c["id"] for c in again], [c["id"] for c in chosen], "seeded: reproducible")


class Compose(unittest.TestCase):
    def test_v1_text_passes_through(self):
        self.assertEqual(validate.compose({"text": "Rates were higher in A."}), ("Rates were higher in A.", None))

    def test_flip_more_depends_on_what_follows(self):
        self.assertEqual(validate.flip("The assay was more accurate than imaging.")[0], "The assay was less accurate than imaging.")
        self.assertEqual(validate.flip("Tumours carried more insertions than normal tissue.")[0], "Tumours carried fewer insertions than normal tissue.")
        self.assertEqual(validate.flip("Fewer patients relapsed after therapy.")[0], "More patients relapsed after therapy.")
        self.assertEqual(validate.flip("Expression was more strongly correlated in responders.")[0], "Expression was less strongly correlated in responders.")

    def test_v2_basis_alter_composes_once(self):
        s = {"basis": "ctDNA was detected in 80% of responders.", "alter": {"from": "80%", "to": "20%", "kind": "magnitude"}}
        self.assertEqual(validate.compose(s), ("ctDNA was detected in 20% of responders.", None))
        bad = {"basis": "A and A.", "alter": {"from": "A", "to": "B", "kind": "group"}}
        self.assertEqual(validate.compose(bad)[0], None)
        self.assertIn("occurs 2 times", validate.compose(bad)[1])
        self.assertIn("equals", validate.compose({"basis": "x y", "alter": {"from": "x", "to": "x"}})[1])
        self.assertIn("kind", validate.compose({"basis": "x y", "alter": {"from": "x", "to": "z", "kind": "mood"}})[1])
        self.assertIn("no text", validate.compose({"label": "supported"})[1])


class Validators(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="abstract-game-")
        self.corpus = {0: {"n": 0, "id": "pmid:1", "sections": [{"label": "Results", "text": "ctDNA was found in 80% of responders. Levels fell after therapy."}]}}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _gen(self, statements, version="gen-v2"):
        path = os.path.join(self.tmp, "gen_00.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"batch": "gen_00", "prompt_version": version, "items": [{"n": 0, "id": "pmid:1", "statements": statements}]}, f)
        return path

    def good(self):
        return [{"k": 1, "label": "supported", "text": "Most responders had detectable ctDNA.", "evidence": "ctDNA was found in 80% of responders.", "note": "n"},
                {"k": 2, "label": "supported", "text": "Therapy lowered ctDNA levels.", "evidence": "Levels fell after therapy.", "note": "n"},
                {"k": 3, "label": "contradicted", "basis": "ctDNA levels fell after therapy.", "alter": {"from": "fell", "to": "rose", "kind": "direction"}, "evidence": "Levels fell after therapy.", "note": "n"},
                {"k": 4, "label": "not_addressed", "text": "ctDNA predicted overall survival.", "evidence": "Levels fell after therapy.", "note": "not studied"}]

    def test_good_file_passes(self):
        fatal, warn = validate.validate_gen_file(self._gen(self.good()), self.corpus, [0])
        self.assertEqual(fatal, [])
        self.assertEqual(warn, [])

    def test_bad_mix_evidence_and_v2_text_are_fatal(self):
        sts = self.good()
        sts[1]["label"] = "contradicted"                       # mix 1/2/1
        sts[0]["evidence"] = "not in the abstract"
        sts[2]["text"] = "ctDNA levels rose after therapy."    # gen-v2 contradicted item must not carry text
        fatal, warn = validate.validate_gen_file(self._gen(sts), self.corpus, [0])
        self.assertTrue(any("label mix" in m for m in fatal))
        self.assertTrue(any("evidence not verbatim" in m for m in fatal))
        self.assertTrue(any("basis+alter" in m for m in fatal))
        fatal, _ = validate.validate_gen_file(self._gen(self.good()), self.corpus, [0, 1])
        self.assertTrue(any("missing items" in m for m in fatal))
        fatal, _ = validate.validate_gen_file(self._gen(self.good()[:3]), self.corpus, [0])
        self.assertTrue(any("has 3 statements" in m for m in fatal))

    def test_verbatim_copy_is_a_warning(self):
        sts = self.good()
        sts[0]["text"] = "ctDNA was found in 80% of responders."
        fatal, warn = validate.validate_gen_file(self._gen(sts), self.corpus, [0])
        self.assertEqual(fatal, [])
        self.assertTrue(any("copied verbatim" in m for m in warn))


class EndToEnd(unittest.TestCase):
    """corpus -> generated -> blind check batches -> three check files -> merge -> site data, on two abstracts."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="abstract-game-e2e-")
        for d in ("src/batches", "src/generated", "src/checks", "docs"):
            os.makedirs(os.path.join(self.tmp, d))
        items = [{"n": 0, "id": "pmid:1", "field": "cfdna", "source": "journal", "server": None, "pmid": "1", "doi": "10.1/a", "title": "Paper A", "authors": ["Doe J"], "journal": "J A", "year": 2025, "date": "2025-02-01", "url": "u", "doi_url": "d",
                  "sections": [{"label": "Results", "text": "ctDNA was found in 80% of responders. Levels fell after therapy."}]},
                 {"n": 1, "id": "doi:10.1/b", "field": "te", "source": "preprint", "server": "bioRxiv", "pmid": None, "doi": "10.1/b", "title": "Paper B", "authors": ["Roe R"], "journal": "bioRxiv", "year": 2026, "date": "2026-01-09", "url": "u2", "doi_url": "d2",
                  "sections": [{"label": None, "text": "LINE-1 copies were 3-fold higher in tumours than in normal tissue. Expression correlated with hypomethylation."}]}]
        with open(os.path.join(self.tmp, "src", "corpus.json"), "w", encoding="utf-8") as f:
            json.dump({"header": {}, "items": items}, f)
        gen = {"batch": "gen_00", "prompt_version": "gen-v2", "items": [
            {"n": 0, "id": "pmid:1", "statements": [
                {"k": 1, "label": "supported", "text": "Most responders had detectable ctDNA.", "evidence": "ctDNA was found in 80% of responders.", "note": "a"},
                {"k": 2, "label": "contradicted", "basis": "ctDNA levels fell after therapy.", "alter": {"from": "fell", "to": "rose", "kind": "direction"}, "evidence": "Levels fell after therapy.", "note": "b"},
                {"k": 3, "label": "supported", "text": "Therapy lowered ctDNA levels.", "evidence": "Levels fell after therapy.", "note": "c"},
                {"k": 4, "label": "not_addressed", "text": "ctDNA predicted survival.", "evidence": "Levels fell after therapy.", "note": "d"}]},
            {"n": 1, "id": "doi:10.1/b", "statements": [
                {"k": 1, "label": "supported", "text": "Tumours carried about three times more LINE-1 copies than normal tissue.", "evidence": "LINE-1 copies were 3-fold higher in tumours than in normal tissue.", "note": "a"},
                {"k": 2, "label": "supported", "text": "LINE-1 expression went with hypomethylation.", "evidence": "Expression correlated with hypomethylation.", "note": "b"},
                {"k": 3, "label": "contradicted", "basis": "LINE-1 copies were higher in tumours.", "alter": {"from": "higher", "to": "lower", "kind": "direction"}, "evidence": "LINE-1 copies were 3-fold higher in tumours than in normal tissue.", "note": "c"},
                {"k": 4, "label": "not_addressed", "text": "LINE-1 insertions caused the tumours.", "evidence": "Expression correlated with hypomethylation.", "note": "d"}]}]}
        with open(os.path.join(self.tmp, "src", "generated", "gen_00.json"), "w", encoding="utf-8") as f:
            json.dump(gen, f)
        for mod in (make_batches, merge, validate, build_site):
            mod.ROOT = self.tmp
        make_batches.CORPUS = merge.CORPUS = validate.CORPUS = os.path.join(self.tmp, "src", "corpus.json")
        make_batches.BATCH_DIR = merge.BATCH_DIR = validate.BATCH_DIR = os.path.join(self.tmp, "src", "batches")
        make_batches.GEN_DIR = merge.GEN_DIR = validate.GEN_DIR = os.path.join(self.tmp, "src", "generated")
        merge.CHECK_DIR = validate.CHECK_DIR = os.path.join(self.tmp, "src", "checks")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_pipeline(self):
        with open(os.path.join(self.tmp, "src", "corpus.json"), encoding="utf-8") as f:
            items = json.load(f)["items"]
        names = make_batches.check_batches(items, ["A", "B", "C"], seed=7, size=35)
        self.assertEqual(names, ["check_A_00", "check_B_00", "check_C_00"])
        with open(os.path.join(self.tmp, "src", "batches", "check_A_00.json"), encoding="utf-8") as f:
            ca = json.load(f)
        st = ca["items"][0]["statements"]
        self.assertEqual(sorted(s["j"] for s in st), [1, 2, 3, 4])
        self.assertTrue(all("label" not in s and "evidence" not in s and "k" not in s for s in st), "checkers are blind: no label, no evidence, no generator id")
        with open(os.path.join(self.tmp, "src", "batches", "check_A_00.map.json"), encoding="utf-8") as f:
            amap = json.load(f)["jk"]
        self.assertEqual(sorted(amap["0"].values()), [1, 2, 3, 4], "the j -> k mapping lives in the side file")
        self.assertIn("ctDNA levels rose after therapy.", [s["text"] for s in st], "the altered sentence is composed for the checker")
        self.assertNotIn("title", ca["items"][0])
        # three checkers: A and B agree with every label; C disagrees on item 0 statement k=4 and flags k=1 of item 1 ill-formed
        for p in ("A", "B", "C"):
            with open(os.path.join(self.tmp, "src", "batches", "check_%s_00.json" % p), encoding="utf-8") as f:
                batch = json.load(f)
            with open(os.path.join(self.tmp, "src", "batches", "check_%s_00.map.json" % p), encoding="utf-8") as f:
                jk = json.load(f)["jk"]
            truth = {it["n"]: {s["k"]: validate.label_of(s) for s in gen_items(gen_path(self.tmp))[it["n"]]} for it in batch["items"]}
            out = {"batch": batch["batch"], "pass": p, "prompt_version": "check-v1", "items": []}
            for it in batch["items"]:
                vs = []
                for s in it["statements"]:
                    k = jk[str(it["n"])][str(s["j"])]
                    lab = truth[it["n"]][k]
                    v = {"j": s["j"], "label": lab, "confidence": 3, "evidence": "Levels fell after therapy." if it["n"] == 0 else "Expression correlated with hypomethylation."}
                    if p == "C" and it["n"] == 0 and k == 4:
                        v["label"] = "supported"
                    if p == "C" and it["n"] == 1 and k == 1:
                        v["flag"] = "ill_formed"; v["reason"] = "test"
                    vs.append(v)
                out["items"].append({"n": it["n"], "id": it["id"], "verdicts": vs})
            with open(os.path.join(self.tmp, "src", "checks", "check_%s_00.json" % p), "w", encoding="utf-8") as f:
                json.dump(out, f)
            corpus = {it["n"]: it for it in items}
            fatal, warn = validate.validate_check_file(os.path.join(self.tmp, "src", "checks", "check_%s_00.json" % p), corpus, batch)
            self.assertEqual(fatal, [], (p, fatal))
        merged, stats = merge.merge(["A", "B", "C"])
        self.assertEqual(stats["abstracts_kept"], 2)
        self.assertEqual(stats["statements_generated"], 8)
        self.assertEqual(stats["statements_kept"], 7, stats)          # one dropped for ill_formed
        self.assertEqual(stats["dropped"], {"ill_formed": 1})
        self.assertEqual(stats["agreement"], {"unanimous": 6, "majority": 1})
        self.assertEqual(stats["k_order_leak"], {"gen_00": 0.5}, "two abstracts, two different label orders over k")
        a0 = next(it for it in merged if it["n"] == 0)
        k4 = next(s for s in a0["statements"] if s["k"] == 4)
        self.assertEqual((k4["agreement"], k4["checks"]["C"]["label"]), ("majority", "supported"))
        k2 = next(s for s in a0["statements"] if s["k"] == 2)
        self.assertEqual(k2["text"], "ctDNA levels rose after therapy.")
        self.assertEqual(k2["alter"], {"kind": "direction", "basis": "ctDNA levels fell after therapy."})
        a1 = next(it for it in merged if it["n"] == 1)
        self.assertEqual(sorted(s["k"] for s in a1["statements"]), [2, 3, 4])
        items_path = os.path.join(self.tmp, "src", "items.json")
        with open(items_path, "w", encoding="utf-8") as f:
            json.dump({"header": {"merged_utc": "x", "passes": ["A", "B", "C"], "rule": {}, "stats": stats}, "items": merged}, f)
        header = build_site.build(items_path, os.path.join(self.tmp, "docs", "data.json"), repo_url="https://example.org/r")
        self.assertEqual((header["n_items"], header["n_statements"], header["years"]), (2, 7, "2025–2026"))
        with open(os.path.join(self.tmp, "docs", "data.json"), encoding="utf-8") as f:
            data = json.load(f)
        s0 = data["items"][0]["statements"]
        self.assertTrue(all("checks" not in s for s in s0), "checker details stay out of the public file")
        self.assertIn("altered", [k for s in s0 for k in s if k == "altered"])
        self.assertEqual(data["header"]["repo_url"], "https://example.org/r")
        # an abstract with fewer than 3 surviving statements is dropped
        merge.MIN_STATEMENTS = 4
        try:
            merged2, stats2 = merge.merge(["A", "B", "C"])
            self.assertEqual(stats2["abstracts_kept"], 1)
            self.assertEqual(stats2["abstracts_dropped_too_few"], 1)
        finally:
            merge.MIN_STATEMENTS = 3


def gen_path(tmp):
    return os.path.join(tmp, "src", "generated", "gen_00.json")


def gen_items(path):
    with open(path, encoding="utf-8") as f:
        return {it["n"]: it["statements"] for it in json.load(f)["items"]}


if __name__ == "__main__":
    unittest.main()
