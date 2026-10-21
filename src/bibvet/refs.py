"""Parse plain-text reference lists.

Handles the formats researchers actually paste out of Word / PDFs:
- one DOI (or doi.org URL) per line
- numbered lists ``[1] ...`` / ``1. ...``
- GB/T 7714 style: ``Authors. Title[J]. Journal, Year, Vol(Issue): Pages.``
- APA-ish style: ``Authors (Year). Title. Journal, ...``

The parser is heuristic: it extracts a DOI when present, a year, and a
best-effort title. Verification (Crossref/OpenAlex title search) does
the heavy lifting afterwards.
"""

from __future__ import annotations

import re

from .bibtex import normalize_doi
from .model import Entry

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
_YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
_MARKER_RE = re.compile(r"\[(J|M|C|D|R|EB/OL|J/OL)\]", re.I)
_NUMBERING_RE = re.compile(r"^\s*(?:\[\d{1,4}\]\s*|\d{1,3}\.\s+|\d{1,3}\)\s*|\d{1,3}、\s*)")


def extract_doi(text: str) -> str:
    m = DOI_RE.search(text or "")
    if not m:
        return ""
    return normalize_doi(m.group(0))


def clean_doi_candidate(raw: str) -> str:
    return normalize_doi(raw).rstrip(")").rstrip("]")


def _is_doi_only(line: str) -> bool:
    stripped = _NUMBERING_RE.sub("", line).strip()
    return bool(DOI_RE.fullmatch(stripped)) or bool(
        re.fullmatch(r"https?://(dx\.)?doi\.org/\S+", stripped, re.I)
    )


def _split_blocks(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    blocks: list[str] = []
    current: list[str] = []
    for ln in lines:
        if not ln:
            if current:
                blocks.append(" ".join(current))
                current = []
            continue
        if _is_doi_only(ln):
            if current:
                blocks.append(" ".join(current))
                current = []
            blocks.append(ln)
            continue
        if _NUMBERING_RE.match(ln) and current:
            blocks.append(" ".join(current))
            current = [ln]
        else:
            current.append(ln)
    if current:
        blocks.append(" ".join(current))
    return [b for b in blocks if b]


def _gbt_authors(segment: str) -> str:
    """'LeCun Y, Bengio Y, Hinton G' / '..., et al.' -> BibTeX 'and' form."""
    segment = re.sub(r",?\s*et al\.?$", "", segment.strip(), flags=re.I)
    names = re.findall(r"[A-ZÀ-Þ][A-Za-zÀ-ÿ'’\-]+(?:\s+[A-Z]{1,3})+", segment)
    if names:
        return " and ".join(n.strip() for n in names)
    return segment


def _parse_one(block: str, idx: int) -> Entry:
    original = block
    block = _NUMBERING_RE.sub("", block).strip()
    fields: dict[str, str] = {}

    doi = extract_doi(block)
    if doi:
        fields["doi"] = clean_doi_candidate(doi)

    ym = _YEAR_RE.search(block)
    if ym:
        fields["year"] = ym.group(1)

    marker = _MARKER_RE.search(block)
    if marker:
        # GB/T 7714: "Authors. Title[J]. Journal, Year, ..."
        head = block[:marker.start()].rstrip(". ").strip()
        tail = block[marker.end():].lstrip(". ").strip()
        # authors end at the first ". " that follows a name token
        if ". " in head:
            _, _, title = head.partition(". ")
            fields["title"] = title.strip().rstrip(".")
        else:
            fields["title"] = head
        journal = tail.split(",")[0].strip()
        if journal:
            fields["journal"] = journal
        vm = re.search(r",\s*(\d+)\s*(?:\((\d+)\))?\s*:\s*([0-9]+[-–][0-9]+|[0-9]+)", tail)
        if vm:
            fields["volume"] = vm.group(1)
            if vm.group(2):
                fields["number"] = vm.group(2)
            fields["pages"] = vm.group(3).replace("–", "-")
        am = head.split(". ")[0] if ". " in head else ""
        if am and len(am) < 200:
            fields["author"] = _gbt_authors(am)
    else:
        # APA-ish: "Authors (2015). Title. Journal, 521, 436-444."
        m = re.match(r"^(.*?)\((\d{4})\)\.\s*(.*?)\.\s*(.*)$", block)
        if m:
            fields["author"] = m.group(1).strip()
            fields["year"] = m.group(2)
            fields["title"] = m.group(3).strip()
            rest = m.group(4)
            if rest:
                fields["journal"] = rest.split(",")[0].strip()
        else:
            # Fallback: drop the DOI tail; the longest sentence-like chunk
            # is our best title guess. Title search will arbitrate.
            text_wo_doi = DOI_RE.sub("", block).strip(" .")
            chunks = [c.strip() for c in re.split(r"\.\s+", text_wo_doi) if len(c.strip()) > 8]
            if chunks:
                fields["title"] = max(chunks, key=len)
            else:
                fields["title"] = text_wo_doi

    return Entry(key=f"ref{idx}", entry_type="article", fields=fields, raw=original)


def parse_text_references(text: str) -> list[Entry]:
    blocks = _split_blocks(text)
    entries = []
    for i, block in enumerate(blocks, 1):
        # a line that is *only* a DOI/URL
        stripped = _NUMBERING_RE.sub("", block).strip()
        if DOI_RE.fullmatch(stripped) or re.fullmatch(
            r"https?://(dx\.)?doi\.org/\S+", stripped, re.I
        ):
            entries.append(Entry(key=f"ref{i}", fields={"doi": clean_doi_candidate(extract_doi(stripped))}, raw=block))
            continue
        entries.append(_parse_one(block, i))
    return entries


def looks_like_bibtex(text: str) -> bool:
    return bool(re.search(r"@\s*(article|book|inproceedings|misc|phdthesis|mastersthesis|techreport|incollection)\s*\{", text, re.I))
