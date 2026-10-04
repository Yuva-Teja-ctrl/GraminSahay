"""Pure-logic tests for the eligibility engine and conflict detector.

No database, no LLM, no network — just the safety-critical decision logic. These mirror the
Java EligibilityEngineTest / ConflictDetectorTest and are the components you should be able
to explain in an interview.
"""

from app import eligibility
from app.domain import (
    CitizenProfile,
    EligibilityResult,
    EligibilityRule,
    EligibilityStatus,
    Operator,
    ProfileField,
    Scheme,
)


def rythu_bharosa() -> Scheme:
    return Scheme(
        id="ts-rythu-bharosa",
        name="Rythu Bharosa",
        category="agriculture",
        state="Telangana",
        description="Investment support for farmers who own cultivable land.",
        benefits="Rs 12,000 per acre per year.",
        required_documents=["Aadhaar", "Pattadar passbook"],
        application_steps=["Verify at AEO office"],
        official_url="https://rythubharosa.telangana.gov.in/",
        rules=[
            EligibilityRule(
                field=ProfileField.OCCUPATION,
                operator=Operator.EQUALS,
                value="farmer",
                human_text="Applicant must be a farmer",
            ),
            EligibilityRule(
                field=ProfileField.LAND_HOLDING_ACRES,
                operator=Operator.GREATER_THAN_OR_EQUAL,
                value="0.01",
                human_text="Applicant must own cultivable agricultural land",
            ),
        ],
        conflicts_with=[],
    )


def test_all_rules_pass_is_eligible():
    farmer = CitizenProfile(occupation="farmer", land_holding_acres=2.0, age=45, is_bpl=True)
    result = eligibility.evaluate(rythu_bharosa(), farmer)
    assert result.status == EligibilityStatus.ELIGIBLE
    assert len(result.passed_rules) == 2
    assert result.failed_rules == []


def test_a_rule_violated_is_not_eligible():
    shopkeeper = CitizenProfile(occupation="shopkeeper", land_holding_acres=0.0)
    result = eligibility.evaluate(rythu_bharosa(), shopkeeper)
    assert result.status == EligibilityStatus.NOT_ELIGIBLE


def test_all_fields_missing_is_missing_information():
    unknown = CitizenProfile()  # nothing provided
    result = eligibility.evaluate(rythu_bharosa(), unknown)
    assert result.status == EligibilityStatus.MISSING_INFORMATION
    assert len(result.missing_fields) == 2


def test_some_pass_but_field_missing_is_possibly_eligible():
    # Occupation is farmer (passes) but land unknown (missing) -> POSSIBLY_ELIGIBLE.
    partial = CitizenProfile(occupation="farmer", age=45)
    result = eligibility.evaluate(rythu_bharosa(), partial)
    assert result.status == EligibilityStatus.POSSIBLY_ELIGIBLE
    assert len(result.passed_rules) == 1
    assert len(result.missing_fields) == 1


def _bare_scheme(scheme_id: str, name: str, conflicts_with: list[str]) -> Scheme:
    return Scheme(
        id=scheme_id,
        name=name,
        category="agriculture",
        state="Telangana",
        description="desc",
        benefits="benefit",
        official_url="https://example.gov.in",
        conflicts_with=conflicts_with,
    )


def test_detects_conflict_between_two_eligible_schemes():
    a = _bare_scheme("ts-rythu-bharosa", "Rythu Bharosa", ["ts-indiramma-atmeeya-bharosa"])
    b = _bare_scheme("ts-indiramma-atmeeya-bharosa", "Indiramma Atmeeya Bharosa", ["ts-rythu-bharosa"])
    results = [
        EligibilityResult(scheme=a, status=EligibilityStatus.ELIGIBLE),
        EligibilityResult(scheme=b, status=EligibilityStatus.ELIGIBLE),
    ]
    conflicts = eligibility.detect_conflicts(results)
    assert len(conflicts) == 1


def test_no_conflict_when_one_scheme_not_eligible():
    a = _bare_scheme("ts-rythu-bharosa", "Rythu Bharosa", ["ts-indiramma-atmeeya-bharosa"])
    b = _bare_scheme("ts-indiramma-atmeeya-bharosa", "Indiramma Atmeeya Bharosa", ["ts-rythu-bharosa"])
    results = [
        EligibilityResult(scheme=a, status=EligibilityStatus.ELIGIBLE),
        EligibilityResult(scheme=b, status=EligibilityStatus.NOT_ELIGIBLE, failed_rules=["some rule"]),
    ]
    conflicts = eligibility.detect_conflicts(results)
    assert conflicts == []
