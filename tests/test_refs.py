import unittest

from bibvet.refs import extract_doi, parse_text_references

GBT = (
    "[1] LeCun Y, Bengio Y, Hinton G. Deep learning[J]. Nature, 2015, "
    "521(7553): 436-444. DOI: 10.1038/nature14539.\n"
    "[2] Hochreiter S, Schmidhuber J. Long short-term memory[J]. "
    "Neural Computation, 1997, 9(8): 1735-1780.\n"
)


class TestRefs(unittest.TestCase):
    def test_extract_doi(self):
        self.assertEqual(extract_doi("see https://doi.org/10.1000/xyz123."), "10.1000/xyz123")
        self.assertEqual(extract_doi("no doi here"), "")

    def test_gbt_parse(self):
        entries = parse_text_references(GBT)
        self.assertEqual(len(entries), 2)
        e = entries[0]
        self.assertEqual(e.doi, "10.1038/nature14539")
        self.assertEqual(e.title, "Deep learning")
        self.assertEqual(e.journal, "Nature")
        self.assertEqual(e.year, "2015")
        self.assertEqual(e.get("volume"), "521")
        self.assertEqual(e.get("pages"), "436-444")
        e2 = entries[1]
        self.assertEqual(e2.title, "Long short-term memory")
        self.assertEqual(e2.year, "1997")

    def test_doi_only_line(self):
        entries = parse_text_references("10.1038/nature14539\n")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].doi, "10.1038/nature14539")

    def test_trailing_doi_line_is_its_own_entry(self):
        text = GBT + "10.1038/nature14539\n"
        entries = parse_text_references(text)
        self.assertEqual(len(entries), 3)
        # the LSTM entry must not absorb the trailing DOI line
        self.assertEqual(entries[1].doi, "")
        self.assertEqual(entries[2].doi, "10.1038/nature14539")

    def test_gbt_author_families(self):
        entries = parse_text_references(GBT)
        self.assertEqual(entries[0].author_families, ["LeCun", "Bengio", "Hinton"])


if __name__ == "__main__":
    unittest.main()
