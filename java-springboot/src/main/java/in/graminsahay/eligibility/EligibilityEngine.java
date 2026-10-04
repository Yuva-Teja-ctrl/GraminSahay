package in.graminsahay.eligibility;

import in.graminsahay.domain.CitizenProfile;
import in.graminsahay.domain.EligibilityResult;
import in.graminsahay.domain.EligibilityRule;
import in.graminsahay.domain.EligibilityStatus;
import in.graminsahay.domain.Scheme;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * Deterministic eligibility evaluator — the reliability core of GraminSahay.
 *
 * <p><strong>Why deterministic?</strong> Eligibility for a welfare scheme is a safety-critical
 * decision: telling a poor citizen "you are eligible" when they are not wastes a trip to the
 * office and erodes trust, while a false "not eligible" denies them a benefit they deserve.
 * LLMs hallucinate; rules do not. So we let the LLM retrieve and explain, but the yes/no/maybe
 * verdict comes from transparent, auditable rules evaluated here.
 *
 * <p>Classification logic:
 * <ul>
 *   <li>Any rule evaluates to a hard fail  -> {@code NOT_ELIGIBLE}</li>
 *   <li>No fail, but a rule needs a field the citizen omitted -> {@code MISSING_INFORMATION}
 *       (if nothing passed yet) or {@code POSSIBLY_ELIGIBLE} (if some rules already passed)</li>
 *   <li>All rules pass with no missing fields -> {@code ELIGIBLE}</li>
 * </ul>
 */
@Component
public class EligibilityEngine {

    /** Evaluate a single scheme against a citizen profile. */
    public EligibilityResult evaluate(Scheme scheme, CitizenProfile profile) {
        List<String> passed = new ArrayList<>();
        List<String> failed = new ArrayList<>();
        List<String> missing = new ArrayList<>();

        for (EligibilityRule rule : scheme.rules()) {
            RuleOutcome outcome = evaluateRule(rule, profile);
            switch (outcome) {
                case PASS -> passed.add(rule.humanText());
                case FAIL -> failed.add(rule.humanText());
                case UNKNOWN -> missing.add(describeMissingField(rule));
            }
        }

        EligibilityStatus status = classify(passed, failed, missing);
        return new EligibilityResult(scheme, status, passed, failed, missing);
    }

    private EligibilityStatus classify(List<String> passed, List<String> failed, List<String> missing) {
        if (!failed.isEmpty()) {
            return EligibilityStatus.NOT_ELIGIBLE;
        }
        if (!missing.isEmpty()) {
            // Nothing has failed. If we have no positive evidence yet, we genuinely need more
            // info; otherwise the citizen is plausibly eligible pending the missing detail.
            return passed.isEmpty()
                    ? EligibilityStatus.MISSING_INFORMATION
                    : EligibilityStatus.POSSIBLY_ELIGIBLE;
        }
        return EligibilityStatus.ELIGIBLE;
    }

    private enum RuleOutcome { PASS, FAIL, UNKNOWN }

    private RuleOutcome evaluateRule(EligibilityRule rule, CitizenProfile profile) {
        Object actual = extract(rule.field(), profile);
        if (actual == null) {
            return RuleOutcome.UNKNOWN; // citizen did not provide this field
        }
        boolean passes = switch (rule.operator()) {
            case EQUALS -> stringOf(actual).equalsIgnoreCase(rule.value().trim());
            case NOT_EQUALS -> !stringOf(actual).equalsIgnoreCase(rule.value().trim());
            case IN -> inList(stringOf(actual), rule.value());
            case IS_TRUE -> Boolean.TRUE.equals(actual);
            case LESS_THAN_OR_EQUAL -> toNumber(actual) <= Double.parseDouble(rule.value().trim());
            case GREATER_THAN_OR_EQUAL -> toNumber(actual) >= Double.parseDouble(rule.value().trim());
        };
        return passes ? RuleOutcome.PASS : RuleOutcome.FAIL;
    }

    private Object extract(EligibilityRule.ProfileField field, CitizenProfile p) {
        return switch (field) {
            case OCCUPATION -> p.occupation();
            case ANNUAL_INCOME -> p.annualIncome();
            case LAND_HOLDING_ACRES -> p.landHoldingAcres();
            case AGE -> p.age();
            case GENDER -> p.gender();
            case DISTRICT -> p.district();
            case IS_BPL -> p.isBpl();
            case CATEGORY -> p.category();
        };
    }

    private boolean inList(String actual, String csv) {
        for (String option : csv.split(",")) {
            if (option.trim().equalsIgnoreCase(actual.trim())) {
                return true;
            }
        }
        return false;
    }

    private double toNumber(Object value) {
        if (value instanceof Number n) {
            return n.doubleValue();
        }
        return Double.parseDouble(value.toString());
    }

    private String stringOf(Object value) {
        return String.valueOf(value);
    }

    private String describeMissingField(EligibilityRule rule) {
        return "We need to know your %s to confirm: %s"
                .formatted(rule.field().name().toLowerCase().replace('_', ' '), rule.humanText());
    }
}
