"""Generation half of the RAG pipeline — grounded, cited explanations.

ANTI-HALLUCINATION DESIGN (same as the Java version): the LLM is NOT asked to decide
eligibility; the deterministic engine already did. The LLM only phrases the already-decided
verdict in simple language, is told to use only the supplied context, and must cite the
official source. This keeps the safety-critical decision verifiable.
"""

import logging

from openai import OpenAI

from app.domain import EligibilityResult

log = logging.getLogger("graminsahay.generator")

SYSTEM_PROMPT = """\
You are GraminSahay, a helpful assistant that explains Indian government welfare schemes
to rural citizens in simple, respectful language.

STRICT RULES:
1. The eligibility decision has ALREADY been made by a rule engine. Do NOT change it,
   re-judge it, or invent new eligibility conclusions.
2. Only use the facts provided in the CONTEXT below. Never invent scheme names, benefits,
   amounts, documents, or rules that are not in the context.
3. Always state the official source link so the citizen can verify.
4. If information is marked as missing, clearly tell the citizen what detail they must
   provide, instead of guessing.
5. Keep the explanation short, warm and easy to understand.
"""


def _join_or_none(items: list[str]) -> str:
    return "; ".join(items) if items else "none"


class AnswerGenerator:
    """Calls an OpenAI-compatible chat model to explain one eligibility result."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def explain(self, result: EligibilityResult) -> str:
        context = self._build_context(result)
        user_prompt = (
            f"CONTEXT:\n{context}\n\n"
            f'Explain to the citizen, in simple language, why their status for this scheme '
            f'is "{result.status.value}". Mention benefits, what to do next, and cite the '
            f"official link."
        )
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0.1,  # low temperature -> faithful, grounded answers
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    def _build_context(self, r: EligibilityResult) -> str:
        s = r.scheme
        return (
            f"Scheme name: {s.name}\n"
            f"Category: {s.category}\n"
            f"Decision (made by rule engine, do not change): {r.status.value}\n"
            f"Benefits: {s.benefits}\n"
            f"Conditions the citizen satisfies: {_join_or_none(r.passed_rules)}\n"
            f"Conditions the citizen does NOT satisfy: {_join_or_none(r.failed_rules)}\n"
            f"Information still needed from the citizen: {_join_or_none(r.missing_fields)}\n"
            f"Required documents: {_join_or_none(s.required_documents)}\n"
            f"How to apply: {_join_or_none(s.application_steps)}\n"
            f"Official source (cite this): {s.official_url}\n"
        )
