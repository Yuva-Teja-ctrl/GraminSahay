"""Orchestrates the full GraminSahay pipeline end to end.

    situation + profile
         -> (1) RAG retrieval of candidate schemes
         -> (2) deterministic eligibility evaluation per scheme
         -> (3) scheme conflict detection across the eligible set
         -> (4) grounded LLM explanation per scheme

Equivalent to the Java ``NavigatorService``.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app import eligibility
from app.domain import STATUS_ORDER, CitizenProfile, Conflict
from app.generator import AnswerGenerator
from app.knowledge import SchemeRepository
from app.vectorstore import VectorStore


class CamelModel(BaseModel):
    """Base model that serializes fields as camelCase in JSON.

    We write Pythonic snake_case field names, but the JSON the API emits uses camelCase
    (schemeName, satisfiedConditions, ...). This lets the SAME frontend built for the Java
    backend work unchanged against this Python backend. ``populate_by_name`` also lets code
    construct these models using the snake_case names.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SchemeAdvice(CamelModel):
    """Per-scheme advice returned to the citizen (shape of the API response items)."""

    scheme_id: str
    scheme_name: str
    category: str
    status: str
    satisfied_conditions: list[str]
    unmet_conditions: list[str]
    information_needed: list[str]
    required_documents: list[str]
    application_steps: list[str]
    official_url: str
    explanation: str | None = None


class NavigationResponse(CamelModel):
    """Full result for the citizen: ranked schemes + any conflicts."""

    schemes: list[SchemeAdvice]
    conflicts: list[Conflict]


class NavigatorService:
    def __init__(
        self,
        repository: SchemeRepository,
        vector_store: VectorStore,
        generator: AnswerGenerator,
        top_k: int,
        similarity_threshold: float,
    ) -> None:
        self._repository = repository
        self._vector_store = vector_store
        self._generator = generator
        self._top_k = top_k
        self._similarity_threshold = similarity_threshold

    def navigate(
        self, situation: str, profile: CitizenProfile, with_explanations: bool
    ) -> NavigationResponse:
        # (1) Retrieve candidate schemes semantically.
        scheme_ids = self._vector_store.search(
            situation, self._top_k, self._similarity_threshold
        )
        candidates = [s for sid in scheme_ids if (s := self._repository.by_id(sid))]

        # (2) Evaluate eligibility deterministically.
        results = [eligibility.evaluate(scheme, profile) for scheme in candidates]

        # Order so the citizen sees ELIGIBLE first, then POSSIBLY, MISSING, NOT.
        results.sort(key=lambda r: STATUS_ORDER[r.status])

        # (3) Detect conflicts across the eligible set.
        conflicts = eligibility.detect_conflicts(results)

        # (4) Generate grounded explanations (optional — skip to save LLM calls/cost).
        advice: list[SchemeAdvice] = []
        for r in results:
            explanation = self._generator.explain(r) if with_explanations else None
            advice.append(
                SchemeAdvice(
                    scheme_id=r.scheme.id,
                    scheme_name=r.scheme.name,
                    category=r.scheme.category,
                    status=r.status.value,
                    satisfied_conditions=r.passed_rules,
                    unmet_conditions=r.failed_rules,
                    information_needed=r.missing_fields,
                    required_documents=r.scheme.required_documents,
                    application_steps=r.scheme.application_steps,
                    official_url=r.scheme.official_url,
                    explanation=explanation,
                )
            )

        return NavigationResponse(schemes=advice, conflicts=conflicts)
