package in.graminsahay.domain;

/**
 * A single, machine-checkable eligibility condition for a scheme.
 *
 * <p>Rules are deliberately simple and declarative so they can be authored in the scheme
 * knowledge base (JSON) by non-programmers and evaluated deterministically. The
 * {@link EligibilityEngine} interprets them; the LLM never decides a rule's outcome.
 *
 * @param field    which {@link CitizenProfile} field this rule inspects
 * @param operator comparison to apply
 * @param value    the threshold / expected value (as a string; parsed per field type)
 * @param humanText plain-language description used in explanations, e.g.
 *                  "Applicant must own 5 acres of land or less"
 */
public record EligibilityRule(
        ProfileField field,
        Operator operator,
        String value,
        String humanText
) {

    /** Profile attributes a rule can reference. */
    public enum ProfileField {
        OCCUPATION,
        ANNUAL_INCOME,
        LAND_HOLDING_ACRES,
        AGE,
        GENDER,
        DISTRICT,
        IS_BPL,
        CATEGORY
    }

    /** Supported comparisons. Numeric ops apply to income/land/age; EQUALS/IN apply to text/boolean. */
    public enum Operator {
        EQUALS,
        NOT_EQUALS,
        IN,            // comma-separated list membership, e.g. "sc,st"
        LESS_THAN_OR_EQUAL,
        GREATER_THAN_OR_EQUAL,
        IS_TRUE
    }
}
