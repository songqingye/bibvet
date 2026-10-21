"""Registry clients: Crossref first, OpenAlex as fallback.

Standard library only (urllib). Both APIs are free and need no key;
passing an email puts requests in Crossref's 'polite pool'.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from .model import RegistryRecord

CROSSREF_API = "https://api.crossref.org"
OPENALEX_API = "https://api.openalex.org"


class HttpJson:
    def __init__(self, email: str = "", timeout: float = 20.0):
        self.email = email
        self.timeout = timeout

    def get(self, url: str):
        headers = {
            "User-Agent": f"bibvet/0.1 (https://pypi.org/project/bibvet; mailto:{self.email or 'noreply@example.com'})",
            "Accept": "application/json",
        }
        req = urllib.request.Request(url, headers=headers)
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code in (429, 500, 502, 503) and attempt == 0:
                    time.sleep(1.5)
                    continue
                return None
            except Exception:
                if attempt == 0:
                    time.sleep(1.0)
                    continue
                return None
        return None


def _crossref_year(msg: dict) -> int | None:
    for key in ("published-print", "published-online", "published", "issued", "created"):
        parts = (msg.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                pass
    return None


def normalize_crossref(msg: dict) -> RegistryRecord:
    authors, full = [], []
    for a in msg.get("author") or []:
        fam = (a.get("family") or "").strip()
        given = (a.get("given") or "").strip()
        if fam:
            authors.append(fam)
            full.append(f"{given} {fam}".strip())
        elif a.get("name"):
            authors.append(a["name"])
            full.append(a["name"])
    titles = msg.get("title") or []
    containers = msg.get("container-title") or []
    return RegistryRecord(
        doi=(msg.get("DOI") or "").strip(),
        title=(titles[0] if titles else "").strip(),
        author_families=authors,
        authors_full=full,
        year=_crossref_year(msg),
        container=(containers[0] if containers else "").strip(),
        volume=(msg.get("volume") or "").strip(),
        issue=(msg.get("issue") or "").strip(),
        pages=(msg.get("page") or "").strip(),
        publisher=(msg.get("publisher") or "").strip(),
        type=(msg.get("type") or "").strip(),
        source="crossref",
    )


def normalize_openalex(w: dict) -> RegistryRecord:
    authors, full = [], []
    for auth in w.get("authorships") or []:
        name = ((auth.get("author") or {}).get("display_name") or "").strip()
        if name:
            full.append(name)
            authors.append(name.split()[-1])
    biblio = w.get("biblio") or {}
    pages = ""
    if biblio.get("first_page"):
        pages = biblio["first_page"]
        if biblio.get("last_page") and biblio["last_page"] != biblio["first_page"]:
            pages += f"-{biblio['last_page']}"
    source = ((w.get("primary_location") or {}).get("source") or {})
    doi = (w.get("doi") or "")
    doi = re.sub(r"^https?://doi\.org/", "", doi)
    return RegistryRecord(
        doi=doi.strip(),
        title=(w.get("display_name") or w.get("title") or "").strip(),
        author_families=authors,
        authors_full=full,
        year=w.get("publication_year"),
        container=(source.get("display_name") or "").strip(),
        volume=(biblio.get("volume") or "").strip(),
        issue=(biblio.get("issue") or "").strip(),
        pages=pages,
        publisher=(source.get("host_organization_name") or "").strip(),
        type=(w.get("type") or "").strip(),
        source="openalex",
    )


class Resolver:
    """DOI lookup + title search across Crossref and OpenAlex."""

    def __init__(self, email: str = "", http: HttpJson | None = None):
        self.http = http or HttpJson(email=email)
        self.email = email
        self._cache: dict[str, RegistryRecord | None] = {}

    # -- DOI ------------------------------------------------------------
    def by_doi(self, doi: str) -> RegistryRecord | None:
        doi = (doi or "").strip()
        if not doi:
            return None
        if doi in self._cache:
            return self._cache[doi]
        record = None
        url = f"{CROSSREF_API}/works/{urllib.parse.quote(doi, safe='')}"
        if self.email:
            url += "?" + urllib.parse.urlencode({"mailto": self.email})
        data = self.http.get(url)
        if data and data.get("message"):
            record = normalize_crossref(data["message"])
        if record is None:
            url = f"{OPENALEX_API}/works/doi:{urllib.parse.quote(doi, safe='/')}"
            data = self.http.get(url)
            if data:
                record = normalize_openalex(data)
        self._cache[doi] = record
        return record

    # -- Title search ----------------------------------------------------
    def by_title(self, title: str, rows: int = 10) -> list[RegistryRecord]:
        title = (title or "").strip()
        if len(title) < 8:
            return []
        out: list[RegistryRecord] = []
        q = urllib.parse.urlencode({
            "query.title": title, "rows": rows,
            "select": "DOI,title,author,container-title,published-print,published-online,issued,volume,issue,page,publisher,type",
            **({"mailto": self.email} if self.email else {}),
        })
        data = self.http.get(f"{CROSSREF_API}/works?{q}")
        items = ((data or {}).get("message") or {}).get("items") or []
        for it in items:
            out.append(normalize_crossref(it))
        # Always merge OpenAlex candidates too: its ranking often surfaces
        # the canonical record that Crossref's relevance order buries
        # (e.g. the 1997 LSTM paper vs same-titled book chapters).
        q = urllib.parse.urlencode({"search": title, "per-page": rows,
                                    **({"mailto": self.email} if self.email else {})})
        data = self.http.get(f"{OPENALEX_API}/works?{q}")
        seen = {(r.doi or r.title).lower() for r in out}
        for w in (data or {}).get("results") or []:
            rec = normalize_openalex(w)
            key = (rec.doi or rec.title).lower()
            if key and key not in seen:
                out.append(rec)
                seen.add(key)
        return out
