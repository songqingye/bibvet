"""Markdown + JSON reporting."""

from __future__ import annotations

import json

from .model import EntryResult

_STATUS_ICON = {"ok": "✅ ok", "warning": "⚠️ warning", "error": "❌ error", "unverified": "❔ unverified"}
_LEVEL_ICON = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}


def summarize(results: list[EntryResult]) -> dict:
    counts = {"ok": 0, "warning": 0, "error": 0, "unverified": 0}
    for r in results:
        counts[r.status] += 1
    return {"total": len(results), **counts}


def render_markdown(results: list[EntryResult], source_name: str) -> str:
    s = summarize(results)
    lines = [
        "# bibvet report",
        "",
        f"Source: `{source_name}` — {s['total']} references: "
        f"✅ {s['ok']} ok · ⚠️ {s['warning']} warnings · ❌ {s['error']} errors · ❔ {s['unverified']} unverified",
        "",
    ]
    for r in results:
        title = r.entry.title or (r.record.title if r.record else "") or "(no title)"
        lines.append(f"## [{r.entry.key}] {_STATUS_ICON[r.status]} — {title}")
        lines.append("")
        if r.entry.doi:
            lines.append(f"- DOI (yours): `{r.entry.doi}`")
        if r.record:
            lines.append(f"- Registry ({r.record.source}): `{r.record.doi}`"
                         + (f", {r.record.container}" if r.record.container else "")
                         + (f", {r.record.year}" if r.record.year else ""))
        if not r.issues:
            lines.append("- No issues found.")
        for issue in r.issues:
            lines.append(f"- {_LEVEL_ICON[issue.level]} **{issue.code}**: {issue.message}")
        lines.append("")
    return "\n".join(lines)


def render_json(results: list[EntryResult], source_name: str) -> str:
    data = {
        "source": source_name,
        "summary": summarize(results),
        "entries": [
            {
                "key": r.entry.key,
                "status": r.status,
                "doi": r.entry.doi or (r.record.doi if r.record else ""),
                "title": r.entry.title or (r.record.title if r.record else ""),
                "registry_source": r.record.source if r.record else None,
                "issues": [
                    {"level": i.level, "code": i.code, "message": i.message}
                    for i in r.issues
                ],
            }
            for r in results
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def render_terminal(results: list[EntryResult], source_name: str) -> str:
    s = summarize(results)
    lines = [f"bibvet: checked {s['total']} references from {source_name}"]
    for r in results:
        head = f"[{r.entry.key}] {_STATUS_ICON[r.status]}"
        title = r.entry.title or (r.record.title if r.record else "")
        lines.append(f"{head}  {title[:90]}")
        for issue in r.issues:
            lines.append(f"    {_LEVEL_ICON[issue.level]} {issue.code}: {issue.message}")
    lines.append(
        f"\nsummary: ✅ {s['ok']} ok · ⚠️ {s['warning']} warnings · "
        f"❌ {s['error']} errors · ❔ {s['unverified']} unverified"
    )
    return "\n".join(lines)
