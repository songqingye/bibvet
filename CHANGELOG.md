# Changelog

## 0.1.0 — 2026-10-21

First release.

- `bibvet check` for `.bib` files (dependency-free BibTeX parser with
  @string expansion and nested-brace support) and plain-text reference
  lists (numbered, GB/T 7714, APA-ish, DOI-per-line).
- Verification against Crossref with OpenAlex fallback for DOI lookups;
  title search merges candidates from both registries.
- Checks: DOI resolution, title / year / journal / volume / pages /
  first-author comparison, duplicate DOI/title detection, missing-DOI
  suggestion with multi-field corroboration (title match alone is
  never trusted).
- Outputs: terminal summary, Markdown report, JSON report, and a
  corrected `.bib` generated from registry metadata.
- `--offline` mode for duplicate/format checks; exit code 1 on errors
  for CI use.
