package in.graminsahay.rag;

import in.graminsahay.domain.EligibilityResult;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Generation half of the RAG pipeline — produces a plain-language explanation.
 *
 * <p><strong>Anti-hallucination design.</strong> The LLM is NOT asked to decide eligibility; the
 * deterministic {@link in.graminsahay.eligibility.EligibilityEngine} already did that. The LLM
 * only phrases the already-decided verdict in simple language, and is instructed to rely solely
 * on the supplied context and to cite the official source. This keeps the safety-critical
 * decision verifiable while still giving the citizen a friendly, readable answer.
 */
@Service
public class AnswerGenerator {

    private static final String SYSTEM_PROMPT = """
            You are GraminSahay, a helpful assistant that explains Indian government welfare schemes
            to rural citizens in simple, respectful language.

            STRICT RULES:
            1. The eligibility decision has ALREADY been made by a rule engine. Do NOT change it,
               re-judge it, or invent new eligibility conclusions.
            2. Only use the facts provided in the CONTEXT below. Never invent scheme names,
               benefits, amounts, documents, or rules that are not in the context.
            3. Always state the official source link so the citizen can verify.
            4. If information is marked as missing, clearly tell the citizen what detail they
               must provide, instead of guessing.
            5. Keep the explanation short, warm and easy to understand.
            """;

    private final ChatClient chatClient;

    public AnswerGenerator(ChatClient.Builder chatClientBuilder) {
        this.chatClient = chatClientBuilder.build();
    }

    /** Build a grounded explanation for one scheme's eligibility result. */
    public String explain(EligibilityResult result) {
        String context = buildContext(result);
        return chatClient.prompt()
                .system(SYSTEM_PROMPT)
                .user(u -> u.text("""
                        CONTEXT:
                        {context}

                        Explain to the citizen, in simple language, why their status for this scheme is
                        "{status}". Mention benefits, what to do next, and cite the official link.
                        """)
                        .param("context", context)
                        .param("status", result.status().name()))
                .call()
                .content();
    }

    private String buildContext(EligibilityResult r) {
        return """
                Scheme name: %s
                Category: %s
                Decision (made by rule engine, do not change): %s
                Benefits: %s
                Conditions the citizen satisfies: %s
                Conditions the citizen does NOT satisfy: %s
                Information still needed from the citizen: %s
                Required documents: %s
                How to apply: %s
                Official source (cite this): %s
                """.formatted(
                r.scheme().name(),
                r.scheme().category(),
                r.status().name(),
                r.scheme().benefits(),
                joinOrNone(r.passedRules()),
                joinOrNone(r.failedRules()),
                joinOrNone(r.missingFields()),
                joinOrNone(r.scheme().requiredDocuments()),
                joinOrNone(r.scheme().applicationSteps()),
                r.scheme().officialUrl()
        );
    }

    private String joinOrNone(List<String> items) {
        if (items == null || items.isEmpty()) {
            return "none";
        }
        return items.stream().collect(Collectors.joining("; "));
    }
}
