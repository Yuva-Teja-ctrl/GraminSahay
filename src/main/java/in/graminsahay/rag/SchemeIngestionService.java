package in.graminsahay.rag;

import in.graminsahay.domain.Scheme;
import in.graminsahay.knowledge.SchemeRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.document.Document;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

/**
 * Embeds the scheme knowledge base into the pgvector store on startup.
 *
 * <p>Each scheme becomes one {@link Document}. We store the scheme id, name and category as
 * metadata so that after a semantic search we can map a retrieved chunk back to the full
 * {@link Scheme} (and therefore to its eligibility rules and citation URL).
 *
 * <p>Idempotency: we only ingest when the store looks empty, so restarting the app does not
 * duplicate embeddings. For a production system you'd use content hashing / upserts.
 */
@Service
public class SchemeIngestionService implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(SchemeIngestionService.class);

    public static final String META_SCHEME_ID = "schemeId";
    public static final String META_SCHEME_NAME = "schemeName";
    public static final String META_CATEGORY = "category";

    private final SchemeRepository schemeRepository;
    private final VectorStore vectorStore;

    public SchemeIngestionService(SchemeRepository schemeRepository, VectorStore vectorStore) {
        this.schemeRepository = schemeRepository;
        this.vectorStore = vectorStore;
    }

    @Override
    public void run(ApplicationArguments args) {
        if (alreadyIngested()) {
            log.info("Vector store already contains scheme embeddings; skipping ingestion.");
            return;
        }
        List<Document> documents = schemeRepository.findAll().stream()
                .map(this::toDocument)
                .toList();
        vectorStore.add(documents);
        log.info("Ingested {} scheme documents into the vector store.", documents.size());
    }

    private boolean alreadyIngested() {
        try {
            List<Document> existing = vectorStore.similaritySearch(
                    SearchRequest.query("welfare scheme").withTopK(1));
            return existing != null && !existing.isEmpty();
        } catch (Exception e) {
            // Store not initialised yet / empty — treat as not ingested.
            return false;
        }
    }

    private Document toDocument(Scheme scheme) {
        return new Document(
                scheme.embeddableText(),
                Map.of(
                        META_SCHEME_ID, scheme.id(),
                        META_SCHEME_NAME, scheme.name(),
                        META_CATEGORY, scheme.category()
                )
        );
    }
}
