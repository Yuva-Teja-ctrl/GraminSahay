"""Multilingual support — translate citizen input to English for processing, and translate
explanations back into the citizen's language.

This delivers the "in their own language" promise of the project abstract. The design keeps
the core pipeline (retrieval, extraction, eligibility, conflicts) running in ENGLISH — which
is where the embedding model and scheme knowledge base are strongest — and uses the LLM only
at the edges to translate in and out. This is the common, robust "translate -> process ->
translate back" pattern for multilingual RAG.

Fail-safe (consistent with the rest of the app): if a translation call fails, we return the
original text unchanged rather than erroring. Worst case the citizen sees English, which is
far better than a 500.
"""

import logging

from openai import OpenAI

log = logging.getLogger("graminsahay.translation")

# Languages the UI offers. Keyed by the short code the frontend sends.
SUPPORTED_LANGUAGES = {
    "en": "English",
    "te": "Telugu",
    "hi": "Hindi",
}


def language_name(code: str) -> str:
    """Human-readable name for a language code (defaults to English)."""
    return SUPPORTED_LANGUAGES.get(code, "English")


class Translator:
    """LLM-backed translator used at the input and output edges of the pipeline."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def to_english(self, text: str, source_lang: str) -> str:
        """Translate the citizen's text into English for internal processing.

        No-op when the source is already English.
        """
        if source_lang == "en" or not text.strip():
            return text
        return self._translate(text, language_name(source_lang), "English")

    def from_english(self, text: str, target_lang: str) -> str:
        """Translate an English answer into the citizen's language for display.

        No-op when the target is English or there is nothing to translate.
        """
        if target_lang == "en" or not text or not text.strip():
            return text
        return self._translate(text, "English", language_name(target_lang))

    def _translate(self, text: str, source_name: str, target_name: str) -> str:
        system_prompt = (
            f"You are a translator for a government welfare assistant used by rural citizens. "
            f"Translate the user's message from {source_name} to {target_name}. "
            f"Preserve meaning, scheme names, numbers, and URLs exactly. "
            f"Use simple, respectful everyday language. "
            f"Return ONLY the translation, with no quotes or commentary."
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            )
            translated = response.choices[0].message.content
            return translated.strip() if translated else text
        except Exception as exc:  # noqa: BLE001 - degrade gracefully: return original text
            log.warning(
                "Translation unavailable (%s -> %s) (%s): %s",
                source_name,
                target_name,
                type(exc).__name__,
                exc,
            )
            return text
