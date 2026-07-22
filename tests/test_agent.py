"""
Tests for the agentic taste-profile pipeline (src/agent.py).

These tests never make a real network call: the Gemini client is replaced
with small fakes that mimic the shape of a google-genai SDK response
(response.function_calls -> list of objects with .name / .args, and
response.text for plain text). This keeps the suite reproducible without an
API key, and lets us exercise the guardrail logic (clamping, categorical
fallback, retries) deterministically.
"""

from types import SimpleNamespace

import pytest

from src.agent import (
    _clamp01,
    _clamp_tempo,
    _confidence_from_corrections,
    _validate_categorical,
    catalog_vocab,
    explain_recommendations,
    extract_profile,
)


def make_songs():
    return [
        {"id": 1, "title": "Sunrise City", "artist": "Neon Echo", "genre": "pop", "mood": "happy",
         "energy": 0.82, "tempo_bpm": 118, "valence": 0.84, "danceability": 0.79, "acousticness": 0.18},
        {"id": 2, "title": "Midnight Coding", "artist": "LoRoom", "genre": "lofi", "mood": "chill",
         "energy": 0.42, "tempo_bpm": 78, "valence": 0.56, "danceability": 0.62, "acousticness": 0.71},
    ]


def make_function_call_response(name, args):
    call = SimpleNamespace(name=name, args=args)
    return SimpleNamespace(function_calls=[call], text=None)


def make_text_response(text):
    return SimpleNamespace(function_calls=None, text=text)


class FakeClient:
    """Records calls and returns a scripted sequence of responses/exceptions."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.models = SimpleNamespace(generate_content=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


# ---------------------------------------------------------------------------
# Guardrail unit tests
# ---------------------------------------------------------------------------

def test_clamp01_clamps_out_of_range_values():
    assert _clamp01(1.5, "energy") == (1.0, True)
    assert _clamp01(-0.3, "energy") == (0.0, True)
    assert _clamp01(0.4, "energy") == (0.4, False)


def test_clamp01_defaults_on_non_numeric():
    assert _clamp01("not a number", "energy") == (0.5, True)
    assert _clamp01(None, "energy") == (0.5, True)


def test_clamp_tempo_clamps_to_reasonable_bpm_range():
    assert _clamp_tempo(9999) == (220.0, True)
    assert _clamp_tempo(1) == (40.0, True)
    assert _clamp_tempo(120) == (120.0, False)


def test_validate_categorical_falls_back_on_unknown_value():
    allowed = ["pop", "lofi"]
    assert _validate_categorical("pop", allowed, "lofi", "genre") == ("pop", False)
    assert _validate_categorical("death metal", allowed, "lofi", "genre") == ("lofi", True)


def test_confidence_from_corrections_decreases_with_each_correction():
    assert _confidence_from_corrections(0) == 1.0
    assert _confidence_from_corrections(1) == 0.85
    assert _confidence_from_corrections(3) == 0.55
    assert _confidence_from_corrections(6) == 0.1
    assert _confidence_from_corrections(100) == 0.0  # floors at 0, never negative


def test_catalog_vocab_derives_known_values_from_songs():
    songs = make_songs()
    known_genres, known_moods, fallback_genre, fallback_mood = catalog_vocab(songs)
    assert set(known_genres) == {"pop", "lofi"}
    assert set(known_moods) == {"happy", "chill"}
    assert fallback_genre in known_genres
    assert fallback_mood in known_moods


# ---------------------------------------------------------------------------
# extract_profile: happy path, guardrail clamping, and retry behavior
# ---------------------------------------------------------------------------

def test_extract_profile_happy_path_returns_valid_profile():
    songs = make_songs()
    fake = FakeClient([
        make_function_call_response("extract_taste_profile", {
            "genre": "lofi", "mood": "chill", "energy": 0.3,
            "acousticness": 0.8, "valence": 0.5, "tempo_bpm": 75,
        })
    ])
    profile = extract_profile("something chill for studying", songs, client=fake)
    assert profile == {
        "genre": "lofi", "mood": "chill", "energy": 0.3,
        "acousticness": 0.8, "valence": 0.5, "tempo_bpm": 75.0,
        "confidence": 1.0,  # no corrections needed -> full confidence
    }
    assert len(fake.calls) == 1
    assert fake.calls[0]["model"]
    assert fake.calls[0]["contents"] == "something chill for studying"


def test_extract_profile_clamps_out_of_range_numeric_fields():
    songs = make_songs()
    fake = FakeClient([
        make_function_call_response("extract_taste_profile", {
            "genre": "pop", "mood": "happy", "energy": 5.0,
            "acousticness": -1.0, "valence": 0.5, "tempo_bpm": 999,
        })
    ])
    profile = extract_profile("upbeat pop", songs, client=fake)
    assert profile["energy"] == 1.0
    assert profile["acousticness"] == 0.0
    assert profile["tempo_bpm"] == 220.0
    # 3 fields needed correction (energy, acousticness, tempo_bpm) -> confidence drops
    assert profile["confidence"] == 0.55


def test_extract_profile_falls_back_on_unknown_categorical_value():
    songs = make_songs()
    fake = FakeClient([
        make_function_call_response("extract_taste_profile", {
            "genre": "death metal",  # not in catalog -- should never happen with a valid enum
            "mood": "happy", "energy": 0.5, "acousticness": 0.5,
            "valence": 0.5, "tempo_bpm": 100,
        })
    ])
    profile = extract_profile("something loud", songs, client=fake)
    known_genres, _, _, _ = catalog_vocab(songs)
    assert profile["genre"] in known_genres
    # exactly 1 field needed correction (genre) -> confidence drops by one step
    assert profile["confidence"] == 0.85


def test_extract_profile_returns_none_when_no_function_call_returned():
    songs = make_songs()
    fake = FakeClient([make_text_response("I'm not sure what you mean.")])
    profile = extract_profile("???", songs, client=fake)
    assert profile is None


def test_extract_profile_returns_none_on_non_retryable_error():
    songs = make_songs()
    fake = FakeClient([RuntimeError("boom")])
    profile = extract_profile("anything", songs, client=fake, max_retries=2)
    assert profile is None
    assert len(fake.calls) == 1  # no retry for a non-retryable error


# ---------------------------------------------------------------------------
# explain_recommendations: grounding + graceful failure
# ---------------------------------------------------------------------------

def test_explain_recommendations_returns_model_text():
    songs = make_songs()
    profile = {"genre": "lofi", "mood": "chill", "energy": 0.4,
               "acousticness": 0.7, "valence": 0.5, "tempo_bpm": 78}
    recs = [(songs[1], 95.0, "genre match: 'lofi' (+30.0)")]
    fake = FakeClient([make_text_response("Midnight Coding is a great chill lofi match.")])

    explanation = explain_recommendations("something chill", profile, recs, client=fake)
    assert "Midnight Coding" in explanation
    # The retrieved data actually reached the prompt sent to the model.
    sent_contents = fake.calls[0]["contents"]
    assert "Midnight Coding" in sent_contents
    assert "95.0" in sent_contents


def test_explain_recommendations_handles_empty_list_without_calling_api():
    fake = FakeClient([])
    explanation = explain_recommendations("anything", {}, [], client=fake)
    assert "No recommendations" in explanation
    assert fake.calls == []


def test_explain_recommendations_fails_gracefully_on_api_error():
    songs = make_songs()
    recs = [(songs[0], 80.0, "genre match")]
    fake = FakeClient([RuntimeError("network down")])
    explanation = explain_recommendations("anything", {}, recs, client=fake)
    assert "Could not generate" in explanation
