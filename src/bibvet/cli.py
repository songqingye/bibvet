"""bibvet command line interface.

Usage:
    bibvet check references.bib
    bibvet check references.txt --report report.md --bib-out fixed.bib
    bibvet check refs.bib --offline          # internal checks only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .bibtex import entry_to_bibtex, parse_bibtex
from .check import check_duplicates, check_entry
from .refs import looks_like_bibtex, parse_text_references
from .registry import Resolver
from .report import render_json, render_markdown, render_terminal


def load_entries(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".bib" or looks_like_bibtex(text):
        return parse_bibtex(text)
    return parse_text_references(text)


def cmd_check(args) -> int:
    path = Path(args.input)
    if not path.exists():
        print(f"bibvet: no such file: {path}", file=sys.stderr)
        return 2
    entries = load_entries(path)
    if not entries:
        print(f"bibvet: no references parsed from {path}", file=sys.stderr)
        return 2

    resolver = None if args.offline else Resolver(email=args.email or "")
    results = [check_entry(e, resolver, offline=args.offline) for e in entries]
    check_duplicates(results)

    if not args.quiet:
        print(render_terminal(results, path.name))

    def _write(path_str: str, content: str, label: str) -> None:
        p = Path(path_str)
        if p.parent and str(p.parent):
            p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        print(f"{label} written to {p}")

    if args.report:
        _write(args.report, render_markdown(results, path.name), "report")
    if args.json:
        _write(args.json, render_json(results, path.name), "json")
    if args.bib_out:
        chunks = [entry_to_bibtex(r.entry, record=r.record, fix=True) for r in results]
        _write(args.bib_out, "\n\n".join(chunks) + "\n", "corrected bib")

    has_error = any(r.status == "error" for r in results)
    return 1 if has_error else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="bibvet",
        description="Vet your bibliography: verify DOIs and BibTeX entries "
                    "against Crossref and OpenAlex.",
    )
    parser.add_argument("--version", action="version", version=f"bibvet {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("check", help="check a .bib file or a plain-text reference list")
    p.add_argument("input", help="input file (.bib, .txt, .md)")
    p.add_argument("--report", metavar="PATH", help="write a Markdown report")
    p.add_argument("--json", metavar="PATH", help="write a JSON report")
    p.add_argument("--bib-out", metavar="PATH",
                   help="write a corrected .bib (registry metadata fills/fixes fields)")
    p.add_argument("--email", metavar="ADDR",
                   help="contact email for the Crossref polite pool (optional)")
    p.add_argument("--offline", action="store_true",
                   help="skip registry lookups; duplicates/format checks only")
    p.add_argument("--quiet", action="store_true", help="suppress terminal output")
    p.set_defaults(func=cmd_check)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
