"""Situation -> structured profile extraction.

This delivers the headline promise of the project abstract: a citizen simply DESCRIBES their
life situation ("I am a farmer with two acres in Warangal and a daughter starting college"),
and the system figures out the structured details (occupation, land, district, ...) instead
of making them fill a form.

SAFETY-CRITICAL DESIGN (the key interview point):
    The extractor is CONSERVATIVE. It only fills a field when the citizen clearly stated or
    strongly implied it. Anything uncertain stays ``null``. A null field then flows into the
    existing eligibility engine as MISSING_INFORMATION — so the system asks a follow-up
    question rather than inventing a detail that could wrongly grant or deny a benefit.

    In other words: the LLM EXTRACTS facts the citizen gave; it never INVENTS facts to make a
    scheme match. This preserves the "LLM for language, rules for decisions" philosophy right
    at the input boundary.
"""

import json
import logging

from openai import OpenAI

from app.domain import CitizenProfile

log = logging.getLogger("graminsahay.extractor")

SYSTEM_PROMPT = """\
You extract a structured profile from a rural Indian citizen's free-text description of their
life situation, to help match them to government welfare schemes.

Return ONLY a JSON object with these keys (use null when the citizen did not clearly state or
strongly imply the value — NEVER guess):

{
  "occupation": string | null,          // e.g. "farmer", "student", "agricultural_labourer", "labourer"
  "annual_income": integer | null,      // household annual income in rupees
  "land_holding_acres": number | null,  // acres of agricultural land owned (0 if explicitly landless)
  "age": integer | null,
  "gender": "male" | "female" | "other" | null,
  "district": string | null,            // a Telangana district name
  "is_bpl": boolean | null,             // true if they mention a white ration card / BPL / very poor
  "category": "general" | "obc" | "sc" | "st" | "minority" | null
}

RULES:
1. Only fill a field if the text clearly supports it. When in doubt, use null.
2. Do NOT infer caste/category, income, or BPL status from occupation or vague poverty hints
   unless explicitly stated.
3. "small / marginal farmer" implies occupation "farmer" but does NOT give an exact acreage —
   leave land_holding_acres null unless a number is given.
4. Output strictly valid JSON. No commentary, no markdown fences.
"""


class ProfileExtractor:
    """Uses an LLM to turn a free-text situation into a (partial) CitizenProfile."""

    # Keys we accept back from the model, mapped onto CitizenProfile fields.
    _ALLOWED_KEYS = {
        "occupation",
        "annual_income",
        "land_holding_acres",
        "age",
        "gender",
        "district",
        "is_bpl",
        "category",
    }

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def extract(self, situation: str) -> CitizenProfile:
        """Extract a profile from free text.

        Robust across providers: we first try the model's native JSON mode; if that is not
        supported (some Groq models reject it), we retry WITHOUT json mode and parse the JSON
        out of the reply ourselves.

        Fail-safe: if the LLM is unavailable or returns something unparseable, we return an
        EMPTY profile (all None). An empty profile is safe — every scheme simply becomes
        MISSING_INFORMATION, so the citizen is asked for details rather than mis-matched.
        """
        raw = self._call_llm(situation)
        if raw is None:
            return CitizenProfile()

        data = self._parse_json(raw)
        if data is None:
            log.warning("Profile extraction: could not parse JSON from model output: %r", raw[:300])
            return CitizenProfile()

        # Keep only known keys; ignore anything unexpected the model may add.
        clean = {k: v for k, v in data.items() if k in self._ALLOWED_KEYS}
        try:
            profile = CitizenProfile(**clean)
            log.info("Profile extraction succeeded: %s", clean)
            return profile
        except Exception as exc:  # noqa: BLE001 - bad types from the model -> safe empty profile
            log.warning("Extracted profile failed validation (%s): %s", type(exc).__name__, exc)
            return CitizenProfile()

    def _call_llm(self, situation: str) -> str | None:
        """Call the chat model, trying JSON mode first and falling back if unsupported."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Citizen's description:\n{situation}"},
        ]
        # Attempt 1: native JSON mode (best when supported — OpenAI, newer Groq models).
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "JSON mode failed (%s): %s — retrying without json mode.",
                type(exc).__name__,
                exc,
            )

        # Attempt 2: plain call, no response_format. We'll extract the JSON from the text.
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0.0,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as exc:  # noqa: BLE001 - truly unavailable
            log.warning("Profile extraction unavailable (%s): %s", type(exc).__name__, exc)
            return None

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        """Parse a JSON object out of the model's reply.

        Handles three cases: clean JSON, JSON wrapped in ```json fences, and JSON embedded in
        surrounding prose (we grab the outermost {...}).
        """
        text = raw.strip()
        # Strip markdown code fences if present.
        if text.startswith("```"):
            text = text.strip("`")
            # drop an optional leading "json" language tag
            if text.lstrip().lower().startswith("json"):
                text = text.lstrip()[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Last resort: grab the first {...} block.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def merge(extracted: CitizenProfile, provided: CitizenProfile) -> CitizenProfile:
        """Merge an extracted profile with any fields the citizen filled in explicitly.

        Explicit form values ALWAYS win over LLM-extracted ones — the human is the source of
        truth. We only fall back to the extracted value where the form left a field blank.
        """
        merged = {}
        for field in CitizenProfile.model_fields:
            provided_value = getattr(provided, field)
            merged[field] = provided_value if provided_value is not None else getattr(extracted, field)
        return CitizenProfile(**merged)
