"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import os
try:
    from src.recommender import load_songs, recommend_songs  # python -m src.main
except ImportError:
    from recommender import load_songs, recommend_songs      # python main.py inside src/

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")


def main() -> None:
    songs = load_songs(CSV_PATH)
    print(f"Loaded songs: {len(songs)}")

    # Starter example profile
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("\n" + "=" * 55)
    print("  USER PROFILE")
    print("=" * 55)
    for key, val in user_prefs.items():
        print(f"  {key:<12}: {val}")

    print("\n" + "=" * 55)
    print("  TOP RECOMMENDATIONS")
    print("=" * 55)
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n  #{rank}  {song['title']}  —  {song['artist']}")
        print(f"       Score : {score:.1f} / 100")
        print(f"       Genre : {song['genre']}  |  Mood: {song['mood']}")
        print("       Why   :")
        for reason in explanation.split("; "):
            print(f"         • {reason}")
    print("\n" + "=" * 55)


if __name__ == "__main__":
    main()
