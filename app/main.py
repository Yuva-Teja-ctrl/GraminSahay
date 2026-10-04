"""FastAPI application — the web edge of GraminSahay.

Combines what Spring split across GraminSahayApplication (startup), NavigatorController
(the endpoint), and NavigateRequest (the request DTO).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import get_settings
from app.domain import CitizenProfile
from app.extractor import ProfileExtractor
from app.generator import AnswerGenerator
from app.knowledge import SchemeRepository
from app.navigator import NavigationResponse, NavigatorService
from app.transcription import Transcriber
from app.translation import Translator
from app.vectorstore import VectorStore

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("graminsahay")

# Holds the wired-up components once startup completes (set in the lifespan handler below):
# "navigator" -> NavigatorService, "transcriber" -> Transcriber.
state: dict[str, object] = {}


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
    extractor = ProfileExtractor(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.chat_model,
    )
    translator = Translator(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.chat_model,
    )
    state["transcriber"] = Transcriber(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.transcribe_model,
    )

    state["navigator"] = NavigatorService(
        repository=repository,
        vector_store=vector_store,
        generator=generator,
        extractor=extractor,
        translator=translator,
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
    # When true (default), extract a structured profile from `situation` via the LLM and merge
    # it with any fields supplied above. Set false to use only the explicit fields.
    auto_extract: bool = Field(default=True, alias="autoExtract")
    # Citizen's language: "en" (default), "te" (Telugu) or "hi" (Hindi). Input is translated
    # to English for processing and explanations are translated back into this language.
    language: str = "en"

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
    navigator: NavigatorService = state["navigator"]  # type: ignore[assignment]
    return navigator.navigate(
        situation=request.situation,
        profile=request.to_profile(),
        with_explanations=request.with_explanations,
        auto_extract=request.auto_extract,
        language=request.language,
    )


class TranscribeResponse(BaseModel):
    """Result of transcribing a voice recording."""

    text: str


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form("auto"),
) -> TranscribeResponse:
    """Voice input: accept an audio recording and return the transcribed text.

    The frontend records the citizen's microphone and posts the audio here. We return the
    text, which the UI drops into the situation box so the citizen can review it before
    searching. ``language`` is an optional hint ("en"/"te"/"hi"/"auto").
    """
    transcriber: Transcriber = state["transcriber"]  # type: ignore[assignment]
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio received.")
    try:
        text = transcriber.transcribe(
            audio_bytes=audio_bytes,
            filename=audio.filename or "recording.webm",
            language=language,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return TranscribeResponse(text=text)


# Serve the web UI (index.html / styles.css / app.js) from app/static at the root path.
# Mounted last so it does not shadow the /api routes above.
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
