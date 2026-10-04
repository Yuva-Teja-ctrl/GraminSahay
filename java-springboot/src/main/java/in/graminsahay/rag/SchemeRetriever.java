package in.graminsahay.rag;

import in.graminsahay.domain.Scheme;
import in.graminsahay.knowledge.SchemeRepository;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Retrieval half of the RAG pipeline.
 *
 * <p>Takes the citizen's free-text situation, runs a semantic similarity search against the
 * pgvector store, and resolves the matching chunks back to full {@link Scheme} objects (so the
 * eligibility engine and the answer generator have the rules, documents and citation URL).
 */
@Service
public class SchemeRetriever {

    private final VectorStore vectorStore;
    private final SchemeRepository schemeRepository;

    @Value("${graminsahay.rag.top-k:6}")
    private int topK;

    @Value("${graminsahay.rag.similarity-threshold:0.5}")
    private double similarityThreshold;

    public SchemeRetriever(VectorStore vectorStore, SchemeRepository schemeRepository) {
        this.vectorStore = vectorStore;
        this.schemeRepository = schemeRepository;
    }

    /** Semantic search -> deduplicated list of candidate schemes, most relevant first. */
    public List<Scheme> retrieve(String situation) {
        SearchRequest request = SearchRequest.query(situation)
                .withTopK(topK)
                .withSimilarityThreshold(similarityThreshold);

        List<Document> matches = vectorStore.similaritySearch(request);

        Set<String> seen = new LinkedHashSet<>();
        List<Scheme> schemes = new ArrayList<>();
        for (Document doc : matches) {
            Object schemeId = doc.getMetadata().get(SchemeIngestionService.META_SCHEME_ID);
            if (schemeId == null) {
                continue;
            }
            String id = schemeId.toString();
            if (seen.add(id)) {
                schemeRepository.findById(id).ifPresent(schemes::add);
            }
        }
        return schemes;
    }
}
