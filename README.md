# bibvet

**Vet your bibliography before your reviewers do.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#installation)

`bibvet` checks your reference list against **Crossref** and **OpenAlex** and flags the mistakes that slip into manuscripts:

- ❌ **Dead / made-up DOIs** that resolve nowhere
- ❌ **Wrong years, volumes, pages** (e.g. `2016` instead of `2015`)
- ⚠️ **Titles and journals** that don't match the registry record
- ⚠️ **Duplicate entries** hiding under different cite keys
- ℹ️ **Missing DOIs** — bibvet finds the paper by title and suggests the DOI

It eats what researchers actually have: a **`.bib` file**, *or* a **plain-text reference list** pasted out of Word/PDF — including Chinese GB/T 7714 style lists (`[1] Author. Title[J]. Journal, Year, ...`).

Zero third-party dependencies: pure Python standard library.

中文说明见 [README.zh-CN.md](README.zh-CN.md).

## Installation

```bash
pip install bibvet        # once published to PyPI
# or, from a clone:
pip install .
```

Requires Python 3.9+. No API key needed.

## Quick start

```bash
bibvet check references.bib
bibvet check references.txt --report report.md --bib-out fixed.bib
bibvet check refs.bib --offline     # duplicates/format only, no network
bibvet check refs.bib --json report.json --email you@lab.edu
```

Exit code is `1` when any error is found, so it drops straight into CI or a pre-submission script.

### Example

Given [examples/example.bib](examples/example.bib) (which contains a wrong year, a wrong volume, a fake DOI, a duplicate, and one entry with no DOI):

```text
$ bibvet check examples/example.bib
bibvet: checked 4 references from example.bib
[lecun2015deep] ✅ ok  Deep learning
[lecun2015wrongyear] ❌ error  Deep learning
    ⚠️ year-mismatch: Year mismatch: yours 2016, registry 2015
    ⚠️ volume-mismatch: Volume mismatch: yours 522, registry 521
    ❌ duplicate: Duplicate of entry "lecun2015deep" (same DOI 10.1038/nature14539).
[fake2020] ❌ error  A study that was never published
    ❌ doi-not-found: DOI does not resolve in Crossref or OpenAlex: 10.1038/nature99999
[hochreiter1997lstm] ✅ ok  Long short-term memory
    ℹ️ doi-suggested: Suggested DOI: 10.1162/neco.1997.9.8.1735

summary: ✅ 2 ok · ⚠️ 0 warnings · ❌ 2 errors · ❔ 0 unverified
```

`--bib-out fixed.bib` writes a corrected bibliography: registry metadata replaces wrong years/volumes and fills in missing DOIs and publishers. Your cite keys are preserved.

Plain-text lists work too — see [examples/references.txt](examples/references.txt), a GB/T 7714 list where bibvet catches a planted wrong year (`1998` → `1997`) and a duplicated DOI pasted as a bare line.

Generated example outputs live in [demo/](demo/).

## How matching works (and when bibvet stays silent)

A title match alone is **not** trusted: different works share titles (a 2021 encyclopedia chapter is literally titled "Short-Term/Long-Term Memory"). Before suggesting a DOI, bibvet requires at least two corroborating fields among *year / first author / journal*, tolerating at most one disagreement — which is then reported as the error it probably is. When corroboration fails, the entry is reported as `❔ unverified` with the closest candidate shown, instead of a confident wrong answer.

Known limitation: some venues are poorly covered by registries (e.g. older NeurIPS proceedings). Such entries come back `unverified`, never silently "ok".

## Options

| Flag | Meaning |
|---|---|
| `--report PATH` | Markdown report, one section per reference |
| `--json PATH` | Machine-readable report |
| `--bib-out PATH` | Corrected `.bib` built from registry metadata |
| `--email ADDR` | Contact email for the Crossref polite pool (faster, optional) |
| `--offline` | No network: duplicates and format checks only |
| `--quiet` | Suppress terminal output |

## Roadmap

- [ ] Zotero library check via the Zotero API
- [ ] GB/T 7714 and APA formatting lint (punctuation, ordering)
- [ ] arXiv ID verification
- [ ] Web UI for drag-and-drop checking

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT © 2026 Song Qingye
