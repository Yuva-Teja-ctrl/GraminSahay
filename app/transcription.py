"""Speech-to-text — the voice-input half of the voice-first experience.

A citizen records themselves describing their situation; we send that audio to a Whisper
model (served by Groq via the same OpenAI-compatible API) and get back the text, which then
flows through the normal pipeline (translation -> extraction -> retrieval -> ...).

Whisper is multilingual, so a citizen can speak in English, Telugu or Hindi. We pass a
language hint when we have one to improve accuracy.

Fail-safe, like the rest of the app: if transcription fails we raise a clear error that the
endpoint turns into a friendly message, rather than crashing.
"""

import logging

from openai import OpenAI

log = logging.getLogger("graminsahay.transcription")


class Transcriber:
    """Wraps Whisper speech-to-text."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def transcribe(self, audio_bytes: bytes, filename: str, language: str | None = None) -> str:
        """Transcribe recorded audio to text.

        :param audio_bytes: the raw audio file content
        :param filename:    original filename (Whisper uses the extension to detect format)
        :param language:    optional ISO code ("en"/"te"/"hi") to hint the spoken language
        :returns:           the transcribed text
        :raises RuntimeError: if transcription fails
        """
        try:
            # The OpenAI SDK expects a (filename, bytes) tuple for the file field.
            kwargs = {"model": self._model, "file": (filename, audio_bytes)}
            if language and language != "auto":
                kwargs["language"] = language
            result = self._client.audio.transcriptions.create(**kwargs)
            return (result.text or "").strip()
        except Exception as exc:  # noqa: BLE001
            log.warning("Transcription failed (%s): %s", type(exc).__name__, exc)
            raise RuntimeError("Could not transcribe the audio. Please try again or type instead.") from exc
