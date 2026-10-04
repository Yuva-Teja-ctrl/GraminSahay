package in.graminsahay;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * GraminSahay — An LLM-Powered RAG-Based Rural Welfare and Government Services Navigator.
 *
 * <p>Phase 1 (this scaffold) covers the core, interview-ready pipeline:
 * <ol>
 *   <li>Ingest official Telangana welfare scheme documents into a pgvector store.</li>
 *   <li>Retrieve relevant schemes for a citizen's situation using semantic search (RAG).</li>
 *   <li>Classify eligibility (ELIGIBLE / POSSIBLY_ELIGIBLE / NOT_ELIGIBLE / MISSING_INFORMATION)
 *       using a deterministic rule engine — NOT a free-form LLM decision.</li>
 *   <li>Generate a grounded, citation-backed explanation using the LLM.</li>
 * </ol>
 *
 * <p>The key engineering stance: the LLM handles <em>language</em> (retrieval context and
 * explanation), while deterministic rules make the <em>eligibility decision</em>. This is the
 * anti-hallucination design — a wrong "you are eligible" could harm a vulnerable citizen.
 */
@SpringBootApplication
public class GraminSahayApplication {

    public static void main(String[] args) {
        SpringApplication.run(GraminSahayApplication.class, args);
    }
}
