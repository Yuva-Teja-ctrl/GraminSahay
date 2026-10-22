"""Vector store + local embeddings — the retrieval half of the RAG pipeline.

Design choice vs. the Java version: instead of calling a paid embedding API, we embed LOCALLY
with the sentence-transformers model ``all-MiniLM-L6-v2`` (the model family used in your
ResuMate project). This means semantic search runs with no API key and no cost; you only need
an LLM key for explanations.

The model runs through ``fastembed`` (ONNX Runtime) rather than the ``sentence-transformers``
package. Same model, same 384-dim normalized vectors — but no PyTorch, so the app fits in
~512 MB RAM (e.g. Render's free tier) instead of needing 1–2 GB.

The vectors are stored in PostgreSQL via the ``pgvector`` extension, queried with cosine
distance — the same storage and distance metric as the Spring AI version.
"""

from __future__ import annotations

import logging

from fastembed import TextEmbedding
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, String, Text, create_engine, select, text
from sqlalchemy.orm import Session, declarative_base

from app.config import get_settings
from app.domain import Scheme

log = logging.getLogger("graminsahay.vectorstore")

Base = declarative_base()

# Vector dimension is fixed by the embedding model (all-MiniLM-L6-v2 -> 384). We read it from
# settings once, at import time, so the column has a concrete size when the table is created.
_EMBEDDING_DIM = get_settings().embedding_dim


class SchemeEmbedding(Base):
    """One row per scheme: its id/name/category metadata plus the embedding vector."""

    __tablename__ = "scheme_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scheme_id = Column(String, unique=True, nullable=False)
    scheme_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(_EMBEDDING_DIM))


class VectorStore:
    """Wraps the embedding model + Postgres/pgvector table.

    Lifecycle:
      * __init__ loads the embedding model (downloaded once, then cached locally).
      * ensure_schema() creates the pgvector extension and table.
      * ingest() embeds and stores schemes (idempotent — skips if already populated).
      * search() embeds the query and returns the most similar schemes.
    """

    def __init__(
        self, db_url: str, model_name: str, dim: int, cache_dir: str | None = None
    ) -> None:
        self._engine = create_engine(db_url, pool_pre_ping=True)
        self._dim = dim
        self._model = load_embedding_model(model_name, cache_dir)

    # ---- schema ----
    def ensure_schema(self) -> None:
        # Enable the pgvector extension, then create the table (column dimension is already
        # fixed at _EMBEDDING_DIM when the model class was defined).
        with self._engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        Base.metadata.create_all(self._engine)

    # ---- embedding helper ----
    def _embed(self, text_value: str) -> list[float]:
        # fastembed mean-pools and L2-normalizes this model's output (same as
        # sentence-transformers with normalize_embeddings=True), so cosine distance behaves
        # consistently. embed() takes a batch and yields one numpy vector per input.
        vector = next(iter(self._model.embed([text_value])))
        return vector.tolist()

    # ---- ingestion ----
    def ingest(self, schemes: list[Scheme]) -> None:
        with Session(self._engine) as session:
            already = session.scalar(select(SchemeEmbedding).limit(1))
            if already is not None:
                log.info("Vector store already populated; skipping ingestion.")
                return
            for scheme in schemes:
                session.add(
                    SchemeEmbedding(
                        scheme_id=scheme.id,
                        scheme_name=scheme.name,
                        category=scheme.category,
                        content=scheme.embeddable_text(),
                        embedding=self._embed(scheme.embeddable_text()),
                    )
                )
            session.commit()
            log.info("Ingested %d scheme documents into the vector store.", len(schemes))

    # ---- retrieval ----
    def search(self, query: str, top_k: int, similarity_threshold: float) -> list[str]:
        """Return scheme ids ordered by semantic similarity to the query.

        pgvector's ``cosine_distance`` returns 0 (identical) .. 2 (opposite); we convert it to
        a 0..1 similarity and keep only results above the threshold.
        """
        query_vec = self._embed(query)
        with Session(self._engine) as session:
            distance = SchemeEmbedding.embedding.cosine_distance(query_vec)
            rows = session.execute(
                select(SchemeEmbedding.scheme_id, distance.label("distance"))
                .order_by(distance)
                .limit(top_k)
            ).all()

        results: list[str] = []
        for scheme_id, dist in rows:
            similarity = 1.0 - (float(dist) / 2.0)
            if similarity >= similarity_threshold:
                results.append(scheme_id)
        return results


def load_embedding_model(model_name: str, cache_dir: str | None = None) -> TextEmbedding:
    """Load (downloading on first use) the ONNX embedding model into ``cache_dir``."""
    log.info("Loading embedding model '%s' (first run downloads it)…", model_name)
    return TextEmbedding(model_name=model_name, cache_dir=cache_dir)


if __name__ == "__main__":
    # `python -m app.vectorstore` pre-downloads the model. The Render build runs this so the
    # model ships with the build and the server starts without downloading anything.
    logging.basicConfig(level=logging.INFO)
    _settings = get_settings()
    load_embedding_model(_settings.embedding_model, _settings.embedding_cache_dir)
    log.info("Embedding model cached in '%s'.", _settings.embedding_cache_dir)
