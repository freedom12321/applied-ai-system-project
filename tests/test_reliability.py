"""
Reliability harness for the agentic pipeline.

This is the project's answer to "prove it works, don't just claim it": a
fixed battery of scripted extraction scenarios, spanning a clean model
response through an unrecoverable failure, run through the real
extract_profile() pipeline (schema validation, guardrail clamping,
categorical fallback, retry/fail-closed logic -- all unmodified production
code). It measures two things a live model call alone can't guarantee:

  1. Success rate  -- does the pipeline produce a usable profile per case,
                       including the case designed to fail?
  2. Confidence     -- the guardrail-based confidence score
                       (src/agent.py::_confidence_from_corrections), which is
                       lower the more the model's raw output had to be
                       corrected.

Run `pytest tests/test_reliability.py -v -s` to see the printed summary
(the -s flag is required to see the summary; pytest hides stdout by
default). Every number in the README's Testing Summary was produced by
actually running this file, not written by hand.
"""

import os
from types import SimpleNamespace

from src.agent import extract_profile
from src.recommender import load_songs


def _songs():
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")
    return load_songs(csv_path)


def _function_call_response(args):
    call = SimpleNamespace(name="extract_taste_profile", args=args)
    return SimpleNamespace(function_calls=[call], text=None)


class ScriptedClient:
    """One-shot stand-in for the Gemini client: returns a fixed response,
    or raises if given an exception, mirroring the real SDK's response
    shape (response.function_calls) without a network call."""

    def __init__(self, response_or_exception):
        self._response = response_or_exception
        self.models = SimpleNamespace(generate_content=self._create)

    def _create(self, **kwargs):
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


# Each case is (label, scripted model output, expected number of guardrail
# corrections). The scripted outputs deliberately span the range a live
# model could plausibly return, from clean to completely malformed.
BATTERY = [
    (
        "clean extraction -- all fields valid",
        _function_call_response({
            "genre": "pop", "mood": "happy", "energy": 0.8,
            "acousticness": 0.2, "valence": 0.9, "tempo_bpm": 120,
        }),
        0,
    ),
    (
        "one out-of-range numeric field (energy=1.4)",
        _function_call_response({
            "genre": "pop", "mood": "happy", "energy": 1.4,
            "acousticness": 0.2, "valence": 0.9, "tempo_bpm": 120,
        }),
        1,
    ),
    (
        "one unknown category (genre='death metal')",
        _function_call_response({
            "genre": "death metal", "mood": "happy", "energy": 0.8,
            "acousticness": 0.2, "valence": 0.9, "tempo_bpm": 120,
        }),
        1,
    ),
    (
        "three bad fields (genre, energy, tempo)",
        _function_call_response({
            "genre": "death metal", "mood": "happy", "energy": 5.0,
            "acousticness": 0.2, "valence": 0.9, "tempo_bpm": 999,
        }),
        3,
    ),
    (
        "all six fields malformed or missing",
        _function_call_response({
            "genre": "death metal", "mood": "screamo", "energy": "loud",
            "acousticness": None, "valence": -9.0, "tempo_bpm": "fast",
        }),
        6,
    ),
    (
        "unrecoverable API failure (simulated)",
        RuntimeError("simulated malformed/refused response"),
        None,  # None marks "expected to fail closed, not produce a profile"
    ),
]


def test_reliability_battery_matches_expected_corrections():
    """Each non-failure case's guardrail-corrected profile matches the
    expected correction count exactly -- pins the confidence formula's
    behavior against concrete scenarios, not just the formula in isolation."""
    songs = _songs()
    for label, scripted_response, expected_corrections in BATTERY:
        if expected_corrections is None:
            continue  # covered by test_reliability_battery_fails_closed_on_error
        client = ScriptedClient(scripted_response)
        profile = extract_profile(f"[{label}]", songs, client=client)
        assert profile is not None, f"case {label!r} unexpectedly failed to extract"
        expected_confidence = round(max(0.0, 1.0 - expected_corrections * 0.15), 2)
        assert profile["confidence"] == expected_confidence, (
            f"case {label!r}: expected confidence {expected_confidence}, "
            f"got {profile['confidence']}"
        )


def test_reliability_battery_fails_closed_on_error():
    """The one case designed to fail (simulated API error) must return None,
    not a guessed or default profile."""
    songs = _songs()
    label, scripted_response, _ = BATTERY[-1]
    client = ScriptedClient(scripted_response)
    profile = extract_profile(f"[{label}]", songs, client=client)
    assert profile is None


def test_reliability_summary(capsys):
    """Runs the full battery once and prints a human-readable summary.

    This is intentionally not just assertions -- it's meant to be read.
    Run with `pytest tests/test_reliability.py::test_reliability_summary -s`
    to see the output.
    """
    songs = _songs()
    results = []
    for label, scripted_response, expected_corrections in BATTERY:
        client = ScriptedClient(scripted_response)
        profile = extract_profile(f"[{label}]", songs, client=client)
        succeeded = profile is not None
        confidence = profile["confidence"] if succeeded else None
        results.append((label, succeeded, confidence))

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    confidences = [c for _, ok, c in results if ok]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    with capsys.disabled():
        print(f"\n--- Reliability summary: {passed}/{total} extractions succeeded ---")
        for label, ok, confidence in results:
            status = f"OK (confidence={confidence:.2f})" if ok else "FAILED CLOSED (no profile returned)"
            print(f"  - {label}: {status}")
        print(f"Average confidence across successful extractions: {avg_confidence:.2f}")

    # The battery is designed so exactly one case fails; assert that
    # invariant so this test itself catches a regression in either
    # direction (silently succeeding on bad input, or failing on good input).
    assert passed == total - 1
