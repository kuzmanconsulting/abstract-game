#!/usr/bin/env python3
"""Headless checks of docs/index.html against docs/data.json (Playwright + python http.server):
journal filter, statement shuffle, score/streak/best arithmetic and persistence, reading list.

    python3 -m unittest tests.test_page -v      (skipped when Playwright or a browser is missing)
"""
import json
import os
import subprocess
import sys
import time
import unittest
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
PORT = 8765

try:
    from playwright.sync_api import sync_playwright
    HAVE_PW = True
except Exception:                                   # pragma: no cover
    HAVE_PW = False


@unittest.skipUnless(HAVE_PW and os.path.exists(os.path.join(DOCS, "data.json")), "playwright or docs/data.json missing")
class PageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=DOCS,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/data.json" % PORT, timeout=1).read(10)
                break
            except Exception:
                time.sleep(0.1)
        with open(os.path.join(DOCS, "data.json"), encoding="utf-8") as f:
            cls.data = json.load(f)
        cls.by_text = {}
        for it in cls.data["items"]:
            for s in it["statements"]:
                cls.by_text[s["text"]] = (it, s)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.terminate(); cls.server.wait(timeout=10)

    def page(self):
        ctx = self.browser.new_context(viewport={"width": 1000, "height": 900})
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto("http://127.0.0.1:%d/" % PORT)
        pg.wait_for_selector("ol.sts li.st")
        return ctx, pg, errors

    def shown(self, pg):
        """The abstract on screen, found through its statement texts, and the statements in display order."""
        texts = [t.strip() for t in pg.eval_on_selector_all("ol.sts li.st .txt", "els => els.map(e => e.textContent.replace(/^\\d+/, ''))")]
        items = {self.by_text[t][0]["n"] for t in texts if t in self.by_text}
        self.assertEqual(len(items), 1, "statements on screen belong to one abstract: %s" % texts[:1])
        it = next(x for x in self.data["items"] if x["n"] in items)
        return it, texts

    def answer(self, pg, it, texts, wrong=0):
        """Click the labels; the first `wrong` statements get a wrong label."""
        for idx, t in enumerate(texts):
            s = self.by_text[t][1]
            label = s["label"]
            if idx < wrong:
                label = {"supported": "contradicted", "contradicted": "supported", "not_addressed": "supported"}[label]
            pg.click("#st-%d .seg button[data-k='%s']" % (s["k"], label))
        pg.click("#submit")
        pg.wait_for_selector("#next")

    def score(self, pg):
        parts = pg.eval_on_selector_all("#score span", "els => els.map(e => e.textContent)")
        return dict(p.split(" ", 1) for p in parts)

    def test_journal_filter_holds_over_many_picks(self):
        ctx, pg, errors = self.page()
        journal = pg.eval_on_selector("#journal", "s => Array.from(s.options).filter(o => o.value !== 'all')[0].value")
        pg.select_option("#journal", journal)
        pg.wait_for_selector("ol.sts li.st")
        for _ in range(12):
            it, _ = self.shown(pg)
            self.assertEqual(it.get("journal") or it.get("server"), journal)
            pg.click("#skip")
            pg.wait_for_selector("ol.sts li.st")
        self.assertEqual(errors, [])
        ctx.close()

    def test_leading_journals_filter_holds_over_many_picks(self):
        """D23: the "Leading journals" chip restricts the pool to journal articles tagged tier=leading in data.json."""
        ctx, pg, errors = self.page()
        pg.click("#filters button:has-text('Leading journals')")
        pg.wait_for_selector("ol.sts li.st")
        for _ in range(12):
            it, _ = self.shown(pg)
            self.assertEqual((it["source"], it.get("tier")), ("journal", "leading"), it.get("journal"))
            pg.click("#skip")
            pg.wait_for_selector("ol.sts li.st")
        pg.eval_on_selector("#about", "d => d.open = true")                # the <details> is closed by default
        self.assertIn("Leading journals", pg.inner_text("#about"))      # the About text names the list
        self.assertEqual(errors, [])
        ctx.close()

    def test_title_is_shown_before_answering_by_default(self):
        ctx, pg, errors = self.page()
        it, _ = self.shown(pg)
        self.assertEqual(pg.inner_text(".pretitle").strip(), it["title"])
        self.assertEqual(pg.locator("#shareHint").count(), 0)             # the Instagram note was removed (Maja 21:24)
        ctx.close()

    def test_statements_are_shuffled_on_display(self):
        ctx, pg, errors = self.page()
        orders = set()
        for _ in range(25):
            it, texts = self.shown(pg)
            ks = tuple(self.by_text[t][1]["k"] for t in texts)
            orders.add(ks == tuple(s["k"] for s in it["statements"]))
            pg.click("#skip")
            pg.wait_for_selector("ol.sts li.st")
        self.assertIn(False, orders, "in 25 abstracts the statements were never shown in a different order than stored")
        ctx.close()

    def test_score_streak_best_and_persistence(self):
        ctx, pg, errors = self.page()
        it, texts = self.shown(pg)
        self.answer(pg, it, texts)                                         # all right
        n1 = len(texts)
        sc = self.score(pg)
        self.assertEqual(sc["statements"], str(n1)); self.assertEqual(sc["correct"], "100%"); self.assertEqual(sc["streak"], "1")
        pg.click("#next"); pg.wait_for_selector("ol.sts li.st")
        it, texts = self.shown(pg)
        self.answer(pg, it, texts)                                         # all right again
        n2 = n1 + len(texts)
        sc = self.score(pg)
        self.assertEqual(sc["statements"], str(n2)); self.assertEqual(sc["streak"], "2")
        pg.click("#next"); pg.wait_for_selector("ol.sts li.st")
        it, texts = self.shown(pg)
        self.answer(pg, it, texts, wrong=1)                                # one wrong: streak resets, best stays 2
        n3 = n2 + len(texts)
        sc = self.score(pg)
        self.assertEqual(sc["statements"], str(n3)); self.assertEqual(sc["streak"], "0 · best 2")
        self.assertEqual(sc["correct"], "%d%%" % round(100 * (n3 - 1) / n3))
        pg.reload(); pg.wait_for_selector("ol.sts li.st")                 # persisted in localStorage
        sc = self.score(pg)
        self.assertEqual(sc["statements"], str(n3)); self.assertEqual(sc["streak"], "0 · best 2")
        self.assertEqual(errors, [])
        ctx.close()

    def test_reading_list_save_and_export(self):
        ctx, pg, errors = self.page()
        it, texts = self.shown(pg)
        self.answer(pg, it, texts)
        pg.click("#saveBtn")
        pg.wait_for_selector("#savedList li", state="attached")
        saved = pg.evaluate("() => JSON.parse(localStorage.getItem('ar.saved'))")
        self.assertEqual(len(saved), 1); self.assertEqual(saved[0]["n"], it["n"]); self.assertEqual(saved[0]["title"], it["title"])
        pg.eval_on_selector("#savedPanel", "d => d.open = true")           # the <details> panel is closed by default
        pg.click("#expShow")                                               # the visible text box carries the BibTeX export
        box = pg.input_value("#expBox")
        self.assertIn("@article{", box); self.assertIn(it["title"].split()[0], box)
        pg.reload(); pg.wait_for_selector("#savedList li", state="attached")
        self.assertEqual(errors, [])
        ctx.close()


if __name__ == "__main__":
    unittest.main()
