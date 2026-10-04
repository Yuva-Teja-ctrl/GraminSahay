"""Deterministic eligibility evaluation + scheme conflict detection.

This is the reliability core of GraminSahay, ported directly from the Java version.

WHY DETERMINISTIC? Eligibility for a welfare scheme is a safety-critical decision: telling a
poor citizen "you are eligible" when they are not wastes a trip to the office and erodes
trust, while a false "not eligible" denies them a benefit they deserve. LLMs hallucinate;
rules do not. So the LLM retrieves and explains, but the yes/no/maybe verdict comes from the
transparent, auditable rules evaluated here.
"""

from app.domain import (
    CitizenProfile,
    Conflict,
    EligibilityResult,
    EligibilityRule,
    EligibilityStatus,
    Operator,
    ProfileField,
    Scheme,
)


def _extract(field: ProfileField, profile: CitizenProfile):
    """Read the profile attribute a rule refers to (returns None if unknown)."""
    mapping = {
        ProfileField.OCCUPATION: profile.occupation,
        ProfileField.ANNUAL_INCOME: profile.annual_income,
        ProfileField.LAND_HOLDING_ACRES: profile.land_holding_acres,
        ProfileField.AGE: profile.age,
        ProfileField.GENDER: profile.gender,
        ProfileField.DISTRICT: profile.district,
        ProfileField.IS_BPL: profile.is_bpl,
        ProfileField.CATEGORY: profile.category,
    }
    return mapping[field]


def _in_list(actual: str, csv: str) -> bool:
    return any(option.strip().lower() == str(actual).strip().lower() for option in csv.split(","))


def _rule_outcome(rule: EligibilityRule, profile: CitizenProfile) -> str:
    """Evaluate one rule. Returns 'PASS', 'FAIL', or 'UNKNOWN'.

    'UNKNOWN' means the citizen did not provide the field this rule needs — the trigger for
    MISSING_INFORMATION rather than a wrong guess.
    """
    actual = _extract(rule.field, profile)
    if actual is None:
        return "UNKNOWN"

    op = rule.operator
    if op == Operator.EQUALS:
        passes = str(actual).strip().lower() == rule.value.strip().lower()
    elif op == Operator.NOT_EQUALS:
        passes = str(actual).strip().lower() != rule.value.strip().lower()
    elif op == Operator.IN:
        passes = _in_list(str(actual), rule.value)
    elif op == Operator.IS_TRUE:
        passes = actual is True
    elif op == Operator.LESS_THAN_OR_EQUAL:
        passes = float(actual) <= float(rule.value)
    elif op == Operator.GREATER_THAN_OR_EQUAL:
        passes = float(actual) >= float(rule.value)
    else:  # pragma: no cover - all operators handled above
        passes = False

    return "PASS" if passes else "FAIL"


def _classify(passed: list[str], failed: list[str], missing: list[str]) -> EligibilityStatus:
    """Combine per-rule outcomes into the four-way status (same logic as the Java engine)."""
    if failed:
        return EligibilityStatus.NOT_ELIGIBLE
    if missing:
        # Nothing failed. With no positive evidence yet we genuinely need more info;
        # otherwise the citizen is plausibly eligible pending the missing detail.
        return (
            EligibilityStatus.MISSING_INFORMATION
            if not passed
            else EligibilityStatus.POSSIBLY_ELIGIBLE
        )
    return EligibilityStatus.ELIGIBLE


def evaluate(scheme: Scheme, profile: CitizenProfile) -> EligibilityResult:
    """Evaluate a single scheme against a citizen profile."""
    passed: list[str] = []
    failed: list[str] = []
    missing: list[str] = []

    for rule in scheme.rules:
        outcome = _rule_outcome(rule, profile)
        if outcome == "PASS":
            passed.append(rule.human_text)
        elif outcome == "FAIL":
            failed.append(rule.human_text)
        else:  # UNKNOWN
            field_name = rule.field.value.lower().replace("_", " ")
            missing.append(f"We need to know your {field_name} to confirm: {rule.human_text}")

    status = _classify(passed, failed, missing)
    return EligibilityResult(
        scheme=scheme,
        status=status,
        passed_rules=passed,
        failed_rules=failed,
        missing_fields=missing,
    )


def detect_conflicts(results: list[EligibilityResult]) -> list[Conflict]:
    """Scheme conflict detection — the project's distinctive feature.

    Some welfare schemes are mutually exclusive by policy. We model this as an undirected
    conflict graph: each scheme declares the ids it ``conflicts_with``, and we report any
    conflicting pair among the schemes the citizen is (possibly) eligible for. Not-eligible
    schemes are ignored — you cannot clash over a benefit you cannot claim.
    """
    candidates = [
        r.scheme
        for r in results
        if r.status in (EligibilityStatus.ELIGIBLE, EligibilityStatus.POSSIBLY_ELIGIBLE)
    ]
    candidate_ids = {s.id for s in candidates}
    by_id = {s.id: s for s in candidates}

    conflicts: list[Conflict] = []
    seen_pairs: set[tuple[str, str]] = set()

    for scheme in candidates:
        for other_id in scheme.conflicts_with:
            if other_id not in candidate_ids:
                continue  # the other scheme isn't a candidate, so no live conflict
            pair_key = tuple(sorted((scheme.id, other_id)))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            other = by_id[other_id]
            conflicts.append(
                Conflict(
                    scheme_a=scheme.name,
                    scheme_b=other.name,
                    message=(
                        f'You appear eligible for both "{scheme.name}" and "{other.name}", '
                        f"but these cannot be claimed together. Please choose one."
                    ),
                )
            )
    return conflicts
