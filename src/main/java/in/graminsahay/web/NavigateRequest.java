package in.graminsahay.web;

import in.graminsahay.domain.CitizenProfile;
import jakarta.validation.constraints.NotBlank;

/**
 * API request body for the welfare navigation endpoint.
 *
 * @param situation       free-text description of the citizen's life situation
 *                        (e.g. "I am a small farmer in Warangal with a daughter in college")
 * @param occupation      optional structured profile fields; omitting a field makes the engine
 *                        return MISSING_INFORMATION rather than guessing
 * @param withExplanations whether to generate LLM explanations (costs an API call per scheme)
 */
public record NavigateRequest(
        @NotBlank(message = "situation is required") String situation,
        String occupation,
        Integer annualIncome,
        Double landHoldingAcres,
        Integer age,
        String gender,
        String district,
        Boolean isBpl,
        String category,
        Boolean withExplanations
) {
    public CitizenProfile toProfile() {
        return new CitizenProfile(
                occupation, annualIncome, landHoldingAcres, age, gender, district, isBpl, category);
    }

    public boolean explanationsEnabled() {
        return Boolean.TRUE.equals(withExplanations);
    }
}
