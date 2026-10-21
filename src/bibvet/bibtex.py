"""Minimal, dependency-free BibTeX parser and writer.

Good enough for real-world .bib files: braced / quoted / bare values,
nested braces in titles, @string expansion, @comment/@preamble skipping.
"""

from __future__ import annotations

import re

from .model import Entry

_FIELD_ORDER = [
    "author", "title", "journal", "booktitle", "year", "volume", "number",
    "pages", "publisher", "doi", "url", "note",
]


def _scan_value(text: str, i: int, strings: dict) -> tuple[str, int]:
    """Read one field value starting at index i; return (value, next_index)."""
    n = len(text)
    while i < n and text[i] in " \t\r\n":
        i += 1
    if i >= n:
        return "", i
    if text[i] == "{":
        depth = 0
        start = i + 1
        while i < n:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i].strip(), i + 1
            i += 1
        return text[start:].strip(), n
    if text[i] == '"':
        i += 1
        start = i
        while i < n and text[i] != '"':
            if text[i] == "\\":
                i += 1
            i += 1
        return text[start:i].strip(), min(i + 1, n)
    # bare token (number or @string name), possibly concatenated with # parts
    start = i
    while i < n and text[i] not in ",}":
        i += 1
    token = text[start:i].strip()
    if "#" in token:
        parts = [p.strip().strip("{}").strip('"') for p in token.split("#")]
        return "".join(strings.get(p.lower(), p) for p in parts), i
    return strings.get(token.lower(), token), i


def parse_bibtex(text: str) -> list[Entry]:
    entries: list[Entry] = []
    strings: dict[str, str] = {}
    pos = 0
    n = len(text)
    while True:
        at = text.find("@", pos)
        if at == -1:
            break
        m = re.match(r"@\s*([A-Za-z]+)\s*\{", text[at:])
        if not m:
            pos = at + 1
            continue
        entry_type = m.group(1).lower()
        body_start = at + m.end()
        if entry_type in ("comment", "preamble"):
            # skip balanced block
            depth, i = 1, body_start
            while i < n and depth:
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                i += 1
            pos = i
            continue
        if entry_type == "string":
            eq = text.find("=", body_start)
            end = text.find("}", body_start)
            if eq != -1 and end != -1:
                name = text[body_start:eq].strip().lower()
                value, _ = _scan_value(text, eq + 1, strings)
                strings[name] = value
            pos = (end + 1) if end != -1 else n
            continue
        # regular entry: key up to first comma
        comma = text.find(",", body_start)
        if comma == -1:
            break
        key = text[body_start:comma].strip()
        fields: dict[str, str] = {}
        i = comma + 1
        while i < n:
            while i < n and text[i] in " \t\r\n,":
                i += 1
            if i >= n:
                break
            if text[i] == "}":
                i += 1
                break
            fm = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=", text[i:])
            if not fm:
                i += 1
                continue
            fname = fm.group(1).lower()
            value, i = _scan_value(text, i + fm.end(), strings)
            value = re.sub(r"\s+", " ", value).strip()
            if fname == "doi":
                value = normalize_doi(value)
            fields[fname] = value
        entries.append(Entry(key=key, entry_type=entry_type, fields=fields,
                             raw=text[at:i].strip()))
        pos = i
    return entries


def normalize_doi(value: str) -> str:
    v = value.strip()
    v = re.sub(r"^https?://(dx\.)?doi\.org/", "", v, flags=re.I)
    v = re.sub(r"^doi:\s*", "", v, flags=re.I)
    return v.strip().rstrip(".")


def entry_to_bibtex(entry: Entry, record=None, fix: bool = False) -> str:
    fields = dict(entry.fields)
    if fix and record is not None:
        if record.title:
            fields["title"] = record.title
        if record.authors_full:
            fields["author"] = " and ".join(record.authors_full)
        if record.year:
            fields["year"] = str(record.year)
        if record.container:
            key = "booktitle" if entry.entry_type in ("inproceedings", "conference") else "journal"
            fields[key] = record.container
        if record.volume:
            fields["volume"] = record.volume
        if record.issue:
            fields["number"] = record.issue
        if record.pages:
            fields["pages"] = record.pages.replace("-", "--", 1) if "--" not in record.pages else record.pages
        if record.publisher:
            fields["publisher"] = record.publisher
        if record.doi:
            fields["doi"] = record.doi
    ordered = [k for k in _FIELD_ORDER if k in fields]
    ordered += [k for k in fields if k not in _FIELD_ORDER]
    lines = [f"@{entry.entry_type}{{{entry.key},"]
    for k in ordered:
        lines.append(f"  {k} = {{{fields[k]}}},")
    lines.append("}")
    return "\n".join(lines)
