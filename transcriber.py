"""Groq Whisper API client for transcribing audio."""
import io
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _client():
    from openai import OpenAI
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY tidak ditemukan. Set environment variable GROQ_API_KEY."
        )
    return OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )


def transcribe(audio_bytes: bytes, language: str,
               filename: str = "recording.webm") -> str:
    """language: 'ar' untuk Arab, 'id' untuk Indonesia."""
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename
    response = _client().audio.transcriptions.create(
        model="whisper-large-v3",
        file=audio_file,
        language=language,
        response_format="text",
        temperature=0.0,
    )
    if isinstance(response, str):
        return response.strip()
    return response.text.strip()
