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
sys.path.insert(0, HERE)
import journals as journals_mod  # noqa: E402  (pipeline/journals.py: the leading-journal list, D23)
RAW_DIR = os.path.join(ROOT, "src", "raw")
OUT = os.path.join(ROOT, "src", "candidates.json")
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
API_POST = "https://www.ebi.ac.uk/europepmc/webservices/rest/searchPOST"     # same parameters, for queries too long for a GET URL

# The first three fields (requirement, 2026-10-23 14:14: recent articles and preprints on these topics, clinical studies left out).
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
    # added 2026-10-23 15:20 (requirement: an evolutionary-genomics field)
    "evogen": {
        "label": "evolutionary genomics",
        "terms": ['"molecular evolution"', "phylogenomic*", '"adaptive evolution"', '"positive selection"', '"comparative genomics"',
                  '"genome evolution"', "speciation", '"gene duplication"', '"horizontal gene transfer"', '"convergent evolution"',
                  '"population genomics"', '"experimental evolution"', '"evolutionary rate"', '"purifying selection"'],
        # D14: "speciation" alone also matches chemical speciation (tin in toothpaste, ion speciation in thermoelectrics)
        "require": ["genome", "genomes", "genomic", "gene", "genes", "phylogen*", "species", "lineage", "lineages", "organism*", "evolutionary"],
    },
    # added 2026-10-23 19:41 (requirement: a small-RNA / RNA-biology field — miRNA, piRNA and RNA biology)
    "smallrna": {
        "label": "small RNA / RNA biology",
        "terms": ["microRNA*", "miRNA*", "piRNA*", '"piwi-interacting"', "siRNA*", '"small RNA"', '"small RNAs"', '"tRNA-derived"', '"tRNA fragments"',
                  '"long noncoding RNA"', '"long non-coding RNA"', "lncRNA*", '"circular RNA"', "circRNA*", '"RNA modification"', '"RNA modifications"',
                  '"m6A"', '"RNA editing"', '"RNA interference"', '"RNA-binding protein"', '"RNA-binding proteins"', '"alternative splicing"',
                  '"RNA decay"', '"nonsense-mediated"', '"RNA structure"'],
        "require": ["RNA", "RNAs", "transcript*", "gene", "genes", "genome", "genomic", "cell", "cells", "organism*", "species", "mRNA"],
    },
    # added 2026-10-23 21:13 (requirement: the biology of piRNA and miRNA in transposon regulation and development, not biomarkers) — a
    # second query for the smallrna field ("as"): the small-RNA pathways themselves, in germline, development and transposon control,
    # with the clinical/biomarker vocabulary excluded. D23.
    "rnadev": {
        "label": "small RNA in development and transposon control",
        "as": "smallrna",
        "terms": ["piRNA*", '"piwi-interacting"', "PIWI", "Piwi", '"piRNA pathway"', '"transposon silencing"', '"transposable element silencing"',
                  '"TE silencing"', '"endo-siRNA"', '"endogenous siRNA"', '"endogenous small interfering"', '"RNA interference"', "RNAi",
                  '"maternal-to-zygotic"', '"maternal-zygotic"', '"let-7"', '"lin-4"', '"miRNA biogenesis"', '"microRNA biogenesis"', "Dicer",
                  "Drosha", "Argonaute", '"RNA-directed DNA methylation"', '"KRAB zinc finger"', '"KRAB-ZFP"', '"ping-pong"', '"22G-RNA"',
                  '"21U-RNA"', '"microRNA"', '"microRNAs"', "miRNA", "miRNAs", '"small RNA"', '"small RNAs"'],
        "require": ["development", "developmental", "embryo*", "germline", '"germ cells"', '"germ cell"', "gonad*", "testis", "testes", "ovary",
                    "ovaries", "oocyte*", "spermatogenesis", "oogenesis", "transposon*", "transposable", "retrotransposon*", "Drosophila",
                    "zebrafish", "Caenorhabditis", "elegans", "Arabidopsis", '"stem cell"', '"stem cells"', "differentiation", "pluripoten*"],
        "exclude": ["cancer", "tumor", "tumour", "carcinoma", "patients", "biomarker", "biomarkers", "serum", "plasma", "prognos*", "chemotherapy"],
    },
    # added 2026-10-23 21:13 (requirement: evolution in the sense of evo-devo and comparative genomics — distinct from the molecular-evolution
    # slice above, which stays). D23.
    "evodevo": {
        "label": "evo-devo / comparative genomics",
        "terms": ['"evo-devo"', '"evolutionary developmental"', '"evolution of development"', '"developmental evolution"', '"cis-regulatory evolution"',
                  '"regulatory evolution"', '"enhancer evolution"', '"gene regulatory network"', '"gene regulatory networks"', '"body plan"',
                  '"body plans"', "Hox", '"Hox genes"', '"comparative genomics"', '"comparative genomic"', '"gene family expansion"',
                  '"gene family evolution"', '"gene family expansions"', '"evolutionary novelty"', '"evolutionary novelties"', '"evolutionary innovation"',
                  '"convergent evolution"', '"co-option"', "cooption", '"deep homology"', '"morphological evolution"', '"phenotypic evolution"',
                  '"whole-genome duplication"', '"genome duplication"', '"conserved noncoding"', '"conserved non-coding"', "ultraconserved",
                  '"enhancer turnover"', '"lineage-specific genes"', '"de novo genes"', '"de novo gene"', '"gene loss"', '"regulatory landscape"',
                  '"evolution of gene regulation"'],
        "require": ["genome", "genomes", "genomic", "gene", "genes", "species", "lineage", "lineages", "development", "developmental", "embryo*",
                    "evolution*", "phylogen*"],
        "exclude": ["cancer", "tumor", "tumour", "carcinoma", "leukemia", "leukaemia", "lymphoma", "melanoma", "glioma", "patients"],
    },
    # added 2026-10-24 (requirement 2026-10-23 22:36/22:42: a field on epigenetics / genome regulation — the 2016–2026 window
    # kept, plus up to ~30 pre-2016 landmarks). The mechanism of genome regulation: chromatin, histone marks, DNA methylation,
    # Polycomb, enhancers, 3D genome organisation, X-inactivation and imprinting. Clinical/cancer vocabulary excluded to keep it
    # mechanistic and distinct from the cancer-genomics field. D26.
    "epi": {
        "label": "epigenetics / genome regulation",
        "terms": ['"epigenetic"', '"epigenetics"', '"epigenome"', '"epigenomic"', '"epigenomics"', '"chromatin"', '"chromatin accessibility"',
                  '"chromatin remodeling"', '"chromatin remodelling"', '"chromatin state"', '"chromatin states"', '"histone modification"',
                  '"histone modifications"', '"histone methylation"', '"histone acetylation"', '"histone variant"', '"histone variants"',
                  '"H3K27me3"', '"H3K4me3"', '"H3K9me3"', '"H3K27ac"', '"H3K36me3"', '"DNA methylation"', '"DNA demethylation"',
                  '"5-methylcytosine"', '"5-hydroxymethylcytosine"', '"CpG island"', '"CpG islands"', '"Polycomb"', '"Trithorax"', '"PRC2"',
                  '"PRC1"', '"enhancer"', '"enhancers"', '"super-enhancer"', '"super-enhancers"', '"cis-regulatory element"', '"nucleosome"',
                  '"nucleosomes"', '"nucleosome positioning"', '"topologically associating domain"', '"topologically associating domains"',
                  '"chromatin loop"', '"chromatin loops"', '"3D genome"', '"genome architecture"', '"genome organization"', '"genome folding"',
                  '"CTCF"', '"cohesin"', '"X-chromosome inactivation"', '"X chromosome inactivation"', '"X-inactivation"', '"dosage compensation"',
                  '"genomic imprinting"', '"imprinted gene"', '"imprinted genes"', '"heterochromatin"', '"euchromatin"', '"DNA methyltransferase"',
                  '"ten-eleven translocation"', '"pioneer factor"', '"pioneer transcription factor"', '"bivalent domain"', '"bivalent domains"'],
        "require": ["genome", "genomes", "genomic", "chromatin", "epigenetic*", "gene", "genes", "transcription*", "histone*", "methylation",
                    "cell", "cells", "nucleus", "nuclear", "regulatory", "embryo*", "development*"],
        "exclude": ["cancer", "tumor", "tumour", "carcinoma", "leukemia", "leukaemia", "lymphoma", "melanoma", "glioma", "patients",
                    "biomarker", "biomarkers", "prognos*", "chemotherapy"],
    },
    # added 2026-10-24 (requirement 13:48: an inflammaging / multi-omics-of-aging field). The molecular biology of ageing-associated
    # inflammation: inflammaging itself, immunosenescence, cellular senescence and the senescence-associated secretory phenotype,
    # the hallmarks of ageing, biological-age/omics ageing clocks, senolytics, and multi-omic studies of the ageing organism. Anchored
    # to an ageing term (require) and biased to molecular/omics findings; oncology vocabulary excluded to keep it distinct from the
    # cancer-genomics field. Biomarker/patient vocabulary is NOT excluded here (cohort omics is the core of the field). D29.
    "inflammaging": {
        "label": "inflammaging / multi-omics of ageing",
        "terms": ['"inflammaging"', '"inflamm-aging"', '"inflamm-ageing"', '"inflammageing"', '"inflammatory aging"', '"inflammatory ageing"',
                  '"immunosenescence"', '"immune senescence"', '"immune aging"', '"immune ageing"', '"immunosenescent"', '"T cell senescence"',
                  '"T-cell senescence"', '"cellular senescence"', '"senescent cell"', '"senescent cells"', '"cell senescence"',
                  '"senescence-associated secretory phenotype"', '"SASP"', '"senescence-associated beta-galactosidase"', '"oncogene-induced senescence"',
                  '"replicative senescence"', '"senolytic"', '"senolytics"', '"senomorphic"', '"senescence surveillance"', '"inflammasome"',
                  '"NLRP3 inflammasome"', '"hallmarks of aging"', '"hallmarks of ageing"', '"geroscience"', '"biological age"', '"biological aging"',
                  '"biological ageing"', '"aging clock"', '"ageing clock"', '"aging clocks"', '"proteomic clock"', '"proteomic aging clock"',
                  '"inflammatory clock"', '"inflammatory age"', '"iAge"', '"chronic low-grade inflammation"', '"low-grade inflammation"',
                  '"sterile inflammation"', '"aging atlas"', '"ageing atlas"', '"single-cell aging"', '"single-cell ageing"', '"aging transcriptome"',
                  '"aging proteome"', '"aging methylome"', '"aging metabolome"', '"multi-omic aging"', '"multi-omic ageing"', '"cGAS-STING"',
                  '"stem cell aging"', '"stem cell ageing"', '"hematopoietic aging"', '"clonal hematopoiesis"', '"clonal haematopoiesis"'],
        "require": ["aging", "ageing", "aged", "age-related", "age-associated", "age-dependent", "senescen*", "longevity", "lifespan",
                    "healthspan", "geroscience", "elderly", "older", "centenarian*", "inflammaging", "immunosenescence", "old age", "gerontol*"],
        "exclude": ["cancer", "tumor", "tumour", "carcinoma", "leukemia", "leukaemia", "lymphoma", "melanoma", "glioma", "sarcoma",
                    "chemotherapy", "radiotherapy", "neoadjuvant"],
    },
}
# journal-targeted top-up (requirement 15:20: more papers from Nature, Cell, Genome Biology and Nature Communications;
# 19:41: Nature, Cell, Science and journals of that rank, from 2020 on)
TOP_JOURNALS = ["Nature", "Cell", "Genome Biology", "Nature Communications"]
TOP_JOURNALS_V2 = TOP_JOURNALS + ["Science", "Nature Genetics", "Nature Methods", "Nature Biotechnology", "Cell Genomics", "Molecular Cell",
                                  "Science Advances", "Genome Research", "Nucleic Acids Research"]
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
    if f.get("exclude"):
        q += " NOT (%s)" % " OR ".join("ABSTRACT:%s" % w for w in f["exclude"])
    if journals:
        q += " AND (%s)" % " OR ".join('JOURNAL:"%s"' % j for j in journals)
    q += " AND %s AND FIRST_PDATE:[%s TO %s] AND HAS_ABSTRACT:y" % (SOURCES[source], start, end)
    if source == "journal":
        q += ' NOT PUB_TYPE:"Review" NOT PUB_TYPE:"Editorial" NOT PUB_TYPE:"Comment" NOT PUB_TYPE:"Letter"'
    return q


def fetch_query(query, page_size=1000, max_pages=1, log=print, opener=None, sleep=0.5, sort=None):
    """sort=None: Europe PMC relevance; sort="cited": most-cited first (the landmark fetch, D18)."""
    opener = opener or urllib.request.urlopen
    out, cursor = [], "*"
    for page in range(max_pages):
        params = {"query": query, "resultType": "core", "format": "json", "pageSize": str(page_size), "cursorMark": cursor}
        if sort == "cited":
            params["sort"] = "CITED desc"
        url = API + "?" + urllib.parse.urlencode(params)
        if len(url) > 4000:          # the 82-journal list (D23) pushes the query past what a GET URL should carry; the REST service takes POST
            url = urllib.request.Request(API_POST, data=urllib.parse.urlencode(params).encode("utf-8"), method="POST")
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


MIN_NUMBERED = 3


def has_results(sections, min_numbered=None):
    labels = [s["label"].lower() for s in sections if s.get("label")]
    if labels:
        return any(any(h in lab for h in RESULT_HEADINGS) for lab in labels)
    # unstructured: at least MIN_NUMBERED sentences carrying a number (the landmark fetch relaxes this to 1, D18)
    text = " ".join(s["text"] for s in sections)
    numbered = [s for s in re.split(r"(?<=[.!?])\s+", text) if re.search(r"\d", s)]
    return len(numbered) >= (MIN_NUMBERED if min_numbered is None else min_numbered)


def normalise(rec, field, source, min_numbered=None):
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
            "date": rec.get("firstPublicationDate"), "field": FIELDS[field].get("as", field), "query_field": field, "sections": sections, "n_chars": len(text),
            "structured": any(s.get("label") for s in sections), "has_results": has_results(sections, min_numbered),
            "cited_by": rec.get("citedByCount"),
            "pub_types": ((rec.get("pubTypeList") or {}).get("pubType") or []),
            "url": ("https://pubmed.ncbi.nlm.nih.gov/%s/" % pmid) if pmid else ("https://doi.org/%s" % doi if doi else None),
            "doi_url": ("https://doi.org/%s" % doi) if doi else None, "is_open_access": rec.get("isOpenAccess") == "Y"}


def keep(c, excluded_pmids, excluded_dois, journal_ok=None):
    """journal_ok: a predicate on the journal title for a journal-restricted fetch — JOURNAL:"Development" also returns records
    whose title merely begins that way, so the exact list is enforced here too (D23)."""
    if c["source"] == "preprint" and c["server"] not in PREPRINT_SERVERS:
        return "server"
    if journal_ok and c["source"] == "journal" and not journal_ok(c["journal"]):
        return "journal_not_listed"
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
    ap.add_argument("--journals", nargs="*", default=None, help="restrict to these exact journal titles (JOURNAL:); 'top' = %s; 'top2' = those + %s; 'leading' = the %d journals of pipeline/journals.py (D23)" % (", ".join(TOP_JOURNALS), ", ".join(TOP_JOURNALS_V2[4:]), len(journals_mod.LEADING)))
    ap.add_argument("--suffix", default="", help="suffix for raw file names, e.g. 'top' → <field>_<source>_top.json")
    ap.add_argument("--sort", choices=["relevance", "cited"], default="relevance", help="cited = most-cited first (landmark fetch, D18)")
    ap.add_argument("--min-numbered", type=int, default=None, help="unstructured abstracts: sentences with a number needed (default %d)" % MIN_NUMBERED)
    a = ap.parse_args(argv)
    journals = (TOP_JOURNALS if a.journals == ["top"] else TOP_JOURNALS_V2 if a.journals == ["top2"]
                else journals_mod.QUERY_TOKENS if a.journals == ["leading"] else (a.journals or None))
    journal_ok = journals_mod.is_leading if a.journals == ["leading"] else None
    os.makedirs(RAW_DIR, exist_ok=True)
    ex_pmids, ex_dois = load_exclusions(a.exclude)
    print("excluding %d pmids, %d dois" % (len(ex_pmids), len(ex_dois)))
    queries, counts, dropped, seen, candidates = {}, {}, {}, set(), []
    for field in a.fields:
        for source in a.sources:
            q = build_query(field, source, a.start, a.end, journals)
            queries["%s_%s" % (field, source)] = q
            print("%s / %s%s" % (field, source, " / " + ",".join(journals) if journals else ""))
            rows = fetch_query(q, a.page_size, a.pages, sort=None if a.sort == "relevance" else a.sort)
            with open(os.path.join(RAW_DIR, "%s_%s%s.json" % (field, source, ("_" + a.suffix) if a.suffix else "")), "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False)
            kept = 0
            for rec in rows:
                c = normalise(rec, field, source, a.min_numbered)
                why = keep(c, ex_pmids, ex_dois, journal_ok)
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
              "fields": a.fields, "sources": a.sources, "journals": journals, "journals_arg": a.journals, "sort": a.sort, "min_numbered": a.min_numbered if a.min_numbered is not None else MIN_NUMBERED,
              "queries": queries, "counts": counts, "dropped": dropped, "excluded_pmids": len(ex_pmids), "excluded_dois": len(ex_dois),
              "n": len(candidates), "filters": {"min_chars": MIN_CHARS, "max_chars": MAX_CHARS, "preprint_servers": sorted(PREPRINT_SERVERS),
                                                   "results_required": True}}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"header": header, "candidates": candidates}, f, ensure_ascii=False, indent=0)
    print(json.dumps({"n": len(candidates), "counts": counts, "dropped": dropped}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
