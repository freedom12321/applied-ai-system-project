"""
Conversational taste-profile agent (Agentic Workflow stretch feature).

Uses the Google Gemini API (via the `google-genai` SDK) rather than a paid
provider, so anyone cloning this repo can run the full pipeline with a free
API key from Google AI Studio (https://aistudio.google.com/apikey) -- no
credit card or billing setup required.

Pipeline, per user request:
  1. PLAN  -- extract_profile() calls Gemini with a forced, enum-constrained
              function-calling schema to turn free-text taste descriptions
              into a structured profile the scoring engine understands. The
              enum constraint is a guardrail: the model is structurally
              unable to return a genre/mood outside the catalog.
  2. CHECK -- the returned profile is defensively re-validated and numeric
              fields are clamped, and transient API failures are retried
              with backoff. Non-retryable errors fail closed with a logged
              reason instead of crashing the app.
  3. ACT   -- the validated profile is handed to the existing
              recommender.recommend_songs() to retrieve real, scored matches.
  4. EXPLAIN -- explain_recommendations() asks Gemini to write a short
              explanation grounded in the *actual* retrieved songs/scores/
              reasons -- it is instructed never to reference a song that
              is not in that retrieved list, so the response is built from
              retrieved data rather than the model's imagination.

Every step is logged to logs/agent.log so pipeline behavior is auditable.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Dict, List, Optional, Tuple

try:
    from src.recommender import recommend_songs
except ImportError:
    from recommender import recommend_songs

try:
    from google import genai
    from google.genai import types as genai_types
    from google.genai import errors as genai_errors

    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Logging -- every pipeline step is recorded so behavior can be audited
# without re-running (and re-paying for) API calls.
# ---------------------------------------------------------------------------

_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
_LOG_PATH = os.path.join(_LOG_DIR, "agent.log")

logger = logging.getLogger("music_agent")
if not logger.handlers:
    os.makedirs(_LOG_DIR, exist_ok=True)
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
    console_handler = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(fmt)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def get_client() -> "genai.Client":
    """Build a Gemini client, or raise a clear, actionable error."""
    if not _GENAI_AVAILABLE:
        raise RuntimeError(
            "The 'google-genai' package is not installed. Run "
            "'pip install -r requirements.txt' and retry."
        )
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise RuntimeError(
            "No Gemini credentials found. Get a free API key (no credit card "
            "required) at https://aistudio.google.com/apikey and set the "
            "GEMINI_API_KEY environment variable (see README 'AI Feature Setup')."
        )
    return genai.Client()


# ---------------------------------------------------------------------------
# Guardrails: numeric clamping + categorical fallback
# ---------------------------------------------------------------------------

def _clamp01(value, field_name: str) -> Tuple[float, bool]:
    """Return (clamped_value, was_corrected)."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        logger.warning("Guardrail: '%s' was not numeric (%r); defaulting to 0.5", field_name, value)
        return 0.5, True
    clamped = max(0.0, min(1.0, x))
    corrected = clamped != x
    if corrected:
        logger.warning("Guardrail: '%s'=%s out of [0,1]; clamped to %s", field_name, x, clamped)
    return clamped, corrected


def _clamp_tempo(value) -> Tuple[float, bool]:
    """Return (clamped_value, was_corrected)."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        logger.warning("Guardrail: tempo_bpm was not numeric (%r); defaulting to 100", value)
        return 100.0, True
    clamped = max(40.0, min(220.0, x))
    corrected = clamped != x
    if corrected:
        logger.warning("Guardrail: tempo_bpm=%s out of [40,220]; clamped to %s", x, clamped)
    return clamped, corrected


def _validate_categorical(value, allowed: List[str], fallback: str, field_name: str) -> Tuple[str, bool]:
    """Return (value_or_fallback, was_corrected)."""
    if value in allowed:
        return value, False
    logger.warning(
        "Guardrail: '%s'=%r is outside the known catalog values; falling back to %r",
        field_name, value, fallback,
    )
    return fallback, True


def _confidence_from_corrections(corrections: int) -> float:
    """
    Guardrail-based confidence score: 1.0 if the model's extraction needed no
    corrections at all, decreasing by 0.15 for every field the guardrails had
    to fix (unknown category, out-of-range number). This is NOT a
    self-reported model probability -- Gemini's function-calling API doesn't
    expose one -- it's a transparent, deterministic measure of "how much did
    we have to fix," which is what actually matters for trusting the output
    of this pipeline.
    """
    return round(max(0.0, 1.0 - corrections * 0.15), 2)


def catalog_vocab(songs: List[Dict]) -> Tuple[List[str], List[str], str, str]:
    """Return (known_genres, known_moods, most_common_genre, most_common_mood)."""
    genres = [s["genre"] for s in songs]
    moods = [s["mood"] for s in songs]
    known_genres = sorted(set(genres))
    known_moods = sorted(set(moods))
    fallback_genre = max(known_genres, key=genres.count) if genres else "pop"
    fallback_mood = max(known_moods, key=moods.count) if moods else "happy"
    return known_genres, known_moods, fallback_genre, fallback_mood


# ---------------------------------------------------------------------------
# Step 1 & 2: PLAN + CHECK -- extract a structured profile from free text
# ---------------------------------------------------------------------------

def _build_extraction_tool(known_genres: List[str], known_moods: List[str]) -> "genai_types.Tool":
    function = genai_types.FunctionDeclaration(
        name="extract_taste_profile",
        description=(
            "Extract a structured music taste profile from the user's natural-language "
            "description. Only use genre/mood values that exist in the provided catalog."
        ),
        parameters_json_schema={
            "type": "object",
            "properties": {
                "genre": {"type": "string", "enum": known_genres},
                "mood": {"type": "string", "enum": known_moods},
                "energy": {
                    "type": "number",
                    "description": "Preferred energy, 0.0 (calm) to 1.0 (energetic).",
                },
                "acousticness": {
                    "type": "number",
                    "description": "Preferred acousticness, 0.0 (electronic) to 1.0 (acoustic).",
                },
                "valence": {
                    "type": "number",
                    "description": "Preferred positivity, 0.0 (sad) to 1.0 (happy).",
                },
                "tempo_bpm": {
                    "type": "integer",
                    "description": "Estimated preferred tempo in BPM, roughly 60-170.",
                },
            },
            "required": ["genre", "mood", "energy", "acousticness", "valence", "tempo_bpm"],
        },
    )
    return genai_types.Tool(function_declarations=[function])


def _is_retryable(exc: Exception) -> bool:
    if not _GENAI_AVAILABLE or not isinstance(exc, genai_errors.APIError):
        return False
    code = getattr(exc, "code", None)
    return code == 429 or (isinstance(code, int) and code >= 500)


def extract_profile(
    user_text: str,
    songs: List[Dict],
    client: Optional["genai.Client"] = None,
    model: str = DEFAULT_MODEL,
    max_retries: int = 2,
) -> Optional[Dict]:
    """
    PLAN + CHECK: turn a free-text taste description into a validated
    user-preference dict compatible with recommender.recommend_songs().

    Returns None if extraction could not be completed after retries.
    """
    known_genres, known_moods, fallback_genre, fallback_mood = catalog_vocab(songs)
    tool = _build_extraction_tool(known_genres, known_moods)

    if client is None:
        client = get_client()

    logger.info("extract_profile: user_text=%r", user_text)

    attempt = 0
    last_error: Optional[Exception] = None
    while attempt <= max_retries:
        attempt += 1
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_text,
                config=genai_types.GenerateContentConfig(
                    system_instruction=(
                        "You convert a listener's free-text description of what they want "
                        "to hear into a structured taste profile by calling "
                        "extract_taste_profile. Be decisive -- always produce a full "
                        "profile, making reasonable estimates for anything not stated "
                        "explicitly."
                    ),
                    tools=[tool],
                    tool_config=genai_types.ToolConfig(
                        function_calling_config=genai_types.FunctionCallingConfig(mode="ANY")
                    ),
                ),
            )
        except Exception as exc:  # noqa: BLE001 - broad on purpose, classified below
            last_error = exc
            if _is_retryable(exc) and attempt <= max_retries:
                delay = min(2 ** attempt, 8)
                logger.warning(
                    "extract_profile: retryable error on attempt %d (%s); backing off %ss",
                    attempt, exc, delay,
                )
                time.sleep(delay)
                continue
            logger.error("extract_profile: failed (attempt %d): %s", attempt, exc)
            return None

        function_calls = getattr(response, "function_calls", None) or []
        call = next((c for c in function_calls if c.name == "extract_taste_profile"), None)
        if call is None:
            logger.error("extract_profile: model did not return a function call; giving up")
            return None

        raw = call.args or {}
        genre, genre_fixed = _validate_categorical(raw.get("genre"), known_genres, fallback_genre, "genre")
        mood, mood_fixed = _validate_categorical(raw.get("mood"), known_moods, fallback_mood, "mood")
        energy, energy_fixed = _clamp01(raw.get("energy"), "energy")
        acousticness, ac_fixed = _clamp01(raw.get("acousticness"), "acousticness")
        valence, valence_fixed = _clamp01(raw.get("valence"), "valence")
        tempo_bpm, tempo_fixed = _clamp_tempo(raw.get("tempo_bpm"))

        corrections = sum([genre_fixed, mood_fixed, energy_fixed, ac_fixed, valence_fixed, tempo_fixed])
        confidence = _confidence_from_corrections(corrections)

        profile = {
            "genre": genre,
            "mood": mood,
            "energy": energy,
            "acousticness": acousticness,
            "valence": valence,
            "tempo_bpm": tempo_bpm,
            "confidence": confidence,
        }
        logger.info(
            "extract_profile: extracted profile=%s (corrections=%d, confidence=%.2f)",
            profile, corrections, confidence,
        )
        return profile

    logger.error("extract_profile: exhausted retries; last error=%s", last_error)
    return None


# ---------------------------------------------------------------------------
# Step 3 is just the existing recommender -- no reimplementation needed.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Step 4: EXPLAIN -- ground the write-up in the actual retrieved results
# ---------------------------------------------------------------------------

def explain_recommendations(
    user_text: str,
    profile: Dict,
    recommendations: List[Tuple[Dict, float, str]],
    client: Optional["genai.Client"] = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Ask Gemini to explain the recommendations, grounded strictly in the
    scored results already computed by recommend_songs() -- this is the
    retrieval step; the model formulates its answer from that retrieved
    data rather than from general knowledge about music.
    """
    if not recommendations:
        return "No recommendations were found to explain."

    retrieved = [
        {
            "title": song["title"],
            "artist": song["artist"],
            "genre": song["genre"],
            "mood": song["mood"],
            "score": score,
            "reasons": reasons,
        }
        for song, score, reasons in recommendations
    ]

    if client is None:
        client = get_client()

    try:
        response = client.models.generate_content(
            model=model,
            contents=(
                f"The listener said: {user_text!r}\n\n"
                f"We derived this taste profile: {json.dumps(profile)}\n\n"
                f"Retrieved, scored recommendations (highest score first):\n"
                f"{json.dumps(retrieved, indent=2)}\n\n"
                "Write a short, friendly explanation of why these songs were picked, "
                "grounded only in the data above."
            ),
            config=genai_types.GenerateContentConfig(
                system_instruction=(
                    "You explain music recommendations to a listener in 3-5 friendly "
                    "sentences. You MUST only reference songs, artists, scores, and "
                    "reasons present in the retrieved results provided in the message "
                    "-- never invent a song, artist, or fact that is not in that list."
                ),
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("explain_recommendations: failed: %s", exc)
        return (
            "(Could not generate a natural-language explanation right now -- "
            "showing the raw scored results below instead.)"
        )

    text = (getattr(response, "text", None) or "").strip()
    if not text:
        logger.warning("explain_recommendations: model returned no text content")
        return "(No explanation was generated.)"
    logger.info("explain_recommendations: generated %d-char explanation", len(text))
    return text


# ---------------------------------------------------------------------------
# Orchestration: the full agentic pipeline, callable from main.py
# ---------------------------------------------------------------------------

def run_agentic_recommendation(
    user_text: str,
    songs: List[Dict],
    k: int = 5,
    client: Optional["genai.Client"] = None,
) -> Dict:
    """
    Run the full PLAN -> CHECK -> ACT -> EXPLAIN pipeline for one user
    request. Returns a dict with keys: ok, profile, recommendations,
    explanation, error.
    """
    logger.info("=== new agentic recommendation request ===")

    if client is None:
        try:
            client = get_client()
        except RuntimeError as exc:
            logger.error("run_agentic_recommendation: %s", exc)
            return {"ok": False, "error": str(exc)}

    profile = extract_profile(user_text, songs, client=client)
    if profile is None:
        return {
            "ok": False,
            "error": "Could not understand that description -- try describing genre/mood more directly.",
        }

    recommendations = recommend_songs(profile, songs, k=k)
    explanation = explain_recommendations(user_text, profile, recommendations, client=client)

    return {
        "ok": True,
        "profile": profile,
        "recommendations": recommendations,
        "explanation": explanation,
    }
