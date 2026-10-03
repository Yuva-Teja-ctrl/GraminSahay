package in.graminsahay.domain;

/**
 * The structured profile we extract from a citizen's free-text / voice description.
 *
 * <p>In the proposed system this is populated from a natural-language situation such as
 * "I am a farmer with a small landholding and a daughter starting college". Phase 1 accepts
 * these fields directly via the API; a later phase can add an LLM extraction step that turns
 * free text into this structured object.
 *
 * <p>Nullable fields matter: a {@code null} field means "citizen did not tell us", which is
 * exactly what drives the {@code MISSING_INFORMATION} classification instead of guessing.
 *
 * @param occupation       e.g. "farmer", "student", "unorganised_worker"
 * @param annualIncome      household annual income in INR; null if unknown
 * @param landHoldingAcres  agricultural land owned in acres; null if unknown / not applicable
 * @param age               age in years; null if unknown
 * @param gender            "male" | "female" | "other"; null if unknown
 * @param district          Telangana district; null if unknown
 * @param isBpl             whether the citizen holds a Below Poverty Line card; null if unknown
 * @param category          social category: "general" | "obc" | "sc" | "st"; null if unknown
 */
public record CitizenProfile(
        String occupation,
        Integer annualIncome,
        Double landHoldingAcres,
        Integer age,
        String gender,
        String district,
        Boolean isBpl,
        String category
) {
}
