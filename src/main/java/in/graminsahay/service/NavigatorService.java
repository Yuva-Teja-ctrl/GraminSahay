package in.graminsahay.service;

import in.graminsahay.domain.CitizenProfile;
import in.graminsahay.domain.EligibilityResult;
import in.graminsahay.domain.Scheme;
import in.graminsahay.eligibility.ConflictDetector;
import in.graminsahay.eligibility.EligibilityEngine;
import in.graminsahay.rag.AnswerGenerator;
import in.graminsahay.rag.SchemeRetriever;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Orchestrates the full GraminSahay pipeline end to end:
 *
 * <pre>
 *   situation + profile
 *        -> (1) RAG retrieval of candidate schemes
 *        -> (2) deterministic eligibility evaluation per scheme
 *        -> (3) scheme conflict detection across the eligible set
 *        -> (4) grounded LLM explanation per scheme
 * </pre>
 *
 * This is the single place that ties retrieval, reasoning, conflict detection and generation
 * together — the "proposed system" flow from the project PPT.
 */
@Service
public class NavigatorService {

    private final SchemeRetriever retriever;
    private final EligibilityEngine eligibilityEngine;
    private final ConflictDetector conflictDetector;
    private final AnswerGenerator answerGenerator;

    public NavigatorService(SchemeRetriever retriever,
                            EligibilityEngine eligibilityEngine,
                            ConflictDetector conflictDetector,
                            AnswerGenerator answerGenerator) {
        this.retriever = retriever;
        this.eligibilityEngine = eligibilityEngine;
        this.conflictDetector = conflictDetector;
        this.answerGenerator = answerGenerator;
    }

    /**
     * Full result for the citizen.
     *
     * @param schemes   per-scheme eligibility + explanation, best status first
     * @param conflicts any mutually-exclusive scheme pairs the citizen qualifies for
     */
    public record NavigationResponse(List<SchemeAdvice> schemes, List<ConflictDetector.Conflict> conflicts) {
    }

    /** Per-scheme advice returned to the citizen. */
    public record SchemeAdvice(
            String schemeId,
            String schemeName,
            String category,
            String status,
            List<String> satisfiedConditions,
            List<String> unmetConditions,
            List<String> informationNeeded,
            List<String> requiredDocuments,
            List<String> applicationSteps,
            String officialUrl,
            String explanation
    ) {
    }

    public NavigationResponse navigate(String situation, CitizenProfile profile, boolean withExplanations) {
        // (1) Retrieve candidate schemes semantically.
        List<Scheme> candidates = retriever.retrieve(situation);

        // (2) Evaluate eligibility deterministically.
        List<EligibilityResult> results = new ArrayList<>();
        for (Scheme scheme : candidates) {
            results.add(eligibilityEngine.evaluate(scheme, profile));
        }

        // Order so the citizen sees ELIGIBLE first, then POSSIBLY, MISSING, NOT.
        results.sort(Comparator.comparingInt(r -> r.status().ordinal()));

        // (3) Detect conflicts across the eligible set.
        List<ConflictDetector.Conflict> conflicts = conflictDetector.detect(results);

        // (4) Generate grounded explanations (optional — skip to save LLM calls/cost).
        List<SchemeAdvice> advice = new ArrayList<>();
        for (EligibilityResult r : results) {
            String explanation = withExplanations ? answerGenerator.explain(r) : null;
            advice.add(toAdvice(r, explanation));
        }

        return new NavigationResponse(advice, conflicts);
    }

    private SchemeAdvice toAdvice(EligibilityResult r, String explanation) {
        Scheme s = r.scheme();
        return new SchemeAdvice(
                s.id(),
                s.name(),
                s.category(),
                r.status().name(),
                r.passedRules(),
                r.failedRules(),
                r.missingFields(),
                s.requiredDocuments(),
                s.applicationSteps(),
                s.officialUrl(),
                explanation
        );
    }
}
