package in.graminsahay.eligibility;

import in.graminsahay.domain.EligibilityResult;
import in.graminsahay.domain.EligibilityStatus;
import in.graminsahay.domain.Scheme;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Scheme conflict detection — the distinctive feature from the project abstract.
 *
 * <p>Some welfare schemes are mutually exclusive by policy (a citizen may not legally claim
 * both). We model this as an undirected conflict graph: each scheme declares the ids it
 * {@code conflictsWith}, and we report any conflicting pair among the schemes the citizen is
 * (possibly) eligible for.
 *
 * <p>Modelled as a graph problem on purpose — in interviews this is a clean "I used a graph to
 * detect mutually-exclusive pairs" talking point.
 */
@Component
public class ConflictDetector {

    /**
     * A detected clash between two schemes the citizen qualifies for.
     *
     * @param schemeA one scheme name
     * @param schemeB the conflicting scheme name
     * @param message user-facing warning
     */
    public record Conflict(String schemeA, String schemeB, String message) {
    }

    /**
     * Find conflicts among the eligible / possibly-eligible schemes in the results.
     * Not-eligible schemes are ignored — you cannot clash over a benefit you cannot claim.
     */
    public List<Conflict> detect(List<EligibilityResult> results) {
        List<Scheme> candidates = results.stream()
                .filter(r -> r.status() == EligibilityStatus.ELIGIBLE
                        || r.status() == EligibilityStatus.POSSIBLY_ELIGIBLE)
                .map(EligibilityResult::scheme)
                .toList();

        Set<String> candidateIds = new HashSet<>();
        candidates.forEach(s -> candidateIds.add(s.id()));

        List<Conflict> conflicts = new ArrayList<>();
        Set<String> seenPairs = new HashSet<>();

        for (Scheme scheme : candidates) {
            if (scheme.conflictsWith() == null) {
                continue;
            }
            for (String otherId : scheme.conflictsWith()) {
                if (!candidateIds.contains(otherId)) {
                    continue; // the other scheme isn't a candidate, so no live conflict
                }
                String pairKey = canonicalPairKey(scheme.id(), otherId);
                if (seenPairs.add(pairKey)) {
                    Scheme other = findById(candidates, otherId);
                    conflicts.add(new Conflict(
                            scheme.name(),
                            other.name(),
                            "You appear eligible for both \"%s\" and \"%s\", but these cannot be claimed together. Please choose one."
                                    .formatted(scheme.name(), other.name())
                    ));
                }
            }
        }
        return conflicts;
    }

    private String canonicalPairKey(String a, String b) {
        return a.compareTo(b) < 0 ? a + "|" + b : b + "|" + a;
    }

    private Scheme findById(List<Scheme> schemes, String id) {
        return schemes.stream().filter(s -> s.id().equals(id)).findFirst().orElseThrow();
    }
}
