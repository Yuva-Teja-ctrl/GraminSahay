"""Domain models.

These mirror the Java `record` classes 1:1. In Python we use Pydantic ``BaseModel`` (and an
``Enum``), which gives us the same immutability-friendly value objects PLUS automatic JSON
(de)serialization and validation — the job that Jackson + Bean Validation did in Spring.
"""

from enum import Enum

from pydantic import BaseModel, Field


class EligibilityStatus(str, Enum):
    """Four-way eligibility classification from the project abstract.

    Subclassing ``str`` means the enum serializes to a plain string in JSON (e.g. "ELIGIBLE"),
    exactly like the Java enum did.

    The ELIGIBLE..NOT_ELIGIBLE order matters: we sort results by this order so the citizen
    sees the best outcomes first (see NavigatorService).
    """

    ELIGIBLE = "ELIGIBLE"
    POSSIBLY_ELIGIBLE = "POSSIBLY_ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    MISSING_INFORMATION = "MISSING_INFORMATION"


# Rank used to sort results (lower = shown first). Mirrors the Java enum ordinal() trick.
STATUS_ORDER = {
    EligibilityStatus.ELIGIBLE: 0,
    EligibilityStatus.POSSIBLY_ELIGIBLE: 1,
    EligibilityStatus.MISSING_INFORMATION: 2,
    EligibilityStatus.NOT_ELIGIBLE: 3,
}


class ProfileField(str, Enum):
    """Citizen attributes a rule can inspect (matches EligibilityRule.ProfileField in Java)."""

    OCCUPATION = "OCCUPATION"
    ANNUAL_INCOME = "ANNUAL_INCOME"
    LAND_HOLDING_ACRES = "LAND_HOLDING_ACRES"
    AGE = "AGE"
    GENDER = "GENDER"
    DISTRICT = "DISTRICT"
    IS_BPL = "IS_BPL"
    CATEGORY = "CATEGORY"


class Operator(str, Enum):
    """Supported comparisons (matches EligibilityRule.Operator in Java)."""

    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    IN = "IN"  # comma-separated membership, e.g. "sc,st"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    IS_TRUE = "IS_TRUE"


class EligibilityRule(BaseModel):
    """A single, machine-checkable eligibility condition for a scheme."""

    field: ProfileField
    operator: Operator
    value: str = ""
    human_text: str = Field(alias="humanText")

    # populate_by_name lets us build rules in code using the python name (human_text) while
    # still reading the camelCase "humanText" key from the JSON knowledge base.
    model_config = {"populate_by_name": True}


class Scheme(BaseModel):
    """A government welfare scheme loaded from the knowledge base.

    Serves as BOTH the retrieval unit (its text is embedded) and the eligibility unit (its
    rules are evaluated) — a single source of truth, like the Java version.
    """

    id: str
    name: str
    category: str
    state: str
    description: str
    benefits: str
    required_documents: list[str] = Field(default_factory=list, alias="requiredDocuments")
    application_steps: list[str] = Field(default_factory=list, alias="applicationSteps")
    official_url: str = Field(default="", alias="officialUrl")
    rules: list[EligibilityRule] = Field(default_factory=list)
    conflicts_with: list[str] = Field(default_factory=list, alias="conflictsWith")

    model_config = {"populate_by_name": True}

    def embeddable_text(self) -> str:
        """Text we embed into the vector store for semantic retrieval."""
        return (
            f"Scheme: {self.name}\n"
            f"Category: {self.category}\n"
            f"State: {self.state}\n"
            f"What it is: {self.description}\n"
            f"Benefits: {self.benefits}\n"
        )


class CitizenProfile(BaseModel):
    """Structured profile extracted from the citizen's description.

    Every field is Optional (``| None``) and defaults to ``None``. A ``None`` field means
    "the citizen did not tell us", which is exactly what drives MISSING_INFORMATION instead
    of guessing — the safety-critical distinction.
    """

    occupation: str | None = None
    annual_income: int | None = None
    land_holding_acres: float | None = None
    age: int | None = None
    gender: str | None = None
    district: str | None = None
    is_bpl: bool | None = None
    category: str | None = None


class EligibilityResult(BaseModel):
    """Outcome of evaluating one scheme against one citizen profile."""

    scheme: Scheme
    status: EligibilityStatus
    passed_rules: list[str] = Field(default_factory=list)
    failed_rules: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class Conflict(BaseModel):
    """A detected clash between two schemes the citizen qualifies for."""

    scheme_a: str = Field(serialization_alias="schemeA")
    scheme_b: str = Field(serialization_alias="schemeB")
    message: str
