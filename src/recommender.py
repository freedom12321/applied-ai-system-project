from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import csv

# ---------------------------------------------------------------------------
# ALGORITHM RECIPE  (total = 100 points)
#
#   +30 pts  Genre match         — exact string match
#   +20 pts  Mood match          — exact = 20, compatible group = 10, miss = 0
#   +20 pts  Energy proximity    — (1 - |song - target|) * 20
#   +15 pts  Acousticness fit    — (1 - |song - target|) * 15
#   +10 pts  Valence proximity   — (1 - |song - target|) * 10
#   + 5 pts  Tempo proximity     — (1 - |norm_bpm - target|) * 5
#
# Mood groups (partial credit fix — "focused" should not score the same as
# "angry" when the user prefers "chill"):
#   chill group:   chill, focused, peaceful
#   happy group:   happy, upbeat, romantic
#   sad group:     sad, melancholic, nostalgic
#   intense group: intense, energetic, angry
#   moody group:   moody (standalone)
#   relaxed group: relaxed (standalone)
#
# Tempo normalization: (bpm - 60) / (168 - 60)
#   anchored to the dataset range: min=60 (Spacewalk), max=168 (Iron Curtain)
# ---------------------------------------------------------------------------

MOOD_GROUPS: Dict[str, str] = {
    "chill":     "chill",
    "focused":   "chill",
    "peaceful":  "chill",
    "happy":     "happy",
    "upbeat":    "happy",
    "romantic":  "happy",
    "sad":       "sad",
    "melancholic": "sad",
    "nostalgic": "sad",
    "intense":   "intense",
    "energetic": "intense",
    "angry":     "intense",
    "moody":     "moody",
    "relaxed":   "relaxed",
}

TEMPO_MIN = 60.0
TEMPO_MAX = 168.0


def _normalize_tempo(bpm: float) -> float:
    """Scale a raw BPM value to [0, 1] using the dataset's min/max tempo range."""
    return (bpm - TEMPO_MIN) / (TEMPO_MAX - TEMPO_MIN)


def _mood_score(song_mood: str, user_mood: str) -> Tuple[float, str]:
    """Return (0–1 fraction of mood points, reason string)."""
    if song_mood == user_mood:
        return 1.0, f"mood exact match: '{song_mood}'"
    if MOOD_GROUPS.get(song_mood) == MOOD_GROUPS.get(user_mood):
        return 0.5, f"mood compatible: '{song_mood}' is in same group as '{user_mood}'"
    return 0.0, f"mood mismatch: '{song_mood}' vs '{user_mood}'"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Song:
    """Represents a song and its attributes."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """Represents a user's taste preferences."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    target_acousticness: float
    target_valence: float
    target_tempo_bpm: float
    likes_acoustic: bool  # kept for backwards compatibility


# ---------------------------------------------------------------------------
# Core scoring
# ---------------------------------------------------------------------------

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Score a single song against user preferences (0–100 points).

    Algorithm Recipe
    ----------------
    Genre match          30 pts  exact string match
    Mood match           20 pts  exact=20, compatible group=10, miss=0
    Energy proximity     20 pts  (1 - |song - target|) * 20
    Acousticness fit     15 pts  (1 - |song - target|) * 15
    Valence proximity    10 pts  (1 - |song - target|) * 10
    Tempo proximity       5 pts  (1 - |norm_song - norm_target|) * 5

    Returns (total_score, reasons) where every reason string shows the
    feature name, what was found, and the points awarded.
    """
    score = 0.0
    reasons: List[str] = []

    # --- Genre match (30 pts) ---
    if song.get("genre") == user_prefs.get("genre"):
        pts = 30.0
        score += pts
        reasons.append(f"genre match: '{song['genre']}' (+{pts:.1f})")
    else:
        reasons.append(
            f"genre mismatch: '{song.get('genre')}' vs '{user_prefs.get('genre')}' (+0.0)"
        )

    # --- Mood match (20 pts, partial credit via mood groups) ---
    mood_fraction, mood_label = _mood_score(
        str(song.get("mood", "")),
        str(user_prefs.get("mood", ""))
    )
    mood_pts = round(mood_fraction * 20, 2)
    score += mood_pts
    reasons.append(f"{mood_label} (+{mood_pts:.1f})")

    # --- Energy proximity (20 pts) ---
    if "energy" in user_prefs and "energy" in song:
        diff = abs(float(user_prefs["energy"]) - float(song["energy"]))
        pts = round((1.0 - diff) * 20, 2)
        score += pts
        closeness = "close" if diff <= 0.25 else "far"
        reasons.append(
            f"energy {closeness}: {song['energy']} vs target {user_prefs['energy']} (+{pts:.1f})"
        )

    # --- Acousticness fit (15 pts) ---
    if "acousticness" in user_prefs and "acousticness" in song:
        diff = abs(float(user_prefs["acousticness"]) - float(song["acousticness"]))
        pts = round((1.0 - diff) * 15, 2)
        score += pts
        closeness = "close" if diff <= 0.25 else "far"
        reasons.append(
            f"acousticness {closeness}: {song['acousticness']} vs target {user_prefs['acousticness']} (+{pts:.1f})"
        )

    # --- Valence proximity (10 pts) ---
    if "valence" in user_prefs and "valence" in song:
        diff = abs(float(user_prefs["valence"]) - float(song["valence"]))
        pts = round((1.0 - diff) * 10, 2)
        score += pts
        closeness = "close" if diff <= 0.25 else "far"
        reasons.append(
            f"valence {closeness}: {song['valence']} vs target {user_prefs['valence']} (+{pts:.1f})"
        )

    # --- Tempo proximity (5 pts, normalized to dataset range 60–168 bpm) ---
    if "tempo_bpm" in user_prefs and "tempo_bpm" in song:
        user_norm = _normalize_tempo(float(user_prefs["tempo_bpm"]))
        song_norm = _normalize_tempo(float(song["tempo_bpm"]))
        diff = abs(user_norm - song_norm)
        pts = round((1.0 - diff) * 5, 2)
        score += pts
        reasons.append(
            f"tempo: {song['tempo_bpm']} bpm vs target {user_prefs['tempo_bpm']} bpm (+{pts:.1f})"
        )

    return (round(score, 2), reasons)


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5
) -> List[Tuple[Dict, float, str]]:
    """
    Score every song, sort descending, return top-k.

    Returns list of (song_dict, score, explanation_string).

    Pythonic pipeline:
      1. List comprehension  — calls score_song once per song, builds all records
      2. sorted()            — returns a new list ranked highest-to-lowest score
      3. [:k] slice          — trims to the top-k results
    """
    def score_and_explain(song: Dict) -> Tuple[Dict, float, str]:
        """Run score_song and join its reasons list into a single explanation string."""
        score, reasons = score_song(user_prefs, song)
        explanation = "; ".join(reasons) or "no strong feature matches"
        return (song, score, explanation)

    return sorted(
        [score_and_explain(song) for song in songs],
        key=lambda rec: rec[1],
        reverse=True
    )[:k]


# ---------------------------------------------------------------------------
# CSV loader
# ---------------------------------------------------------------------------

def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file and return as a list of dicts."""
    print(f"Loading songs from {csv_path}...")
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["energy"]       = float(row["energy"])
            row["tempo_bpm"]    = float(row["tempo_bpm"])
            row["valence"]      = float(row["valence"])
            row["danceability"] = float(row["danceability"])
            row["acousticness"] = float(row["acousticness"])
            row["id"]           = int(row["id"])
            songs.append(row)
    return songs


# ---------------------------------------------------------------------------
# OOP wrapper (mirrors functional API above)
# ---------------------------------------------------------------------------

class Recommender:
    """OOP implementation of the recommendation logic."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _song_to_dict(self, song: Song) -> Dict:
        return {
            "id":           song.id,
            "title":        song.title,
            "artist":       song.artist,
            "genre":        song.genre,
            "mood":         song.mood,
            "energy":       song.energy,
            "tempo_bpm":    song.tempo_bpm,
            "valence":      song.valence,
            "danceability": song.danceability,
            "acousticness": song.acousticness,
        }

    def _profile_to_dict(self, user: UserProfile) -> Dict:
        return {
            "genre":        user.favorite_genre,
            "mood":         user.favorite_mood,
            "energy":       user.target_energy,
            "acousticness": user.target_acousticness,
            "valence":      user.target_valence,
            "tempo_bpm":    user.target_tempo_bpm,
        }

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        prefs = self._profile_to_dict(user)
        song_dicts = [self._song_to_dict(s) for s in self.songs]
        results = recommend_songs(prefs, song_dicts, k)
        id_to_song = {s.id: s for s in self.songs}
        return [id_to_song[r[0]["id"]] for r in results]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        prefs = self._profile_to_dict(user)
        _, reasons = score_song(prefs, self._song_to_dict(song))
        return "; ".join(reasons) if reasons else "no strong feature matches"
