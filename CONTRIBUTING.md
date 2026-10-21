# Contributing to bibvet

Thanks for considering a contribution!

## Development setup

```bash
git clone https://github.com/songqingye/bibvet.git
cd bibvet
pip install -e .
python -m unittest discover -s tests -v
```

bibvet intentionally has **zero runtime dependencies** (standard library
only) — please keep it that way. Tests must pass offline; registry
behavior is tested through fake resolvers (see `tests/test_check.py`).

## Good first issues

- Parsers for more plain-text styles (Vancouver, MLA, university thesis
  templates)
- More registry fields in comparisons (issue numbers, edition, ISBN)
- Localisation of report output

## Pull requests

1. Add or update tests for your change.
2. Run the full test suite and the offline smoke test:
   `bibvet check examples/example.bib --offline`
3. Keep the tone of messages user-facing: an issue message should tell
   the user what is wrong and what the registry says, in one glance.

## Reporting bugs

Please include the exact input entry that misbehaves (redact anything
private), the bibvet version, and what you expected to happen.
