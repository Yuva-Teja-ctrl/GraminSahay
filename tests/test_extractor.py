"""Tests for the profile extractor's pure logic (the merge step — no LLM needed).

We don't test the LLM call itself (that needs network/key); we test the safety-critical
MERGE rule: explicit form values from the citizen must always win over LLM-extracted ones.
"""

from app.domain import CitizenProfile
from app.extractor import ProfileExtractor


def test_explicit_values_win_over_extracted():
    extracted = CitizenProfile(occupation="farmer", district="Warangal", land_holding_acres=5.0)
    provided = CitizenProfile(land_holding_acres=2.0)  # citizen explicitly corrected the land

    merged = ProfileExtractor.merge(extracted, provided)

    assert merged.land_holding_acres == 2.0  # explicit value wins
    assert merged.occupation == "farmer"  # falls back to extracted where form was blank
    assert merged.district == "Warangal"


def test_extracted_fills_blanks():
    extracted = CitizenProfile(occupation="student", category="sc", age=19)
    provided = CitizenProfile()  # citizen filled nothing in the form

    merged = ProfileExtractor.merge(extracted, provided)

    assert merged.occupation == "student"
    assert merged.category == "sc"
    assert merged.age == 19


def test_both_empty_stays_empty():
    merged = ProfileExtractor.merge(CitizenProfile(), CitizenProfile())
    assert merged.occupation is None
    assert merged.land_holding_acres is None
    assert merged.age is None
