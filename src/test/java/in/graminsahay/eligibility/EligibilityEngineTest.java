package in.graminsahay.eligibility;

import in.graminsahay.domain.CitizenProfile;
import in.graminsahay.domain.EligibilityResult;
import in.graminsahay.domain.EligibilityRule;
import in.graminsahay.domain.EligibilityRule.Operator;
import in.graminsahay.domain.EligibilityRule.ProfileField;
import in.graminsahay.domain.EligibilityStatus;
import in.graminsahay.domain.Scheme;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Pure-logic tests for the eligibility engine. No Spring context, no DB, no LLM — just the
 * safety-critical decision logic. This is the component to be able to explain in interviews.
 */
class EligibilityEngineTest {

    private final EligibilityEngine engine = new EligibilityEngine();

    private Scheme rythuBharosa() {
        return new Scheme(
                "ts-rythu-bharosa", "Rythu Bharosa", "agriculture", "Telangana",
                "Investment support for farmers who own cultivable land.",
                "Rs 12,000 per acre per year.",
                List.of("Aadhaar", "Pattadar passbook"),
                List.of("Verify at AEO office"),
                "https://rythubharosa.telangana.gov.in/",
                List.of(
                        new EligibilityRule(ProfileField.OCCUPATION, Operator.EQUALS, "farmer",
                                "Applicant must be a farmer"),
                        new EligibilityRule(ProfileField.LAND_HOLDING_ACRES, Operator.GREATER_THAN_OR_EQUAL, "0.01",
                                "Applicant must own cultivable agricultural land")
                ),
                List.of()
        );
    }

    @Test
    void allRulesPass_isEligible() {
        CitizenProfile farmer = new CitizenProfile(
                "farmer", 90000, 2.0, 45, "male", "Warangal", true, "obc");

        EligibilityResult result = engine.evaluate(rythuBharosa(), farmer);

        assertEquals(EligibilityStatus.ELIGIBLE, result.status());
        assertEquals(2, result.passedRules().size());
        assertEquals(0, result.failedRules().size());
    }

    @Test
    void aRuleViolated_isNotEligible() {
        // A shopkeeper with no land violates both rules.
        CitizenProfile shopkeeper = new CitizenProfile(
                "shopkeeper", 90000, 0.0, 45, "male", "Warangal", true, "obc");

        EligibilityResult result = engine.evaluate(rythuBharosa(), shopkeeper);

        assertEquals(EligibilityStatus.NOT_ELIGIBLE, result.status());
    }

    @Test
    void requiredFieldMissing_withNoPasses_isMissingInformation() {
        // Occupation unknown AND land unknown -> nothing can pass, nothing fails -> MISSING_INFORMATION.
        CitizenProfile unknown = new CitizenProfile(
                null, null, null, null, null, null, null, null);

        EligibilityResult result = engine.evaluate(rythuBharosa(), unknown);

        assertEquals(EligibilityStatus.MISSING_INFORMATION, result.status());
        assertEquals(2, result.missingFields().size());
    }

    @Test
    void somePassButAFieldMissing_isPossiblyEligible() {
        // Occupation is farmer (passes) but land is unknown (missing) -> POSSIBLY_ELIGIBLE.
        CitizenProfile partial = new CitizenProfile(
                "farmer", 90000, null, 45, "male", "Warangal", true, "obc");

        EligibilityResult result = engine.evaluate(rythuBharosa(), partial);

        assertEquals(EligibilityStatus.POSSIBLY_ELIGIBLE, result.status());
        assertEquals(1, result.passedRules().size());
        assertEquals(1, result.missingFields().size());
    }
}
