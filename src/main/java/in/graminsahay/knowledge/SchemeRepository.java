package in.graminsahay.knowledge;

import com.fasterxml.jackson.databind.ObjectMapper;
import in.graminsahay.domain.Scheme;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.stereotype.Repository;

import java.io.InputStream;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * Loads the scheme knowledge base from JSON at startup and keeps it in memory.
 *
 * <p>The same {@link Scheme} objects are used for (a) embedding into the vector store for
 * retrieval and (b) deterministic eligibility evaluation, so there is a single source of truth.
 */
@Repository
public class SchemeRepository {

    private static final Logger log = LoggerFactory.getLogger(SchemeRepository.class);

    private final ResourceLoader resourceLoader;
    private final ObjectMapper objectMapper;

    @Value("${graminsahay.ingest.schemes-location}")
    private String schemesLocation;

    private Map<String, Scheme> schemesById = Map.of();

    public SchemeRepository(ResourceLoader resourceLoader, ObjectMapper objectMapper) {
        this.resourceLoader = resourceLoader;
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    void load() {
        Resource resource = resourceLoader.getResource(schemesLocation);
        try (InputStream in = resource.getInputStream()) {
            List<Scheme> schemes = objectMapper.readValue(
                    in, objectMapper.getTypeFactory().constructCollectionType(List.class, Scheme.class));
            this.schemesById = schemes.stream()
                    .collect(Collectors.toUnmodifiableMap(Scheme::id, s -> s));
            log.info("Loaded {} welfare schemes from {}", schemes.size(), schemesLocation);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to load scheme knowledge base from " + schemesLocation, e);
        }
    }

    public List<Scheme> findAll() {
        return List.copyOf(schemesById.values());
    }

    public Optional<Scheme> findById(String id) {
        return Optional.ofNullable(schemesById.get(id));
    }
}
