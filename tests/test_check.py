import unittest

from bibvet.check import check_duplicates, check_entry, title_similarity
from bibvet.model import Entry, RegistryRecord

LECUN = RegistryRecord(
    doi="10.1038/nature14539", title="Deep learning",
    author_families=["LeCun", "Bengio", "Hinton"],
    authors_full=["Yann LeCun", "Yoshua Bengio", "Geoffrey Hinton"],
    year=2015, container="Nature", volume="521", issue="7553",
    pages="436-444", publisher="Nature Portfolio", source="crossref",
)


class FakeResolver:
    def __init__(self):
        self.by_doi_map = {"10.1038/nature14539": LECUN}
        self.by_title_map = {"long short-term memory": RegistryRecord(
            doi="10.1162/neco.1997.9.8.1735", title="Long Short-Term Memory",
            author_families=["Hochreiter", "Schmidhuber"], year=1997,
            container="Neural Computation", volume="9", issue="8",
            pages="1735-1780", source="crossref")}

    def by_doi(self, doi):
        return self.by_doi_map.get(doi)

    def by_title(self, title):
        rec = self.by_title_map.get(title.strip().lower())
        return [rec] if rec else []


def make_entry(**fields):
    base = {
        "author": "LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey",
        "title": "Deep learning", "journal": "Nature", "year": "2015",
        "volume": "521", "pages": "436--444", "doi": "10.1038/nature14539",
    }
    base.update(fields)
    return Entry(key="x", entry_type="article", fields=base)


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.resolver = FakeResolver()

    def test_clean_entry_ok(self):
        r = check_entry(make_entry(), self.resolver)
        self.assertEqual(r.status, "ok", r.issues)

    def test_wrong_year_flagged(self):
        r = check_entry(make_entry(year="2019"), self.resolver)
        codes = [i.code for i in r.issues]
        self.assertIn("year-mismatch", codes)
        self.assertEqual(r.status, "error")  # >1 year off is an error

    def test_fake_doi(self):
        r = check_entry(make_entry(doi="10.1038/nature99999"), self.resolver)
        self.assertEqual(r.status, "error")
        self.assertEqual(r.issues[0].code, "doi-not-found")

    def test_missing_doi_suggests(self):
        e = Entry(key="lstm", entry_type="article", fields={
            "author": "Hochreiter, Sepp and Schmidhuber, Jurgen",
            "title": "Long short-term memory", "journal": "Neural Computation",
            "year": "1997"})
        r = check_entry(e, self.resolver)
        codes = [i.code for i in r.issues]
        self.assertIn("doi-suggested", codes)
        self.assertIsNotNone(r.record)

    def test_title_match_needs_corroboration(self):
        # A same-titled but different work (e.g. a book chapter) must not
        # be auto-suggested: year and first author disagree.
        class TrapResolver(FakeResolver):
            def by_title(self, title):
                return [RegistryRecord(
                    doi="10.1007/xyz", title="Long Short-Term Memory",
                    author_families=["Knudson"], year=2021,
                    container="Encyclopedia of Gerontology", source="crossref")]

        e = Entry(key="lstm", entry_type="article", fields={
            "author": "Hochreiter, Sepp and Schmidhuber, Jurgen",
            "title": "Long short-term memory", "journal": "Neural Computation",
            "year": "1997"})
        r = check_entry(e, TrapResolver())
        self.assertIsNone(r.record)
        self.assertIn("possible-match", [i.code for i in r.issues])

    def test_duplicates(self):
        r1 = check_entry(make_entry(), self.resolver)
        e2 = make_entry()
        e2.key = "y"
        r2 = check_entry(e2, self.resolver)
        check_duplicates([r1, r2])
        self.assertIn("duplicate", [i.code for i in r2.issues])

    def test_title_similarity(self):
        self.assertGreater(title_similarity("Deep learning", "Deep learning"), 0.99)
        self.assertLess(title_similarity("Deep learning", "Quantum chromodynamics"), 0.5)


if __name__ == "__main__":
    unittest.main()
