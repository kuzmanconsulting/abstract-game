#!/usr/bin/env python3
"""Fetch candidate abstracts for the game from Europe PMC (journal articles = SRC:MED, preprints = SRC:PPR
restricted to bioRxiv/medRxiv), 2023–2026, three fields. Standard library only.

Why Europe PMC and not PubMed + the bioRxiv API: one record format for both sources, keyword search over
preprints (the bioRxiv API has none), structured-abstract headings preserved as <h4> tags, authors, DOI and
journal/server in the same record. Reference: https://europepmc.org/RestfulWebService

Output: src/raw/<field>_<source>.json (the records as returned, for provenance) and src/candidates.json
(normalised, filtered, deduplicated), with the queries and counts in its header.

    python3 pipeline/fetch_candidates.py                # default: 2023-01-01..today, 1000 per query
    python3 pipeline/fetch_candidates.py --exclude ~/work/pilltrackerapp/tasks/bank   # drop trial-bank PMIDs/DOIs
"""
import argparse
import glob
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW_DIR = os.path.join(ROOT, "src", "raw")
OUT = os.path.join(ROOT, "src", "candidates.json")
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

# The three fields (Maja, 2026-10-23 14:14: "newer articles and preprints on this topics, omitting the clinical").
FIELDS = {
    "cfdna": {
        "label": "cfDNA / liquid biopsy",
        "terms": ['"cell-free DNA"', "cfDNA", '"liquid biopsy"', '"circulating tumor DNA"', '"circulating tumour DNA"', "ctDNA", "fragmentomic*", '"cell-free RNA"'],
    },
    "te": {
        "label": "transposable elements / genome evolution",
        "terms": ['"transposable element"', '"transposable elements"', "retrotransposon*", '"endogenous retrovirus"', '"endogenous retroviruses"',
                  '"mobile genetic element"', '"mobile genetic elements"', '"LINE-1"', '"Alu element"', '"transposon"', '"transposons"'],
    },
    "cancergen": {
        "label": "cancer genomics",
        "terms": ['"tumor evolution"', '"tumour evolution"', '"clonal evolution"', '"mutational signature"', '"mutational signatures"',
                  '"somatic mutations"', '"cancer genome"', '"cancer genomes"', '"copy number alterations"', '"structural variants"'],
        "require": ["cancer", "tumor", "tumour", "carcinoma", "leukemia", "leukaemia", "lymphoma", "melanoma", "glioma", "sarcoma"],
    },
    # added 2026-10-23 15:20 (Maja: "yes absolutely do evolutionary genomics as well")
    "evogen": {
        "label": "evolutionary genomics",
        "terms": ['"molecular evolution"', "phylogenomic*", '"adaptive evolution"', '"positive selection"', '"comparative genomics"',
                  '"genome evolution"', "speciation", '"gene duplication"', '"horizontal gene transfer"', '"convergent evolution"',
                  '"population genomics"', '"experimental evolution"', '"evolutionary rate"', '"purifying selection"'],
    },
}
# journal-targeted top-up (Maja, 15:20: "add more Nature papers !! and the Cell and Genome Biology and Nature Communications")
TOP_JOURNALS = ["Nature", "Cell", "Genome Biology", "Nature Communications"]
SOURCES = {"journal": "SRC:MED", "preprint": "SRC:PPR"}
PREPRINT_SERVERS = {"bioRxiv", "medRxiv"}
MIN_CHARS, MAX_CHARS = 900, 3200
RESULT_HEADINGS = ("result", "finding", "outcome")


def build_query(field, source, start, end, journals=None):
    f = FIELDS[field]
    terms = " OR ".join("ABSTRACT:%s" % t for t in f["terms"])
    q = "(%s)" % terms
    if f.get("require"):
        q += " AND (%s)" % " OR ".join("ABSTRACT:%s" % w for w in f["require"])
    if journals:
        q += " AND (%s)" % " OR ".join('JOURNAL:"%s"' % j for j in journals)
    q += " AND %s AND FIRST_PDATE:[%s TO %s] AND HAS_ABSTRACT:y" % (SOURCES[source], start, end)
    if source == "journal":
        q += ' NOT PUB_TYPE:"Review" NOT PUB_TYPE:"Editorial" NOT PUB_TYPE:"Comment" NOT PUB_TYPE:"Letter"'
    return q


def fetch_query(query, page_size=1000, max_pages=1, log=print, opener=None, sleep=0.5):
    opener = opener or urllib.request.urlopen
    out, cursor = [], "*"
    for page in range(max_pages):
        params = {"query": query, "resultType": "core", "format": "json", "pageSize": str(page_size), "cursorMark": cursor}
        url = API + "?" + urllib.parse.urlencode(params)
        for attempt in range(3):
            try:
                with opener(url, timeout=120) as resp:
                    doc = json.loads(resp.read().decode("utf-8"))
                break
            except Exception as e:
                log("attempt %d failed: %s" % (attempt + 1, e))
                time.sleep(3 * (attempt + 1))
        else:
            break
        rows = (doc.get("resultList") or {}).get("result") or []
        out.extend(rows)
        log("  page %d: %d records (hitCount %s)" % (page, len(rows), doc.get("hitCount")))
        cursor = doc.get("nextCursorMark")
        if not rows or not cursor or len(rows) < page_size:
            break
        time.sleep(sleep)
    return out


TAG = re.compile(r"<h4>\s*(.*?)\s*</h4>", re.I | re.S)
# only real markup is stripped: a bare "<" in prose ("p < 0.05", "<1%") is text, not a tag. The first version used
# r"<[^>]+>" and deleted everything from such a "<" to the next ">" in 91 corpus abstracts (fixed 2026-10-23 15:20,
# repaired by pipeline/repair_text.py; see DECISIONS D8)
OTHER_TAGS = re.compile(r"</?(?:h[1-6]|i|b|em|strong|sup|sub|p|br|u|span|a|ul|ol|li|div|small|font|tt|code)\b[^<>]*>", re.I)


def parse_abstract(text):
    """Europe PMC abstract -> [{label, text}]; structured abstracts use <h4>Heading</h4>; one unlabelled section otherwise."""
    text = (text or "").replace("\r", " ")
    parts = TAG.split(text)
    sections = []
    if len(parts) == 1:
        body = html.unescape(OTHER_TAGS.sub(" ", parts[0])).strip()
        if body:
            sections.append({"label": None, "text": re.sub(r"\s+", " ", body)})
        return sections
    lead = html.unescape(OTHER_TAGS.sub(" ", parts[0])).strip()
    if lead:
        sections.append({"label": None, "text": re.sub(r"\s+", " ", lead)})
    for i in range(1, len(parts), 2):
        label = html.unescape(OTHER_TAGS.sub("", parts[i])).strip().rstrip(":")
        body = html.unescape(OTHER_TAGS.sub(" ", parts[i + 1] if i + 1 < len(parts) else "")).strip()
        body = re.sub(r"\s+", " ", body)
        if body:
            sections.append({"label": label or None, "text": body})
    return sections


def has_results(sections):
    labels = [s["label"].lower() for s in sections if s.get("label")]
    if labels:
        return any(any(h in lab for h in RESULT_HEADINGS) for lab in labels)
    # unstructured: at least three sentences carrying a number
    text = " ".join(s["text"] for s in sections)
    numbered = [s for s in re.split(r"(?<=[.!?])\s+", text) if re.search(r"\d", s)]
    return len(numbered) >= 3


def normalise(rec, field, source):
    sections = parse_abstract(rec.get("abstractText"))
    text = " ".join(s["text"] for s in sections)
    authors = [a.get("fullName") for a in ((rec.get("authorList") or {}).get("author") or []) if a.get("fullName")]
    journal = ((rec.get("journalInfo") or {}).get("journal") or {}).get("title")
    publisher = (rec.get("bookOrReportDetails") or {}).get("publisher")
    doi = rec.get("doi")
    pmid = rec.get("pmid")
    return {"id": ("pmid:%s" % pmid) if pmid else ("doi:%s" % doi) if doi else ("epmc:%s" % rec.get("id")),
            "epmc_id": rec.get("id"), "source": source, "server": publisher if source == "preprint" else None,
            "pmid": pmid, "doi": doi, "title": html.unescape(OTHER_TAGS.sub("", rec.get("title") or "")).strip().rstrip("."),
            "authors": authors, "author_string": rec.get("authorString"), "journal": journal if source == "journal" else publisher,
            "year": int(rec["pubYear"]) if str(rec.get("pubYear", "")).isdigit() else None,
            "date": rec.get("firstPublicationDate"), "field": field, "sections": sections, "n_chars": len(text),
            "structured": any(s.get("label") for s in sections), "has_results": has_results(sections),
            "pub_types": ((rec.get("pubTypeList") or {}).get("pubType") or []),
            "url": ("https://pubmed.ncbi.nlm.nih.gov/%s/" % pmid) if pmid else ("https://doi.org/%s" % doi if doi else None),
            "doi_url": ("https://doi.org/%s" % doi) if doi else None, "is_open_access": rec.get("isOpenAccess") == "Y"}


def keep(c, excluded_pmids, excluded_dois):
    if c["source"] == "preprint" and c["server"] not in PREPRINT_SERVERS:
        return "server"
    if not c["sections"] or not (MIN_CHARS <= c["n_chars"] <= MAX_CHARS):
        return "length"
    if not c["has_results"]:
        return "no_results"
    if not c["year"] or not c["title"] or not c["authors"]:
        return "metadata"
    if c["pmid"] and str(c["pmid"]) in excluded_pmids:
        return "trial_bank"
    if c["doi"] and c["doi"].lower() in excluded_dois:
        return "trial_bank"
    if any(t.lower() in ("review", "systematic review", "meta-analysis", "editorial", "comment", "letter", "erratum") for t in c["pub_types"]):
        return "pub_type"
    if re.search(r"\b(review|meta-analysis|systematic review|protocol|erratum|correction)\b", c["title"], re.I):
        return "title_type"
    return None


def load_exclusions(bank_dir):
    pmids, dois = set(), set()
    if not bank_dir:
        return pmids, dois
    for path in glob.glob(os.path.join(bank_dir, "*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                bank = json.load(f)
        except ValueError:
            continue
        for it in bank.get("items", []):
            if it.get("pmid"):
                pmids.add(str(it["pmid"]))
            if it.get("doi"):
                dois.add(str(it["doi"]).lower())
    return pmids, dois


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-01-01")
    ap.add_argument("--end", default=date.today().isoformat())
    ap.add_argument("--page-size", type=int, default=1000)
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--exclude", default=None, help="a bank directory whose items' pmids/dois are dropped (the trial banks)")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--fields", nargs="+", default=list(FIELDS), help="fields to fetch (default all)")
    ap.add_argument("--sources", nargs="+", default=list(SOURCES), help="journal and/or preprint")
    ap.add_argument("--journals", nargs="*", default=None, help="restrict to these exact journal titles (JOURNAL:); 'top' = %s" % ", ".join(TOP_JOURNALS))
    ap.add_argument("--suffix", default="", help="suffix for raw file names, e.g. 'top' → <field>_<source>_top.json")
    a = ap.parse_args(argv)
    journals = TOP_JOURNALS if a.journals == ["top"] else (a.journals or None)
    os.makedirs(RAW_DIR, exist_ok=True)
    ex_pmids, ex_dois = load_exclusions(a.exclude)
    print("excluding %d pmids, %d dois" % (len(ex_pmids), len(ex_dois)))
    queries, counts, dropped, seen, candidates = {}, {}, {}, set(), []
    for field in a.fields:
        for source in a.sources:
            q = build_query(field, source, a.start, a.end, journals)
            queries["%s_%s" % (field, source)] = q
            print("%s / %s%s" % (field, source, " / " + ",".join(journals) if journals else ""))
            rows = fetch_query(q, a.page_size, a.pages)
            with open(os.path.join(RAW_DIR, "%s_%s%s.json" % (field, source, ("_" + a.suffix) if a.suffix else "")), "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False)
            kept = 0
            for rec in rows:
                c = normalise(rec, field, source)
                why = keep(c, ex_pmids, ex_dois)
                if why:
                    dropped[why] = dropped.get(why, 0) + 1
                    continue
                key = (c["doi"] or "").lower() or c["id"]
                if key in seen:
                    dropped["duplicate"] = dropped.get("duplicate", 0) + 1
                    continue
                seen.add(key)
                candidates.append(c)
                kept += 1
            counts["%s_%s" % (field, source)] = {"fetched": len(rows), "kept": kept}
            print("  kept %d of %d" % (kept, len(rows)))
    header = {"fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "api": API, "window": [a.start, a.end],
              "fields": a.fields, "sources": a.sources, "journals": journals,
              "queries": queries, "counts": counts, "dropped": dropped, "excluded_pmids": len(ex_pmids), "excluded_dois": len(ex_dois),
              "n": len(candidates), "filters": {"min_chars": MIN_CHARS, "max_chars": MAX_CHARS, "preprint_servers": sorted(PREPRINT_SERVERS),
                                                   "results_required": True}}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"header": header, "candidates": candidates}, f, ensure_ascii=False, indent=0)
    print(json.dumps({"n": len(candidates), "counts": counts, "dropped": dropped}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
