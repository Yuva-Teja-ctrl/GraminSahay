"""FastAPI application — the web edge of GraminSahay.

Combines what Spring split across GraminSahayApplication (startup), NavigatorController
(the endpoint), and NavigateRequest (the request DTO).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.auth import AuthError, AuthService
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
        db_url=settings.sqlalchemy_url,
        model_name=settings.embedding_model,
        dim=settings.embedding_dim,
        cache_dir=settings.embedding_cache_dir,
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

    auth_service = AuthService(
        db_url=settings.sqlalchemy_url,
        jwt_secret=settings.jwt_secret,
        jwt_algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_expire_minutes,
    )
    auth_service.ensure_schema()
    state["auth"] = auth_service

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


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
# auto_error=False: a missing token is allowed. GraminSahay is a public-good service for
# rural citizens, so the core navigator must work WITHOUT an account — login is an optional
# convenience (to save a profile), never a barrier to accessing welfare information.
_bearer = HTTPBearer(auto_error=False)


def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str | None:
    """FastAPI dependency: identify the user IF a valid token is supplied, else allow anonymous.

    Returns the username for a valid token, or None when no token is sent (anonymous use).
    An *invalid* token (as opposed to absent) is rejected, so a corrupt/expired session is a
    clear 401 rather than silently falling back to anonymous.
    """
    if credentials is None:
        return None  # anonymous — allowed
    auth: AuthService = state["auth"]  # type: ignore[assignment]
    try:
        return auth.verify_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


class AuthRequest(BaseModel):
    """Register/login request body."""

    username: str = Field(min_length=3)
    password: str = Field(min_length=6)


class AuthResponse(BaseModel):
    """Returned on successful register/login."""

    token: str
    username: str


@app.post("/api/auth/register", response_model=AuthResponse)
def register(request: AuthRequest) -> AuthResponse:
    """Create a new account and return a JWT."""
    auth: AuthService = state["auth"]  # type: ignore[assignment]
    try:
        token = auth.register(request.username, request.password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - never leak a bare 500; return readable JSON
        log.exception("Registration failed")
        raise HTTPException(status_code=500, detail=f"Registration failed: {exc}") from exc
    return AuthResponse(token=token, username=request.username.strip().lower())


@app.post("/api/auth/login", response_model=AuthResponse)
def login(request: AuthRequest) -> AuthResponse:
    """Verify credentials and return a JWT."""
    auth: AuthService = state["auth"]  # type: ignore[assignment]
    try:
        token = auth.login(request.username, request.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("Login failed")
        raise HTTPException(status_code=500, detail=f"Login failed: {exc}") from exc
    return AuthResponse(token=token, username=request.username.strip().lower())


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
def navigate(
    request: NavigateRequest, user: str | None = Depends(optional_user)
) -> NavigationResponse:
    """Find welfare schemes for a citizen's situation + profile.

    Works anonymously (no login needed). If a signed-in user's token is supplied, ``user`` is
    their username — available for future per-user features like saving the profile.
    """
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
    user: str | None = Depends(optional_user),
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


@app.get("/api/schemes")
def get_schemes() -> list[dict]:
    """Return all welfare schemes in the knowledge base for browsing."""
    navigator: NavigatorService = state.get("navigator")  # type: ignore[assignment]
    if not navigator:
        # Fallback if accessed before lifespan initialization in tests/dev
        settings = get_settings()
        repo = SchemeRepository(settings.schemes_path)
        return [s.model_dump(by_alias=True) for s in repo.all()]
    return [s.model_dump(by_alias=True) for s in navigator._repository.all()]


# Serve the web UI (index.html / styles.css / app.js) from app/static at the root path.
# Mounted last so it does not shadow the /api routes above.
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
