package in.graminsahay.domain;

import java.util.List;

/**
 * A government welfare scheme loaded from the knowledge base.
 *
 * <p>This is both the retrieval unit (its {@code description} + {@code benefits} are embedded
 * into the vector store) and the eligibility unit (its {@code rules} are evaluated by the
 * {@link EligibilityEngine}).
 *
 * @param id              stable identifier, e.g. "ts-rythu-bharosa"
 * @param name            official scheme name
 * @param category        one of: agriculture, education, healthcare, housing, pension
 * @param state           "Telangana"
 * @param description     plain-language summary (embedded for semantic search)
 * @param benefits        what the citizen receives
 * @param requiredDocuments documents needed to apply
 * @param applicationSteps step-by-step guidance
 * @param officialUrl     source link — used as the citation in generated answers
 * @param rules           deterministic eligibility conditions (ALL must pass for ELIGIBLE)
 * @param conflictsWith   ids of schemes that cannot be claimed together with this one
 */
public record Scheme(
        String id,
        String name,
        String category,
        String state,
        String description,
        String benefits,
        List<String> requiredDocuments,
        List<String> applicationSteps,
        String officialUrl,
        List<EligibilityRule> rules,
        List<String> conflictsWith
) {
    /** Text we embed into the vector store for semantic retrieval. */
    public String embeddableText() {
        return """
                Scheme: %s
                Category: %s
                State: %s
                What it is: %s
                Benefits: %s
                """.formatted(name, category, state, description, benefits);
    }
}
