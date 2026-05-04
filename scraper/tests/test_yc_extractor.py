"""
Tests for extractors/yc.py pure functions.
Covers every bug that was found and fixed in the scraper:

  1. founded_year: Unix timestamp → real year  (was taking first 4 digits: 1640→2021)
  2. founded_year: plain int year passthrough
  3. founded_year: ISO date string fallback
  4. founded_year: batch fallback when no field present
  5. founded_year: out-of-range int falls back to batch year
  6. founded_year: junk string falls back to batch year
  7. _headcount: boundary at exactly 10 (was <, now <=)
  8. _headcount: each bucket boundary
  9. _headcount: 100+ bucket
  10. _headcount: None / zero input
  11. _parse_founders: full_name preferred over first+last
  12. _parse_founders: first+last fallback when full_name absent
  13. _parse_founders: rows with no name are skipped
  14. _parse_founders: linkedin_url key variant
  15. _parse_founders: linkedinUrl camelCase key variant
  16. _parse_founders: empty / None input
  17. _sector: known keywords map correctly
  18. _sector: unknown industry returns "Other"
  19. _sector: empty list returns None
  20. _sector: case-insensitive matching
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors.yc import _headcount, _parse_founders, _sector, parse_founded_year


class TestParseFountedYear(unittest.TestCase):

    def test_unix_timestamp_int(self):
        # 1640000000 = 2021-12-20 — was returning 1640 before fix
        self.assertEqual(parse_founded_year(1640000000), 2021)

    def test_unix_timestamp_string(self):
        self.assertEqual(parse_founded_year("1704067200"), 2024)

    def test_plain_int_year(self):
        self.assertEqual(parse_founded_year(2022), 2022)

    def test_plain_int_year_string(self):
        self.assertEqual(parse_founded_year("2019"), 2019)

    def test_iso_date_string(self):
        self.assertEqual(parse_founded_year("2023-04-01"), 2023)

    def test_none_returns_batch_fallback(self):
        self.assertEqual(parse_founded_year(None, batch_fallback=2023), 2023)

    def test_none_no_fallback_returns_none(self):
        self.assertIsNone(parse_founded_year(None))

    def test_out_of_range_int_uses_fallback(self):
        # 1700 is not a unix timestamp and not in 1980-2030
        self.assertEqual(parse_founded_year(1700, batch_fallback=2022), 2022)

    def test_junk_string_uses_fallback(self):
        self.assertEqual(parse_founded_year("not-a-year", batch_fallback=2021), 2021)


class TestHeadcount(unittest.TestCase):

    def test_none(self):
        self.assertIsNone(_headcount(None))

    def test_zero(self):
        self.assertIsNone(_headcount(0))

    def test_exactly_1(self):
        self.assertEqual(_headcount(1), "1-10")

    def test_exactly_10(self):
        # Was broken (< instead of <=): team of exactly 10 returned None
        self.assertEqual(_headcount(10), "1-10")

    def test_11(self):
        self.assertEqual(_headcount(11), "11-25")

    def test_exactly_25(self):
        self.assertEqual(_headcount(25), "11-25")

    def test_26(self):
        self.assertEqual(_headcount(26), "26-50")

    def test_exactly_50(self):
        self.assertEqual(_headcount(50), "26-50")

    def test_51(self):
        self.assertEqual(_headcount(51), "51-100")

    def test_exactly_100(self):
        self.assertEqual(_headcount(100), "51-100")

    def test_101(self):
        self.assertEqual(_headcount(101), "100+")

    def test_large(self):
        self.assertEqual(_headcount(5000), "100+")


class TestParseFounders(unittest.TestCase):

    def test_full_name_preferred_over_first_last(self):
        raw = [{"full_name": "Alice Smith", "first_name": "Alice", "last_name": "Jones"}]
        founders = _parse_founders(raw)
        self.assertEqual(len(founders), 1)
        self.assertEqual(founders[0].name, "Alice Smith")

    def test_fallback_to_first_last(self):
        raw = [{"first_name": "Bob", "last_name": "Chen"}]
        founders = _parse_founders(raw)
        self.assertEqual(len(founders), 1)
        self.assertEqual(founders[0].name, "Bob Chen")

    def test_skips_empty_name(self):
        raw = [{"full_name": ""}, {"first_name": "", "last_name": ""}]
        self.assertEqual(_parse_founders(raw), [])

    def test_linkedin_url_key(self):
        raw = [{"full_name": "Carol", "linkedin_url": "https://linkedin.com/in/carol"}]
        self.assertEqual(_parse_founders(raw)[0].linkedin_url, "https://linkedin.com/in/carol")

    def test_linkedin_camelcase_key(self):
        raw = [{"full_name": "Dave", "linkedinUrl": "https://linkedin.com/in/dave"}]
        self.assertEqual(_parse_founders(raw)[0].linkedin_url, "https://linkedin.com/in/dave")

    def test_empty_list(self):
        self.assertEqual(_parse_founders([]), [])

    def test_none_input(self):
        self.assertEqual(_parse_founders(None), [])

    def test_multiple_founders(self):
        raw = [{"full_name": "Eve"}, {"full_name": "Frank"}]
        names = [f.name for f in _parse_founders(raw)]
        self.assertEqual(names, ["Eve", "Frank"])


class TestSector(unittest.TestCase):

    def test_ai(self):
        self.assertEqual(_sector(["Artificial Intelligence"]), "AI")

    def test_fintech(self):
        self.assertEqual(_sector(["fintech"]), "Fintech")

    def test_first_match_wins(self):
        self.assertEqual(_sector(["fintech", "B2B"]), "Fintech")

    def test_unknown_returns_other(self):
        self.assertEqual(_sector(["Quantum Computing"]), "Other")

    def test_empty_returns_none(self):
        self.assertIsNone(_sector([]))

    def test_case_insensitive(self):
        self.assertEqual(_sector(["Machine Learning"]), "AI")

    def test_b2b_maps_to_enterprise(self):
        self.assertEqual(_sector(["B2B SaaS"]), "Enterprise")


if __name__ == "__main__":
    unittest.main(verbosity=2)
