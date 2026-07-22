"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import argparse
import os
try:
    from src.recommender import load_songs, recommend_songs  # python -m src.main
    from src.agent import run_agentic_recommendation
except ImportError:
    from recommender import load_songs, recommend_songs      # python main.py inside src/
    from agent import run_agentic_recommendation

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")

# ---------------------------------------------------------------------------
# Standard profiles
# ---------------------------------------------------------------------------
PROFILES = {
    "High-Energy Pop": {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.85,
        "acousticness": 0.12,
        "valence": 0.80,
        "tempo_bpm": 125,
    },
    "Chill Lofi": {
        "genre": "lofi",
        "mood": "chill",
        "energy": 0.39,
        "acousticness": 0.78,
        "valence": 0.58,
        "tempo_bpm": 77,
    },
    "Deep Intense Rock": {
        "genre": "rock",
        "mood": "intense",
        "energy": 0.91,
        "acousticness": 0.10,
        "valence": 0.48,
        "tempo_bpm": 152,
    },
    # -----------------------------------------------------------------------
    # Adversarial / edge-case profiles
    # -----------------------------------------------------------------------
    # Conflict: high energy (0.93) paired with sad mood — tests whether
    # numeric energy score can compensate for a categorical mood mismatch.
    "ADVERSARIAL — High-Energy Sad": {
        "genre": "hip-hop",
        "mood": "sad",
        "energy": 0.93,
        "acousticness": 0.20,
        "valence": 0.30,
        "tempo_bpm": 140,
    },
    # Dead average: every numeric preference sits at 0.5 — tests whether
    # the system degenerates into pure genre/mood sorting when numerics
    # provide almost no signal differentiation.
    "ADVERSARIAL — Dead Average": {
        "genre": "ambient",
        "mood": "peaceful",
        "energy": 0.50,
        "acousticness": 0.50,
        "valence": 0.50,
        "tempo_bpm": 114,
    },
    # Genre desert: requests a genre with only one song in the catalog —
    # tests whether the system gracefully falls back on numeric similarity
    # rather than returning five copies of the same song or crashing.
    "ADVERSARIAL — Genre Desert (country)": {
        "genre": "country",
        "mood": "nostalgic",
        "energy": 0.48,
        "acousticness": 0.72,
        "valence": 0.68,
        "tempo_bpm": 100,
    },
}


def print_recommendations(label: str, user_prefs: dict, songs: list) -> None:
    """Print a labelled profile block followed by its top-5 recommendations."""
    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("\n" + "=" * 60)
    print(f"  PROFILE: {label}")
    print("=" * 60)
    for key, val in user_prefs.items():
        print(f"  {key:<12}: {val}")

    print("\n  TOP 5 RECOMMENDATIONS")
    print("  " + "-" * 56)
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n  #{rank}  {song['title']}  —  {song['artist']}")
        print(f"       Score : {score:.1f} / 100")
        print(f"       Genre : {song['genre']}  |  Mood: {song['mood']}")
        print("       Why   :")
        for reason in explanation.split("; "):
            print(f"         • {reason}")
    print("\n" + "=" * 60)


def run_chat(songs: list) -> None:
    """
    Interactive agentic mode: describe your taste in plain English and the
    Gemini-powered agent (src/agent.py) extracts a structured profile,
    scores the catalog with the existing recommender, and explains the
    picks grounded in those exact scores. Type 'quit' to exit.
    """
    print("\nDescribe the music you're in the mood for (or type 'quit').")
    while True:
        try:
            user_text = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_text:
            continue
        if user_text.lower() in {"quit", "exit"}:
            break

        result = run_agentic_recommendation(user_text, songs, k=5)
        if not result["ok"]:
            print(f"\n[!] {result['error']}")
            continue

        profile = dict(result["profile"])
        confidence = profile.pop("confidence", None)
        print("\nDerived taste profile:")
        for key, val in profile.items():
            print(f"  {key:<12}: {val}")
        if confidence is not None:
            print(f"  {'confidence':<12}: {confidence}  (1.0 = no guardrail corrections needed)")

        print("\nTop picks:")
        for rank, (song, score, _reasons) in enumerate(result["recommendations"], start=1):
            print(f"  #{rank}  {song['title']} — {song['artist']}  ({score:.1f}/100)")

        print("\nWhy:")
        print(f"  {result['explanation']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Music Recommender Simulation")
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Run the interactive natural-language agent instead of the fixed demo profiles.",
    )
    args = parser.parse_args()

    songs = load_songs(CSV_PATH)
    print(f"Loaded songs: {len(songs)}")

    if args.chat:
        run_chat(songs)
        return

    for label, prefs in PROFILES.items():
        print_recommendations(label, prefs, songs)


if __name__ == "__main__":
    main()
