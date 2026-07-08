# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

Explain your design in plain language.

Some prompts to answer:

- What features does each `Song` use in your system
  - For example: genre, mood, energy, tempo
- What information does your `UserProfile` store
- How does your `Recommender` compute a score for each song
- How do you choose which songs to recommend

You can include a simple diagram or bullet list if helpful.

---
Real-world recommenders like Spotify and YouTube operate at massive scale — they blend collaborative filtering (patterns across millions of users), deep audio analysis (neural nets on raw waveforms), NLP on playlists and reviews, and real-time context (device, time of day, listening session length) — all re-ranked by models optimizing for engagement metrics like stream completion rate. This simulation prioritizes clarity over complexity: it uses pure content-based filtering on a single user's explicit preferences, scoring each song with a transparent weighted formula against a profile built from liked songs. No other users, no black-box neural nets, no engagement optimization — just a clean demonstration of the core idea that features can be compared mathematically to surface songs that match what one person already loves. The goal is to make every step of the recommendation decision visible and understandable.

Song Object
Maps directly to one row in songs.csv:


class Song:
    id:           int     # 1–10, unique identifier
    title:        str     # "Library Rain"
    artist:       str     # "Paper Lanterns"
    genre:        str     # "lofi" | "pop" | "rock" | "ambient" | "jazz" | "indie pop" | "synthwave"
    mood:         str     # "chill" | "happy" | "intense" | "moody" | "relaxed" | "focused"
    energy:       float   # 0.0–1.0
    tempo_bpm:    int     # 60–152 (normalize before scoring)
    valence:      float   # 0.0–1.0
    danceability: float   # 0.0–1.0 (optional — see note below)
    acousticness: float   # 0.0–1.0

Holds the user's preference target for each feature — derived by averaging the songs they've liked:


class UserProfile:
    # Categorical preferences (most-common value among liked songs)
    preferred_genre:  str     # "lofi"
    preferred_mood:   str     # "chill"

    # Numerical preferences (average value among liked songs, all 0.0–1.0)
    preferred_energy:       float   # e.g. 0.40
    preferred_acousticness: float   # e.g. 0.78
    preferred_valence:      float   # e.g. 0.58
    preferred_tempo:        float   # normalized: (bpm - 60) / (152 - 60)

Final Algorithm Recipe (100 points total)

INPUT: one song + one user profile
OUTPUT: score 0–100 + list of reasons

STEP 1 — Genre match         (30 pts)
  IF song.genre == user.genre → +30
  ELSE                        → +0

STEP 2 — Mood match          (20 pts, with partial credit)
  IF exact match              → +20
  IF same mood group          → +10   ← the fix for "focused" vs "chill"
  ELSE                        → +0

  Mood groups:
    chill   → [chill, focused, peaceful]
    happy   → [happy, upbeat, romantic]
    sad     → [sad, melancholic, nostalgic]
    intense → [intense, energetic, angry]
    moody   → [moody]
    relaxed → [relaxed]

STEP 3 — Energy proximity    (20 pts)
  +( 1 - |song.energy - user.target_energy| ) × 20

STEP 4 — Acousticness fit    (15 pts)
  +( 1 - |song.acousticness - user.target_acousticness| ) × 15

STEP 5 — Valence proximity   (10 pts)
  +( 1 - |song.valence - user.target_valence| ) × 10

STEP 6 — Tempo proximity     (5 pts)
  normalize both: (bpm - 60) / (168 - 60)
  +( 1 - |song_norm - user_norm| ) × 5

Data Flow Map

songs.csv
    │
    ▼
load_songs()
    │  reads rows, casts types (str→float/int)
    ▼
List[Dict]  ← 18 song dictionaries in memory
    │
    │   user_profile dict
    │   { genre, mood, energy,
    │     acousticness, valence, tempo_bpm }
    │         │
    ▼         ▼
score_song(user_prefs, song)   ← called once per song
    │
    │  for each feature:
    │    categorical → exact/group/miss
    │    numerical   → proximity formula
    │
    ▼
(score: float, reasons: List[str])
    │
    ▼  ← repeated for all 18 songs
List[ (song, score, reasons) ]
    │
    ▼
sort descending by score
    │
    ▼
top-k slice  →  final recommendations displayed to user

| Bias | Where it comes from | Effect |
|---|---|---|
| Genre dominance | Genre is 30 pts — a categorical cliff | A perfect numeric match in the wrong genre can never beat a mediocre song in the right genre. Intentional, but aggressive. |
| Small dataset amplification | Only 18 songs, multiple lofi entries | Lofi songs will almost always sweep the top-3 for a lofi user — no variety pressure. |
| Cold-start profile drift | Profile built from averages | One outlier liked song pulls all numeric targets off-center. A user who liked one high-energy lofi track inflates `target_energy` for every future score. |
| Unrepresented moods score 0 | Standalone moods like moody and relaxed have no group | A song with mood `"moody"` scores 0 mood points even for a user whose taste is adjacent — no partial credit available. |
| Tempo has lowest weight (5 pts) | By design | At this dataset size, tempo barely differentiates. If the dataset grew to 1000+ songs, it would matter more and the weight should be revisited. |

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Profile used: `genre=pop`, `mood=happy`, `energy=0.8`

```
Loaded songs: 18

=======================================================
  USER PROFILE
=======================================================
  genre       : pop
  mood        : happy
  energy      : 0.8

=======================================================
  TOP RECOMMENDATIONS
=======================================================

  #1  Sunrise City  —  Neon Echo
       Score : 69.6 / 100
       Genre : pop  |  Mood: happy
       Why   :
         • genre match: 'pop' (+30.0)
         • mood exact match: 'happy' (+20.0)
         • energy close: 0.82 vs target 0.8 (+19.6)

  #2  Gym Hero  —  Max Pulse
       Score : 47.4 / 100
       Genre : pop  |  Mood: intense
       Why   :
         • genre match: 'pop' (+30.0)
         • mood mismatch: 'intense' vs 'happy' (+0.0)
         • energy close: 0.93 vs target 0.8 (+17.4)

  #3  Rooftop Lights  —  Indigo Parade
       Score : 39.2 / 100
       Genre : indie pop  |  Mood: happy
       Why   :
         • genre mismatch: 'indie pop' vs 'pop' (+0.0)
         • mood exact match: 'happy' (+20.0)
         • energy close: 0.76 vs target 0.8 (+19.2)

  #4  Groove Theory  —  Funky Dept
       Score : 29.8 / 100
       Genre : funk  |  Mood: upbeat
       Why   :
         • genre mismatch: 'funk' vs 'pop' (+0.0)
         • mood compatible: 'upbeat' is in same group as 'happy' (+10.0)
         • energy close: 0.79 vs target 0.8 (+19.8)

  #5  Velvet Hours  —  Sable June
       Score : 25.0 / 100
       Genre : r&b  |  Mood: romantic
       Why   :
         • genre mismatch: 'r&b' vs 'pop' (+0.0)
         • mood compatible: 'romantic' is in same group as 'happy' (+10.0)
         • energy close: 0.55 vs target 0.8 (+15.0)

=======================================================
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



