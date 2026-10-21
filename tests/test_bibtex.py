import unittest

from bibvet.bibtex import entry_to_bibtex, normalize_doi, parse_bibtex

SAMPLE = r"""
% a comment
@string{nat = {Nature}}

@article{lecun2015,
  author  = {LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey},
  title   = {Deep {Learning} with {Nested} Braces},
  journal = nat,
  year    = 2015,
  volume  = "521",
  pages   = {436--444},
  doi     = {https://doi.org/10.1038/nature14539}
}

@book{knuth1984,
  author    = {Knuth, Donald E.},
  title     = {The TeXbook},
  publisher = {Addison-Wesley},
  year      = {1984}
}

@comment{this should be ignored}
"""


class TestParseBibtex(unittest.TestCase):
    def test_parses_entries(self):
        entries = parse_bibtex(SAMPLE)
        self.assertEqual(len(entries), 2)
        e = entries[0]
        self.assertEqual(e.key, "lecun2015")
        self.assertEqual(e.entry_type, "article")
        self.assertEqual(e.year, "2015")
        self.assertEqual(e.get("volume"), "521")
        self.assertEqual(e.journal, "Nature")  # @string expanded
        self.assertIn("Nested", e.title)  # nested braces survived
        self.assertEqual(e.author_families, ["LeCun", "Bengio", "Hinton"])

    def test_doi_normalized(self):
        entries = parse_bibtex(SAMPLE)
        self.assertEqual(entries[0].doi, "10.1038/nature14539")
        self.assertEqual(normalize_doi("doi: 10.1000/xyz.1"), "10.1000/xyz.1")
        self.assertEqual(normalize_doi("http://dx.doi.org/10.1000/xyz.1"), "10.1000/xyz.1")

    def test_fix_with_record(self):
        from bibvet.model import RegistryRecord

        entries = parse_bibtex(SAMPLE)
        rec = RegistryRecord(doi="10.1038/nature14539", title="Deep learning",
                             year=2015, container="Nature", volume="521",
                             pages="436-444", source="crossref",
                             authors_full=["Yann LeCun"])
        out = entry_to_bibtex(entries[0], record=rec, fix=True)
        self.assertIn("Deep learning", out)
        self.assertIn("436--444", out)


if __name__ == "__main__":
    unittest.main()
