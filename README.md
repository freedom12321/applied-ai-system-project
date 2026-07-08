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

Six profiles tested: three standard and three adversarial edge cases.
Run with: `python -m src.main`

---

### Profile 1 — High-Energy Pop

```
============================================================
  PROFILE: High-Energy Pop
============================================================
  genre       : pop
  mood        : happy
  energy      : 0.85
  acousticness: 0.12
  valence     : 0.8
  tempo_bpm   : 125

  TOP 5 RECOMMENDATIONS
  --------------------------------------------------------

  #1  Sunrise City  —  Neon Echo
       Score : 97.8 / 100
       Genre : pop  |  Mood: happy
       Why   :
         • genre match: 'pop' (+30.0)
         • mood exact match: 'happy' (+20.0)
         • energy close: 0.82 vs target 0.85 (+19.4)
         • acousticness close: 0.18 vs target 0.12 (+14.1)
         • valence close: 0.84 vs target 0.8 (+9.6)
         • tempo: 118.0 bpm vs target 125 bpm (+4.7)

  #2  Gym Hero  —  Max Pulse
       Score : 76.7 / 100
       Genre : pop  |  Mood: intense
       Why   :
         • genre match: 'pop' (+30.0)
         • mood mismatch: 'intense' vs 'happy' (+0.0)
         • energy close: 0.93 vs target 0.85 (+18.4)
         • acousticness close: 0.05 vs target 0.12 (+13.9)
         • valence close: 0.77 vs target 0.8 (+9.7)
         • tempo: 132.0 bpm vs target 125 bpm (+4.7)

  #3  Rooftop Lights  —  Indigo Parade
       Score : 64.6 / 100
       Genre : indie pop  |  Mood: happy
       Why   :
         • genre mismatch: 'indie pop' vs 'pop' (+0.0)
         • mood exact match: 'happy' (+20.0)
         • energy close: 0.76 vs target 0.85 (+18.2)
         • acousticness close: 0.35 vs target 0.12 (+11.6)
         • valence close: 0.81 vs target 0.8 (+9.9)
         • tempo: 124.0 bpm vs target 125 bpm (+5.0)

  #4  Groove Theory  —  Funky Dept
       Score : 54.5 / 100
       Genre : funk  |  Mood: upbeat
       Why   :
         • genre mismatch: 'funk' vs 'pop' (+0.0)
         • mood compatible: 'upbeat' is in same group as 'happy' (+10.0)
         • energy close: 0.79 vs target 0.85 (+18.8)
         • acousticness close: 0.3 vs target 0.12 (+12.3)
         • valence close: 0.88 vs target 0.8 (+9.2)
         • tempo: 108.0 bpm vs target 125 bpm (+4.2)

  #5  Velvet Hours  —  Sable June
       Score : 47.3 / 100
       Genre : r&b  |  Mood: romantic
       Why   :
         • genre mismatch: 'r&b' vs 'pop' (+0.0)
         • mood compatible: 'romantic' is in same group as 'happy' (+10.0)
         • energy far: 0.55 vs target 0.85 (+14.0)
         • acousticness far: 0.45 vs target 0.12 (+10.1)
         • valence close: 0.76 vs target 0.8 (+9.6)
         • tempo: 95.0 bpm vs target 125 bpm (+3.6)

============================================================
```

---

### Profile 2 — Chill Lofi

```
============================================================
  PROFILE: Chill Lofi
============================================================
  genre       : lofi
  mood        : chill
  energy      : 0.39
  acousticness: 0.78
  valence     : 0.58
  tempo_bpm   : 77

  TOP 5 RECOMMENDATIONS
  --------------------------------------------------------

  #1  Midnight Coding  —  LoRoom
       Score : 98.1 / 100
       Genre : lofi  |  Mood: chill
       Why   :
         • genre match: 'lofi' (+30.0)
         • mood exact match: 'chill' (+20.0)
         • energy close: 0.42 vs target 0.39 (+19.4)
         • acousticness close: 0.71 vs target 0.78 (+13.9)
         • valence close: 0.56 vs target 0.58 (+9.8)
         • tempo: 78.0 bpm vs target 77 bpm (+5.0)

  #2  Library Rain  —  Paper Lanterns
       Score : 97.6 / 100
       Genre : lofi  |  Mood: chill
       Why   :
         • genre match: 'lofi' (+30.0)
         • mood exact match: 'chill' (+20.0)
         • energy close: 0.35 vs target 0.39 (+19.2)
         • acousticness close: 0.86 vs target 0.78 (+13.8)
         • valence close: 0.6 vs target 0.58 (+9.8)
         • tempo: 72.0 bpm vs target 77 bpm (+4.8)

  #3  Focus Flow  —  LoRoom
       Score : 89.6 / 100
       Genre : lofi  |  Mood: focused
       Why   :
         • genre match: 'lofi' (+30.0)
         • mood compatible: 'focused' is in same group as 'chill' (+10.0)
         • energy close: 0.4 vs target 0.39 (+19.8)
         • acousticness close: 0.78 vs target 0.78 (+15.0)
         • valence close: 0.59 vs target 0.58 (+9.9)
         • tempo: 80.0 bpm vs target 77 bpm (+4.9)

  #4  Spacewalk Thoughts  —  Orbit Bloom
       Score : 64.2 / 100
       Genre : ambient  |  Mood: chill
       Why   :
         • genre mismatch: 'ambient' vs 'lofi' (+0.0)
         • mood exact match: 'chill' (+20.0)
         • energy close: 0.28 vs target 0.39 (+17.8)
         • acousticness close: 0.92 vs target 0.78 (+12.9)
         • valence close: 0.65 vs target 0.58 (+9.3)
         • tempo: 60.0 bpm vs target 77 bpm (+4.2)

  #5  Sunday Sonata  —  Elara Strings
       Score : 52.2 / 100
       Genre : classical  |  Mood: peaceful
       Why   :
         • genre mismatch: 'classical' vs 'lofi' (+0.0)
         • mood compatible: 'peaceful' is in same group as 'chill' (+10.0)
         • energy close: 0.22 vs target 0.39 (+16.6)
         • acousticness close: 0.95 vs target 0.78 (+12.4)
         • valence close: 0.72 vs target 0.58 (+8.6)
         • tempo: 68.0 bpm vs target 77 bpm (+4.6)

============================================================
```

---

### Profile 3 — Deep Intense Rock

```
============================================================
  PROFILE: Deep Intense Rock
============================================================
  genre       : rock
  mood        : intense
  energy      : 0.91
  acousticness: 0.1
  valence     : 0.48
  tempo_bpm   : 152

  TOP 5 RECOMMENDATIONS
  --------------------------------------------------------

  #1  Storm Runner  —  Voltline
       Score : 100.0 / 100
       Genre : rock  |  Mood: intense
       Why   :
         • genre match: 'rock' (+30.0)
         • mood exact match: 'intense' (+20.0)
         • energy close: 0.91 vs target 0.91 (+20.0)
         • acousticness close: 0.1 vs target 0.1 (+15.0)
         • valence close: 0.48 vs target 0.48 (+10.0)
         • tempo: 152.0 bpm vs target 152 bpm (+5.0)

  #2  Gym Hero  —  Max Pulse
       Score : 65.0 / 100
       Genre : pop  |  Mood: intense
       Why   :
         • genre mismatch: 'pop' vs 'rock' (+0.0)
         • mood exact match: 'intense' (+20.0)
         • energy close: 0.93 vs target 0.91 (+19.6)
         • acousticness close: 0.05 vs target 0.1 (+14.2)
         • valence far: 0.77 vs target 0.48 (+7.1)
         • tempo: 132.0 bpm vs target 152 bpm (+4.1)

  #3  Iron Curtain  —  Wraith Engine
       Score : 55.2 / 100
       Genre : metal  |  Mood: angry
       Why   :
         • genre mismatch: 'metal' vs 'rock' (+0.0)
         • mood compatible: 'angry' is in same group as 'intense' (+10.0)
         • energy close: 0.97 vs target 0.91 (+18.8)
         • acousticness close: 0.04 vs target 0.1 (+14.1)
         • valence close: 0.28 vs target 0.48 (+8.0)
         • tempo: 168.0 bpm vs target 152 bpm (+4.3)

  #4  Grid Collapse  —  Bass Architect
       Score : 54.5 / 100
       Genre : edm  |  Mood: energetic
       Why   :
         • genre mismatch: 'edm' vs 'rock' (+0.0)
         • mood compatible: 'energetic' is in same group as 'intense' (+10.0)
         • energy close: 0.96 vs target 0.91 (+19.0)
         • acousticness close: 0.03 vs target 0.1 (+13.9)
         • valence close: 0.71 vs target 0.48 (+7.7)
         • tempo: 128.0 bpm vs target 152 bpm (+3.9)

  #5  Night Drive Loop  —  Neon Echo
       Score : 43.0 / 100
       Genre : synthwave  |  Mood: moody
       Why   :
         • genre mismatch: 'synthwave' vs 'rock' (+0.0)
         • mood mismatch: 'moody' vs 'intense' (+0.0)
         • energy close: 0.75 vs target 0.91 (+16.8)
         • acousticness close: 0.22 vs target 0.1 (+13.2)
         • valence close: 0.49 vs target 0.48 (+9.9)
         • tempo: 110.0 bpm vs target 152 bpm (+3.1)

============================================================
```

---

### Profile 4 — ADVERSARIAL: High-Energy Sad (conflicting preferences)

```
============================================================
  PROFILE: ADVERSARIAL — High-Energy Sad
============================================================
  genre       : hip-hop
  mood        : sad
  energy      : 0.93
  acousticness: 0.2
  valence     : 0.3
  tempo_bpm   : 140

  TOP 5 RECOMMENDATIONS
  --------------------------------------------------------

  #1  Broken Clocks  —  Gray Verse
       Score : 89.6 / 100
       Genre : hip-hop  |  Mood: sad
       Why   :
         • genre match: 'hip-hop' (+30.0)
         • mood exact match: 'sad' (+20.0)
         • energy far: 0.58 vs target 0.93 (+13.0)
         • acousticness close: 0.25 vs target 0.2 (+14.2)
         • valence close: 0.32 vs target 0.3 (+9.8)
         • tempo: 88.0 bpm vs target 140 bpm (+2.6)

  #2  Storm Runner  —  Voltline
       Score : 45.7 / 100
       Genre : rock  |  Mood: intense
       Why   :
         • genre mismatch: 'rock' vs 'hip-hop' (+0.0)
         • mood mismatch: 'intense' vs 'sad' (+0.0)
         • energy close: 0.91 vs target 0.93 (+19.6)
         • acousticness close: 0.1 vs target 0.2 (+13.5)
         • valence close: 0.48 vs target 0.3 (+8.2)
         • tempo: 152.0 bpm vs target 140 bpm (+4.4)

  #3  Iron Curtain  —  Wraith Engine
       Score : 45.3 / 100
       Genre : metal  |  Mood: angry
       Why   :
         • genre mismatch: 'metal' vs 'hip-hop' (+0.0)
         • mood mismatch: 'angry' vs 'sad' (+0.0)
         • energy close: 0.97 vs target 0.93 (+19.2)
         • acousticness close: 0.04 vs target 0.2 (+12.6)
         • valence close: 0.28 vs target 0.3 (+9.8)
         • tempo: 168.0 bpm vs target 140 bpm (+3.7)

  #4  Night Drive Loop  —  Neon Echo
       Score : 42.8 / 100
       Genre : synthwave  |  Mood: moody
       Why   :
         • genre mismatch: 'synthwave' vs 'hip-hop' (+0.0)
         • mood mismatch: 'moody' vs 'sad' (+0.0)
         • energy close: 0.75 vs target 0.93 (+16.4)
         • acousticness close: 0.22 vs target 0.2 (+14.7)
         • valence close: 0.49 vs target 0.3 (+8.1)
         • tempo: 110.0 bpm vs target 140 bpm (+3.6)

  #5  Gym Hero  —  Max Pulse
       Score : 42.7 / 100
       Genre : pop  |  Mood: intense
       Why   :
         • genre mismatch: 'pop' vs 'hip-hop' (+0.0)
         • mood mismatch: 'intense' vs 'sad' (+0.0)
         • energy close: 0.93 vs target 0.93 (+20.0)
         • acousticness close: 0.05 vs target 0.2 (+12.8)
         • valence far: 0.77 vs target 0.3 (+5.3)
         • tempo: 132.0 bpm vs target 140 bpm (+4.6)

============================================================
```

---

### Profile 5 — ADVERSARIAL: Dead Average (all numerics at 0.5)

```
============================================================
  PROFILE: ADVERSARIAL — Dead Average
============================================================
  genre       : ambient
  mood        : peaceful
  energy      : 0.5
  acousticness: 0.5
  valence     : 0.5
  tempo_bpm   : 114

  TOP 5 RECOMMENDATIONS
  --------------------------------------------------------

  #1  Spacewalk Thoughts  —  Orbit Bloom
       Score : 75.3 / 100
       Genre : ambient  |  Mood: chill
       Why   :
         • genre match: 'ambient' (+30.0)
         • mood compatible: 'chill' is in same group as 'peaceful' (+10.0)
         • energy close: 0.28 vs target 0.5 (+15.6)
         • acousticness far: 0.92 vs target 0.5 (+8.7)
         • valence close: 0.65 vs target 0.5 (+8.5)
         • tempo: 60.0 bpm vs target 114 bpm (+2.5)

  #2  Sunday Sonata  —  Elara Strings
       Score : 53.3 / 100
       Genre : classical  |  Mood: peaceful
       Why   :
         • genre mismatch: 'classical' vs 'ambient' (+0.0)
         • mood exact match: 'peaceful' (+20.0)
         • energy far: 0.22 vs target 0.5 (+14.4)
         • acousticness far: 0.95 vs target 0.5 (+8.2)
         • valence close: 0.72 vs target 0.5 (+7.8)
         • tempo: 68.0 bpm vs target 114 bpm (+2.9)

  #3  Midnight Coding  —  LoRoom
       Score : 53.0 / 100
       Genre : lofi  |  Mood: chill
       Why   :
         • genre mismatch: 'lofi' vs 'ambient' (+0.0)
         • mood compatible: 'chill' is in same group as 'peaceful' (+10.0)
         • energy close: 0.42 vs target 0.5 (+18.4)
         • acousticness close: 0.71 vs target 0.5 (+11.8)
         • valence close: 0.56 vs target 0.5 (+9.4)
         • tempo: 78.0 bpm vs target 114 bpm (+3.3)

  #4  Focus Flow  —  LoRoom
       Score : 51.3 / 100
       Genre : lofi  |  Mood: focused
       Why   :
         • genre mismatch: 'lofi' vs 'ambient' (+0.0)
         • mood compatible: 'focused' is in same group as 'peaceful' (+10.0)
         • energy close: 0.4 vs target 0.5 (+18.0)
         • acousticness far: 0.78 vs target 0.5 (+10.8)
         • valence close: 0.59 vs target 0.5 (+9.1)
         • tempo: 80.0 bpm vs target 114 bpm (+3.4)

  #5  Library Rain  —  Paper Lanterns
       Score : 48.7 / 100
       Genre : lofi  |  Mood: chill
       Why   :
         • genre mismatch: 'lofi' vs 'ambient' (+0.0)
         • mood compatible: 'chill' is in same group as 'peaceful' (+10.0)
         • energy close: 0.35 vs target 0.5 (+17.0)
         • acousticness far: 0.86 vs target 0.5 (+9.6)
         • valence close: 0.6 vs target 0.5 (+9.0)
         • tempo: 72.0 bpm vs target 114 bpm (+3.1)

============================================================
```

---

### Profile 6 — ADVERSARIAL: Genre Desert (only one country song exists)

```
============================================================
  PROFILE: ADVERSARIAL — Genre Desert (country)
============================================================
  genre       : country
  mood        : nostalgic
  energy      : 0.48
  acousticness: 0.72
  valence     : 0.68
  tempo_bpm   : 100

  TOP 5 RECOMMENDATIONS
  --------------------------------------------------------

  #1  Dust Roads Home  —  The Pines
       Score : 100.0 / 100
       Genre : country  |  Mood: nostalgic
       Why   :
         • genre match: 'country' (+30.0)
         • mood exact match: 'nostalgic' (+20.0)
         • energy close: 0.48 vs target 0.48 (+20.0)
         • acousticness close: 0.72 vs target 0.72 (+15.0)
         • valence close: 0.68 vs target 0.68 (+10.0)
         • tempo: 100.0 bpm vs target 100 bpm (+5.0)

  #2  Paper Boats  —  Hollow Fern
       Score : 51.0 / 100
       Genre : folk  |  Mood: melancholic
       Why   :
         • genre mismatch: 'folk' vs 'country' (+0.0)
         • mood compatible: 'melancholic' is in same group as 'nostalgic' (+10.0)
         • energy close: 0.31 vs target 0.48 (+16.6)
         • acousticness close: 0.88 vs target 0.72 (+12.6)
         • valence close: 0.44 vs target 0.68 (+7.6)
         • tempo: 82.0 bpm vs target 100 bpm (+4.2)

  #3  Broken Clocks  —  Gray Verse
       Score : 46.8 / 100
       Genre : hip-hop  |  Mood: sad
       Why   :
         • genre mismatch: 'hip-hop' vs 'country' (+0.0)
         • mood compatible: 'sad' is in same group as 'nostalgic' (+10.0)
         • energy close: 0.58 vs target 0.48 (+18.0)
         • acousticness far: 0.25 vs target 0.72 (+8.0)
         • valence far: 0.32 vs target 0.68 (+6.4)
         • tempo: 88.0 bpm vs target 100 bpm (+4.4)

  #4  Midnight Coding  —  LoRoom
       Score : 46.4 / 100
       Genre : lofi  |  Mood: chill
       Why   :
         • genre mismatch: 'lofi' vs 'country' (+0.0)
         • mood mismatch: 'chill' vs 'nostalgic' (+0.0)
         • energy close: 0.42 vs target 0.48 (+18.8)
         • acousticness close: 0.71 vs target 0.72 (+14.8)
         • valence close: 0.56 vs target 0.68 (+8.8)
         • tempo: 78.0 bpm vs target 100 bpm (+4.0)

  #5  Focus Flow  —  LoRoom
       Score : 45.7 / 100
       Genre : lofi  |  Mood: focused
       Why   :
         • genre mismatch: 'lofi' vs 'country' (+0.0)
         • mood mismatch: 'focused' vs 'nostalgic' (+0.0)
         • energy close: 0.4 vs target 0.48 (+18.4)
         • acousticness close: 0.78 vs target 0.72 (+14.1)
         • valence close: 0.59 vs target 0.68 (+9.1)
         • tempo: 80.0 bpm vs target 100 bpm (+4.1)

============================================================
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



