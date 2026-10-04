package in.graminsahay.domain;

/**
 * Four-way eligibility classification from the project abstract.
 *
 * <p>The distinction between {@link #NOT_ELIGIBLE} and {@link #MISSING_INFORMATION} is the
 * safety-critical part: when the citizen has not provided a field a rule needs, we must say
 * "I need more detail" rather than silently assuming and producing a wrong decision.
 */
public enum EligibilityStatus {
    /** All known rules pass and no required field is missing. */
    ELIGIBLE,

    /** No rule fails outright, but at least one required field is unknown. */
    POSSIBLY_ELIGIBLE,

    /** At least one rule is violated by the citizen's profile. */
    NOT_ELIGIBLE,

    /** The scheme's gating rule depends on a field the citizen did not supply. */
    MISSING_INFORMATION
}
