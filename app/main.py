"""FastAPI application — the web edge of GraminSahay.

Combines what Spring split across GraminSahayApplication (startup), NavigatorController
(the endpoint), and NavigateRequest (the request DTO).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import get_settings
from app.domain import CitizenProfile
from app.generator import AnswerGenerator
from app.knowledge import SchemeRepository
from app.navigator import NavigationResponse, NavigatorService
from app.vectorstore import VectorStore

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("graminsahay")

# Holds the wired-up service once startup completes (set in the lifespan handler below).
state: dict[str, NavigatorService] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once at startup — the equivalent of Spring's bean wiring + ApplicationRunner.

    We build the components, create the DB schema, and ingest+embed the schemes before the
    server starts accepting requests.
    """
    settings = get_settings()

    repository = SchemeRepository(settings.schemes_path)
    vector_store = VectorStore(
        db_url=settings.db_url,
        model_name=settings.embedding_model,
        dim=settings.embedding_dim,
    )
    vector_store.ensure_schema()
    vector_store.ingest(repository.all())

    generator = AnswerGenerator(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.chat_model,
    )

    state["navigator"] = NavigatorService(
        repository=repository,
        vector_store=vector_store,
        generator=generator,
        top_k=settings.rag_top_k,
        similarity_threshold=settings.rag_similarity_threshold,
    )
    log.info("GraminSahay is ready.")
    yield
    state.clear()


app = FastAPI(title="GraminSahay", version="0.1.0", lifespan=lifespan)

# Allow the frontend (served from the same app, but handy during development) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class NavigateRequest(BaseModel):
    """API request body. Mirrors the Java NavigateRequest DTO.

    Only ``situation`` is required (``min_length=1`` is FastAPI's equivalent of @NotBlank).
    Omitting a profile field is meaningful: it makes the engine return MISSING_INFORMATION /
    POSSIBLY_ELIGIBLE rather than guessing.
    """

    situation: str = Field(min_length=1)
    occupation: str | None = None
    annual_income: int | None = Field(default=None, alias="annualIncome")
    land_holding_acres: float | None = Field(default=None, alias="landHoldingAcres")
    age: int | None = None
    gender: str | None = None
    district: str | None = None
    is_bpl: bool | None = Field(default=None, alias="isBpl")
    category: str | None = None
    with_explanations: bool = Field(default=False, alias="withExplanations")

    model_config = {"populate_by_name": True}

    def to_profile(self) -> CitizenProfile:
        return CitizenProfile(
            occupation=self.occupation,
            annual_income=self.annual_income,
            land_holding_acres=self.land_holding_acres,
            age=self.age,
            gender=self.gender,
            district=self.district,
            is_bpl=self.is_bpl,
            category=self.category,
        )


@app.post("/api/navigate", response_model=NavigationResponse, response_model_by_alias=True)
def navigate(request: NavigateRequest) -> NavigationResponse:
    """Find welfare schemes for a citizen's situation + profile."""
    navigator = state["navigator"]
    return navigator.navigate(
        situation=request.situation,
        profile=request.to_profile(),
        with_explanations=request.with_explanations,
    )


# Serve the web UI (index.html / styles.css / app.js) from app/static at the root path.
# Mounted last so it does not shadow the /api routes above.
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
