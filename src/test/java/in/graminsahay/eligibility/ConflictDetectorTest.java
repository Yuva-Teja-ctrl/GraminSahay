package in.graminsahay.eligibility;

import in.graminsahay.domain.EligibilityResult;
import in.graminsahay.domain.EligibilityStatus;
import in.graminsahay.domain.Scheme;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Tests the mutually-exclusive scheme detection — the project's distinctive feature. */
class ConflictDetectorTest {

    private final ConflictDetector detector = new ConflictDetector();

    private Scheme scheme(String id, String name, List<String> conflictsWith) {
        return new Scheme(id, name, "agriculture", "Telangana",
                "desc", "benefit", List.of(), List.of(), "https://example.gov.in",
                List.of(), conflictsWith);
    }

    @Test
    void detectsConflictBetweenTwoEligibleSchemes() {
        Scheme a = scheme("ts-rythu-bharosa", "Rythu Bharosa", List.of("ts-indiramma-atmeeya-bharosa"));
        Scheme b = scheme("ts-indiramma-atmeeya-bharosa", "Indiramma Atmeeya Bharosa", List.of("ts-rythu-bharosa"));

        List<EligibilityResult> results = List.of(
                new EligibilityResult(a, EligibilityStatus.ELIGIBLE, List.of(), List.of(), List.of()),
                new EligibilityResult(b, EligibilityStatus.ELIGIBLE, List.of(), List.of(), List.of())
        );

        List<ConflictDetector.Conflict> conflicts = detector.detect(results);

        assertEquals(1, conflicts.size(), "exactly one conflicting pair expected");
    }

    @Test
    void noConflictWhenOneSchemeIsNotEligible() {
        Scheme a = scheme("ts-rythu-bharosa", "Rythu Bharosa", List.of("ts-indiramma-atmeeya-bharosa"));
        Scheme b = scheme("ts-indiramma-atmeeya-bharosa", "Indiramma Atmeeya Bharosa", List.of("ts-rythu-bharosa"));

        // b is NOT_ELIGIBLE, so there is nothing to clash over.
        List<EligibilityResult> results = List.of(
                new EligibilityResult(a, EligibilityStatus.ELIGIBLE, List.of(), List.of(), List.of()),
                new EligibilityResult(b, EligibilityStatus.NOT_ELIGIBLE, List.of(), List.of("some rule"), List.of())
        );

        List<ConflictDetector.Conflict> conflicts = detector.detect(results);

        assertTrue(conflicts.isEmpty(), "no conflict when a scheme is not claimable");
    }
}
