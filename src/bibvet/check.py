"""Compare parsed entries against registry records and flag problems."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from .model import Entry, EntryResult, RegistryRecord

TITLE_OK = 0.95
TITLE_MINOR = 0.80
TITLE_SUGGEST = 0.90


def normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_similarity(a: str, b: str) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    ratio = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    jaccard = len(ta & tb) / max(1, len(ta | tb))
    return max(ratio, jaccard)


def _norm_pages(p: str) -> str:
    return re.sub(r"\s+", "", (p or "")).replace("--", "-").replace("–", "-").replace("—", "-")


def _family_match(a: str, b: str) -> bool:
    return normalize_text(a) == normalize_text(b)


def compare(entry: Entry, record: RegistryRecord, result: EntryResult) -> None:
    """Field-by-field comparison; appends issues to result."""
    if entry.title and record.title:
        sim = title_similarity(entry.title, record.title)
        if sim < TITLE_MINOR:
            result.add("error", "title-mismatch",
                       f"Title differs from registry record (similarity {sim:.2f}).\n"
                       f"      yours:   {entry.title}\n"
                       f"      registry: {record.title}")
        elif sim < TITLE_OK:
            result.add("warning", "title-differs",
                       f"Title slightly differs from registry (similarity {sim:.2f}): \"{record.title}\"")
    if entry.year and record.year:
        try:
            ey = int(re.search(r"\d{4}", entry.year).group(0))
            if ey != record.year:
                diff = abs(ey - record.year)
                level = "warning" if diff == 1 else "error"
                note = " (could be online-first vs print year)" if diff == 1 else ""
                result.add(level, "year-mismatch",
                           f"Year mismatch: yours {ey}, registry {record.year}{note}")
        except (AttributeError, ValueError):
            result.add("warning", "year-unparsed", f"Could not parse year: {entry.year!r}")
    if entry.journal and record.container:
        sim = title_similarity(entry.journal, record.container)
        if sim < 0.6:
            result.add("warning", "journal-mismatch",
                       f"Journal differs: yours \"{entry.journal}\", registry \"{record.container}\"")
    entry_volume = entry.get("volume")
    if entry_volume and record.volume and entry_volume != record.volume:
        result.add("warning", "volume-mismatch",
                   f"Volume mismatch: yours {entry_volume}, registry {record.volume}")
    entry_pages = entry.get("pages")
    if entry_pages and record.pages and _norm_pages(entry_pages) != _norm_pages(record.pages):
        result.add("warning", "pages-mismatch",
                   f"Pages mismatch: yours {entry_pages}, registry {record.pages}")
    fams = entry.author_families
    if fams and record.author_families:
        if not _family_match(fams[0], record.author_families[0]):
            result.add("warning", "first-author-mismatch",
                       f"First author differs: yours {fams[0]}, registry {record.author_families[0]}")
        elif len(fams) != len(record.author_families):
            result.add("info", "author-count",
                       f"Author count differs: yours {len(fams)}, registry {len(record.author_families)}")


def check_entry(entry: Entry, resolver, offline: bool = False) -> EntryResult:
    result = EntryResult(entry=entry)

    if not entry.title and not entry.doi:
        result.add("error", "empty-entry", "Entry has neither a title nor a DOI; cannot verify.")
        return result
    if entry.entry_type in ("article", "inproceedings") and not entry.year:
        result.add("warning", "missing-year", "No year field.")
    if offline:
        result.add("info", "offline", "Offline mode: registry checks skipped.")
        return result

    if entry.doi:
        record = resolver.by_doi(entry.doi)
        if record is None:
            result.add("error", "doi-not-found",
                       f"DOI does not resolve in Crossref or OpenAlex: {entry.doi}")
            return result
        result.record = record
        compare(entry, record, result)
        return result

    # No DOI: try to find the paper by title. A perfect title match is
    # NOT enough on its own (different works share titles, e.g. book
    # chapters) — require corroboration from year / first author /
    # journal whenever the entry provides them.
    if entry.title:
        candidates = resolver.by_title(entry.title)
        scored = [(title_similarity(entry.title, c.title), c) for c in candidates]
        scored.sort(key=lambda t: t[0], reverse=True)

        def corroborates(rec) -> bool:
            # Allow at most one disagreeing field (that may be exactly
            # the error the user wants flagged) but require >= 2 agreeing
            # fields. The same-title trap scores 0 and is rejected.
            checks = []
            if entry.year and rec.year:
                m = re.search(r"\d{4}", entry.year)
                if m:
                    checks.append(int(m.group(0)) == rec.year)
            fams = entry.author_families
            if fams and rec.author_families:
                checks.append(_family_match(fams[0], rec.author_families[0]))
            if entry.journal and rec.container:
                checks.append(title_similarity(entry.journal, rec.container) >= 0.5)
            agree = sum(checks)
            return agree >= 2 and agree >= len(checks) - 1

        passing = [(s, c) for s, c in scored if s >= TITLE_SUGGEST and corroborates(c)]
        if not passing and scored and scored[0][0] >= 0.98 and not (
            entry.year or entry.author_families or entry.journal
        ):
            passing = scored[:1]  # title-only entry: accept near-exact match
        if passing:
            best_sim, best = passing[0]
            result.record = best
            result.add("info", "doi-suggested",
                       f"No DOI given; title matches registry record (similarity {best_sim:.2f}). "
                       f"Suggested DOI: {best.doi}")
            compare(entry, best, result)
        elif scored and scored[0][0] >= 0.6:
            best_sim, best = scored[0]
            result.add("warning", "possible-match",
                       f"No DOI given; closest title match is uncertain (similarity {best_sim:.2f}): "
                       f"\"{best.title}\" ({best.doi or 'no DOI'})")
        else:
            result.add("warning", "not-found",
                       "No DOI given and no confident registry match by title.")
    return result


def check_duplicates(results: list[EntryResult]) -> None:
    seen_doi: dict[str, EntryResult] = {}
    seen_title: dict[str, EntryResult] = {}
    for r in results:
        doi = (r.entry.doi or (r.record.doi if r.record else "")).lower()
        if doi:
            if doi in seen_doi:
                r.add("error", "duplicate",
                      f"Duplicate of entry \"{seen_doi[doi].entry.key}\" (same DOI {doi}).")
            else:
                seen_doi[doi] = r
        nt = normalize_text(r.entry.title)
        if nt:
            if nt in seen_title and seen_title[nt] is not r:
                if not any(i.code == "duplicate" for i in r.issues):
                    r.add("warning", "duplicate-title",
                          f"Same title as entry \"{seen_title[nt].entry.key}\".")
            else:
                seen_title.setdefault(nt, r)
