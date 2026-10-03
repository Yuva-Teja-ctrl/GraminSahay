package in.graminsahay.domain;

import java.util.List;

/**
 * Outcome of evaluating one scheme against one citizen profile.
 *
 * @param scheme          the scheme that was evaluated
 * @param status          four-way classification
 * @param passedRules     human-readable rules the citizen satisfies
 * @param failedRules     human-readable rules the citizen violates (drives NOT_ELIGIBLE)
 * @param missingFields   profile fields that were required but not provided
 *                        (drives MISSING_INFORMATION / POSSIBLY_ELIGIBLE)
 */
public record EligibilityResult(
        Scheme scheme,
        EligibilityStatus status,
        List<String> passedRules,
        List<String> failedRules,
        List<String> missingFields
) {
}
