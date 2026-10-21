"""Core data model for bibvet."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Entry:
    """One reference as parsed from the user's file."""

    key: str
    entry_type: str = "article"
    fields: dict = field(default_factory=dict)
    raw: str = ""

    def get(self, name: str, default: str = "") -> str:
        return (self.fields.get(name) or default).strip()

    @property
    def doi(self) -> str:
        return self.get("doi")

    @property
    def title(self) -> str:
        return self.get("title")

    @property
    def year(self) -> str:
        return self.get("year")

    @property
    def journal(self) -> str:
        return self.get("journal") or self.get("booktitle")

    @property
    def author_families(self) -> list:
        """Family names parsed from a BibTeX ``author`` field."""
        raw = self.get("author")
        if not raw:
            return []
        families = []
        for part in raw.split(" and "):
            part = part.strip().strip("{}")
            if not part:
                continue
            if "," in part:  # "Family, Given"
                families.append(part.split(",")[0].strip())
            else:
                tokens = part.split()
                # "Family Y" / "Family Y B" (GB/T style initials last)
                if len(tokens) >= 2 and all(
                    len(t) <= 2 and t.isupper() for t in tokens[1:]
                ):
                    families.append(tokens[0])
                else:  # "Given ... Family"
                    families.append(tokens[-1].strip())
        return families


@dataclass
class RegistryRecord:
    """Bibliographic record normalized from Crossref or OpenAlex."""

    doi: str = ""
    title: str = ""
    author_families: list = field(default_factory=list)
    authors_full: list = field(default_factory=list)
    year: int | None = None
    container: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    publisher: str = ""
    type: str = ""
    source: str = ""  # "crossref" or "openalex"


@dataclass
class Issue:
    level: str  # "error" | "warning" | "info"
    code: str
    message: str


@dataclass
class EntryResult:
    entry: Entry
    record: RegistryRecord | None = None
    issues: list = field(default_factory=list)

    @property
    def status(self) -> str:
        if any(i.level == "error" for i in self.issues):
            return "error"
        if self.record is None and (not self.entry.doi
                                    or any(i.code == "offline" for i in self.issues)):
            return "unverified"
        if any(i.level == "warning" for i in self.issues):
            return "warning"
        return "ok"

    def add(self, level: str, code: str, message: str) -> None:
        self.issues.append(Issue(level, code, message))
