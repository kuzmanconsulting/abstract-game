#!/usr/bin/env python3
"""Leading journals (D23; requirement 2026-10-23 21:14/21:16: enrich the corpus from Q1 journals rather than from
lower-ranked ones, and offer a filter for them on the page).

A curated list, not a bibliometric quartile: by SCImago (SJR) or JCR quartile, Scientific Reports, PLoS ONE, the MDPI and
Frontiers titles and most BMC journals are Q1 in at least one category, which is not what "Q1" means in conversation. The
list below is the selective journals of the game's fields — the Nature, Cell and Science research families, PNAS, eLife,
the genome/genetics/evolution/RNA/development society and specialist journals, and the leading cancer and medical
journals the cfDNA and cancer-genomics slices draw on. Edit it here; the fetch, the build and the page read it.

Two forms are needed: the NLM abbreviation for the Europe PMC query (JOURNAL: is an exact match on the title or its
abbreviation: JOURNAL:"Nature" does not match "Nature communications") and the canonical name for matching the title
Europe PMC returns in a record ("Science (New York, N.Y.)", "Journal of clinical oncology : official journal of …").

    python3 pipeline/journals.py            # prints the list and checks the canonical forms are unique
"""
import re

# (display name, NLM abbreviation used in the query)
LEADING = [
    # multidisciplinary
    ("Nature", "Nature"), ("Science", "Science"), ("Cell", "Cell"),
    ("PNAS", "Proc Natl Acad Sci U S A"), ("Nature Communications", "Nat Commun"), ("Science Advances", "Sci Adv"), ("eLife", "Elife"),
    ("PLoS Biology", "PLoS Biol"),
    # genomics, genetics, evolution
    ("Nature Genetics", "Nat Genet"), ("Nature Methods", "Nat Methods"), ("Nature Biotechnology", "Nat Biotechnol"),
    ("Nature Ecology & Evolution", "Nat Ecol Evol"), ("Cell Genomics", "Cell Genom"), ("Genome Biology", "Genome Biol"),
    ("Genome Research", "Genome Res"), ("Genome Medicine", "Genome Med"), ("Nucleic Acids Research", "Nucleic Acids Res"),
    ("American Journal of Human Genetics", "Am J Hum Genet"), ("PLoS Genetics", "PLoS Genet"), ("PLoS Computational Biology", "PLoS Comput Biol"),
    ("Genetics", "Genetics"), ("Molecular Biology and Evolution", "Mol Biol Evol"), ("Genome Biology and Evolution", "Genome Biol Evol"),
    ("Systematic Biology", "Syst Biol"), ("Evolution", "Evolution"), ("Molecular Ecology", "Mol Ecol"), ("Mobile DNA", "Mob DNA"),
    ("Molecular Systems Biology", "Mol Syst Biol"),
    # molecular, cell and developmental biology
    ("Molecular Cell", "Mol Cell"), ("Developmental Cell", "Dev Cell"), ("Cell Reports", "Cell Rep"), ("Cell Stem Cell", "Cell Stem Cell"),
    ("Cell Systems", "Cell Syst"), ("Cell Research", "Cell Res"), ("Current Biology", "Curr Biol"), ("Development", "Development"),
    ("Genes & Development", "Genes Dev"), ("The EMBO Journal", "EMBO J"), ("EMBO Reports", "EMBO Rep"), ("RNA", "RNA"),
    ("Nature Cell Biology", "Nat Cell Biol"), ("Nature Structural & Molecular Biology", "Nat Struct Mol Biol"),
    ("Nature Chemical Biology", "Nat Chem Biol"), ("Nature Metabolism", "Nat Metab"), ("Cell Metabolism", "Cell Metab"),
    ("Nature Aging", "Nat Aging"), ("Nature Neuroscience", "Nat Neurosci"), ("Neuron", "Neuron"),
    # plants, microbes
    ("Nature Plants", "Nat Plants"), ("The Plant Cell", "Plant Cell"), ("New Phytologist", "New Phytol"),
    ("Nature Microbiology", "Nat Microbiol"), ("Cell Host & Microbe", "Cell Host Microbe"), ("The ISME Journal", "ISME J"),
    # immunology
    ("Immunity", "Immunity"), ("Nature Immunology", "Nat Immunol"), ("Science Immunology", "Sci Immunol"), ("Journal of Experimental Medicine", "J Exp Med"),
    # cancer and medicine (the cfDNA and cancer-genomics slices)
    ("Nature Medicine", "Nat Med"), ("Nature Cancer", "Nat Cancer"), ("Cancer Cell", "Cancer Cell"), ("Cancer Discovery", "Cancer Discov"),
    ("Blood Cancer Discovery", "Blood Cancer Discov"), ("Cancer Research", "Cancer Res"), ("Clinical Cancer Research", "Clin Cancer Res"),
    ("Journal of Clinical Oncology", "J Clin Oncol"), ("Annals of Oncology", "Ann Oncol"), ("The Lancet Oncology", "Lancet Oncol"),
    ("JAMA Oncology", "JAMA Oncol"), ("Journal of the National Cancer Institute", "J Natl Cancer Inst"),
    ("Science Translational Medicine", "Sci Transl Med"), ("The New England Journal of Medicine", "N Engl J Med"), ("The Lancet", "Lancet"),
    ("JAMA", "JAMA"), ("BMJ", "BMJ"), ("Blood", "Blood"), ("Leukemia", "Leukemia"), ("Haematologica", "Haematologica"),
    ("Gut", "Gut"), ("Gastroenterology", "Gastroenterology"), ("Hepatology", "Hepatology"), ("Journal of Hepatology", "J Hepatol"),
]
# titles Europe PMC returns that do not reduce to the display name by canon() alone
ALIASES = {
    "proceedings of the national academy of sciences of the united states of america": "PNAS",
    "proceedings of the national academy of sciences": "PNAS",
    "bmj (clinical research ed.)": "BMJ",
    "lancet": "The Lancet",
    "lancet. oncology": "The Lancet Oncology",
    "lancet oncology": "The Lancet Oncology",
}
QUERY_TOKENS = [abbr for _, abbr in LEADING]


def canon(title):
    """'Science (New York, N.Y.)' → 'science'; 'Journal of clinical oncology : official journal of …' → 'journal of clinical oncology';
    'Evolution; international journal of organic evolution' → 'evolution'; 'The EMBO journal' → 'embo journal'; '&' → 'and'."""
    t = (title or "").lower().strip()
    t = re.sub(r"\s*\([^)]*\)", "", t)
    t = re.split(r"\s+:\s|;", t)[0]
    t = t.replace("&", "and").replace(".", "")
    t = re.sub(r"^the\s+", "", t)
    return re.sub(r"\s+", " ", t).strip()


_CANON = {}
for _d, _a in LEADING:
    _CANON[canon(_d)] = _d
    _CANON[canon(_a)] = _d
for _k, _v in ALIASES.items():
    _CANON[canon(_k)] = _v


def leading_name(title):
    """The display name when `title` (as Europe PMC returns it, or an abbreviation) is a leading journal, else None."""
    return _CANON.get(canon(title))


def is_leading(title):
    return leading_name(title) is not None


def display(title):
    """Display form of any journal title: the leading-list name when known, else the title with the parenthetical city
    and the ': official journal of …' tail removed ('Science (New York, N.Y.)' → 'Science')."""
    name = leading_name(title)
    if name:
        return name
    t = re.sub(r"\s*\([^)]*\)", "", title or "")
    return re.split(r"\s+:\s", t)[0].strip() or title


if __name__ == "__main__":
    names = [d for d, _ in LEADING]
    assert len(names) == len(set(names)), "duplicate display names"
    for d, a in LEADING:
        assert leading_name(d) == d and leading_name(a) == d, (d, a)
    for probe in ("Science (New York, N.Y.)", "Development (Cambridge, England)", "Current biology : CB", "RNA (New York, N.Y.)",
                  "Evolution; international journal of organic evolution", "The EMBO journal", "Genes & development", "Lancet (London, England)",
                  "The Lancet. Oncology", "Journal of clinical oncology : official journal of the American Society of Clinical Oncology",
                  "Proceedings of the National Academy of Sciences of the United States of America", "BMJ (Clinical research ed.)", "eLife", "Nature communications"):
        assert is_leading(probe), probe
    for probe in ("Scientific reports", "International journal of molecular sciences", "Frontiers in plant science", "PloS one", "BMC genomics", "bioRxiv", None):
        assert not is_leading(probe), probe
    print("%d leading journals, %d canonical forms" % (len(LEADING), len(_CANON)))
    for d, a in LEADING:
        print("%-45s %s" % (d, a))
