# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeMatch 1.0**

A content-based music recommender that scores songs against a user's taste profile and returns the best matches with a plain-language explanation for each pick.

---

## 2. Intended Use

**What it is for:**
VibeMatch is designed to suggest songs a single user would enjoy based on their stated preferences for genre, mood, and audio features like energy and acousticness. It is built for classroom exploration — the goal is to make every step of the recommendation process visible and understandable, not to power a real app.

**What it is NOT for:**
- It should not be used as a real music recommendation product. The catalog is too small (18 songs) to serve actual listeners.
- It should not be used to judge whether a song is "good." It only measures fit to one specific profile.
- It should not be used with users who cannot describe their taste in numeric terms. It has no way to learn preferences from listening history.
- It should not be treated as fair or unbiased. Several known gaps exist in the catalog and scoring logic (see Limitations).

---

## 3. How the Model Works

Each song in the catalog gets a score out of 100 by comparing it to the user's preference profile feature by feature.

**Genre (30 points):** If the song's genre exactly matches the user's preferred genre, it earns the full 30 points. If not, it gets zero. Genre carries the most weight because it is the strongest signal of long-term taste.

**Mood (20 points):** An exact mood match earns 20 points. If the song's mood is in the same family as the user's preferred mood — for example, "focused" is in the same family as "chill" — it earns 10 points instead of zero. A completely different mood earns nothing.

**Energy (20 points):** Energy is a number from 0 to 1. The closer the song's energy is to the user's target, the more points it earns. A perfect match earns 20 points. A song that is 0.5 away earns 10. This rewards closeness, not just having high or low energy.

**Acousticness (15 points):** Same idea as energy — proximity to the user's target earns partial credit up to 15 points.

**Valence (10 points):** Valence measures how positive or cheerful a song feels. Closer to the user's preference earns more of the 10 available points.

**Tempo (5 points):** Tempo in BPM is normalized to a 0–1 scale before comparing, so a fast song and a slow song are fairly penalized regardless of raw BPM difference.

Songs are sorted by total score from highest to lowest. The top 5 are returned along with a breakdown of exactly how many points each feature contributed.

---

## 4. Data

The catalog contains **18 songs** stored in a CSV file with 10 columns per song: id, title, artist, genre, mood, energy, tempo\_bpm, valence, danceability, and acousticness.

**Genres covered (15 total):** lofi, pop, rock, ambient, jazz, synthwave, indie pop, hip-hop, classical, r&b, country, edm, funk, metal, folk.

**Moods covered (14 total):** chill, happy, intense, moody, relaxed, focused, sad, peaceful, romantic, nostalgic, energetic, upbeat, angry, melancholic.

**Known gaps in the data:**
- Lofi has 3 songs; pop has 2; every other genre has exactly 1. This means lofi dominates fallback recommendations for any low-energy user.
- Only 2 songs fall in the mid-energy range of 0.50–0.74. Users who prefer medium-intensity music are poorly served.
- No lyrics, audio waveforms, artist popularity, release year, or listening history are included. The system only sees the numeric and categorical features in the CSV.
- The 18 songs were hand-picked for variety, not sampled from real listening data, so the distribution does not reflect what real listeners actually play.

---

## 5. Strengths

**Works well for clear, consistent taste profiles.** A user who strongly prefers lofi/chill music gets a tight cluster of matching songs near 90–98 points, and the results feel intuitively correct.

**Every recommendation is explainable.** The output shows exactly which features matched and how many points each one contributed. A user can always see why a song ranked where it did.

**Partial mood credit reduces harsh penalties.** The mood group system means a "focused" user is not treated the same as an "angry" user when both are compared to a "chill" preference. Adjacent moods earn half credit instead of zero.

**Adversarial profiles fail gracefully.** When given conflicting or ambiguous preferences, the system still returns a ranked list. It does not crash. The ranking degrades sensibly toward genre and mood matching when numeric features provide weak signal.

**Perfect matches score 100.** When a catalog song was seeded to exactly match a profile (Storm Runner for the rock profile, Dust Roads Home for the country profile), the system correctly returns a perfect score, confirming the formula is working as designed.

---

## 6. Limitations and Bias

Where the system struggles or behaves unfairly.

Prompts:

- Features it does not consider
- Genres or moods that are underrepresented
- Cases where the system overfits to one preference
- Ways the scoring might unintentionally favor some users

**Discovered weakness — Mid-energy users are systematically underserved (bimodal energy gap).**
The catalog's 18 songs split into two tight clusters: 8 songs with energy below 0.50 (lofi, ambient, classical, folk) and 8 songs above 0.74 (pop, rock, edm, metal), with only 2 songs in the entire 0.50–0.74 mid-energy range — hip-hop at 0.58 and r&b at 0.55.
A user who prefers mid-energy music, such as someone who enjoys mellow indie rock or relaxed electronic, will find that nearly every song in the catalog sits far from their target energy value, so the energy proximity score provides almost no meaningful signal and the system silently collapses into ranking by genre and mood alone.
This creates a hidden filter bubble: mid-energy users do not receive an error or warning — they simply get recommendations that feel "close enough" on genre but consistently wrong in feel, and because the scoring formula never reports how badly a numeric feature missed, neither the user nor a developer inspecting the output would immediately notice the problem.
The underlying cause is a dataset design bias, not a flaw in the formula itself: when the catalog was built, low-energy chill genres and high-energy intense genres were added first, leaving the middle of the energy spectrum nearly empty, which means any scoring system trained or tuned on this data will inherit the same blind spot.

---

## 7. Evaluation

Six user profiles were tested: three standard profiles designed to represent clearly defined listener types (High-Energy Pop, Chill Lofi, Deep Intense Rock) and three adversarial profiles designed to expose edge cases in the scoring logic (High-Energy Sad, Dead Average, and Genre Desert).

---

### Profile 1 vs. Profile 2 — High-Energy Pop vs. Chill Lofi

These two profiles sit at opposite ends of nearly every numeric dimension: Pop targets energy 0.85 and acousticness 0.12, while Lofi targets energy 0.39 and acousticness 0.78. As expected, their top-5 lists share zero songs. The Pop profile surfaces bright, fast tracks (Sunrise City 97.8 pts, Gym Hero 76.7 pts), while the Lofi profile surfaces quiet, textured tracks (Midnight Coding 98.1 pts, Library Rain 97.6 pts). What makes sense: these profiles are the clearest possible contrast in musical feel, so the scoring formula correctly sends them to opposite ends of the catalog. What was surprising: Rooftop Lights (indie pop, not pop) ranked #3 for the Pop profile purely because its mood ("happy") and energy (0.76) were close enough to compensate for the genre mismatch — showing that mood can act as a partial substitute for genre when the numeric features align well.

---

### Profile 2 vs. Profile 3 — Chill Lofi vs. Deep Intense Rock

Both profiles have strong genre and mood signals, but they differ sharply on energy (0.39 vs. 0.91) and acousticness (0.78 vs. 0.10). The Lofi profile's top 3 are all lofi songs scoring 89–98 pts; the Rock profile's #1, Storm Runner, scored a perfect 100 because it matched every single feature exactly. What makes sense: when a catalog contains a song that was deliberately seeded to match a profile perfectly, the scoring formula should return a near-perfect score — and it does. What was surprising: the Rock profile's fallback songs (#2–5) were Gym Hero (pop), Iron Curtain (metal), Grid Collapse (EDM), and Night Drive Loop (synthwave) — no second rock song existed, so the system correctly pivoted to "intense/energetic mood + low acousticness + high energy" as the shared signal, which is exactly the right fallback behavior.

---

### Profile 3 vs. Profile 4 — Deep Intense Rock vs. High-Energy Sad (adversarial)

Both profiles request high energy (0.91 and 0.93 respectively), but their moods point in opposite directions — intense vs. sad. Rock's top songs are hard-edged and fast; Sad's #1 is Broken Clocks (hip-hop) at 89.6 pts, which matched on genre and mood but only scored 13.0 energy points because its energy (0.58) is far from the target (0.93). What makes sense: genre and mood together are worth 50 pts, so a categorical double-match dominates even when the numeric features are a poor fit. What was surprising: positions #2–5 for the High-Energy Sad profile were completely wrong-mood songs (rock, metal, synthwave, pop) that ranked purely on energy proximity — there are simply no other sad songs with high energy in the catalog, exposing the bimodal energy gap described in the Limitations section. The system did not crash or warn; it silently surfaced intense songs for a user who asked for sad ones.

---

### Profile 4 vs. Profile 5 — High-Energy Sad vs. Dead Average (adversarial)

High-Energy Sad has a sharp, conflicting signal (high energy + low valence + sad mood). Dead Average deliberately flattens all numeric preferences to 0.5, which sits in the catalog's energy dead zone. The Sad profile still produced a clear #1 winner (Broken Clocks, 89.6 pts) because genre and mood matched exactly. The Dead Average profile's #1, Spacewalk Thoughts, scored only 75.3 pts — a noticeably lower ceiling — and positions #2–5 were tightly bunched between 48–53 pts with no clear winner. What makes sense: when numeric preferences are ambiguous, the scoring degrades to a genre/mood sorter, which is exactly what happened. What was surprising: three lofi songs (Midnight Coding, Focus Flow, Library Rain) appeared in the Dead Average top 5 even though the user asked for ambient/peaceful — the lofi genre's over-representation in the catalog (3 songs vs. 1 for every other genre) caused it to dominate the fallback rankings by sheer volume.

---

### Profile 5 vs. Profile 6 — Dead Average vs. Genre Desert (adversarial)

Both profiles expose catalog sparsity, but in different ways. Dead Average suffers from numeric ambiguity; Genre Desert (country) suffers from having only one matching song in the entire catalog. The country profile's #1 (Dust Roads Home) scored a perfect 100.0 pts, but #2 dropped to 51.0 pts — a 49-point cliff. By contrast, Dead Average's scores were compressed in a narrow band (48–75 pts) with no such cliff. What makes sense: a perfect catalog match always wins by a large margin when every other song must earn its points through numeric similarity alone. What was surprising: after the one country song, the Genre Desert fallback list was dominated by lofi songs (Midnight Coding #4, Focus Flow #5) — not because lofi sounds like country, but because lofi's high acousticness and low energy happen to be numerically close to country's acoustic, mid-tempo profile. This is an example of numeric coincidence masquerading as a meaningful recommendation.

---

## 8. Future Work

**1. Add a diversity rule.**
Right now nothing stops the top 5 from being all lofi songs for a lofi user. A simple fix: after scoring, limit the results to at most 2 songs per genre. This would force the system to surface adjacent genres instead of repeating the same one.

**2. Fill the mid-energy gap.**
Add 6–8 songs with energy values between 0.50 and 0.74. Good candidates: mellow indie rock, downtempo electronic, acoustic soul. This would give mid-energy users meaningful numeric signal instead of forcing the system to fall back on genre/mood alone.

**3. Build an automatic profile builder.**
Right now the user has to supply target values manually. A better approach: let the user "like" 3–5 songs, then automatically compute the average of each numeric feature and the most common genre and mood. This mirrors how real apps like Spotify Discover Weekly actually build taste profiles from listening history.

---

## 9. Personal Reflection

**Biggest learning moment**

The biggest learning moment was discovering the bimodal energy gap through actual output — not by reading about it, but by running the Dead Average adversarial profile and watching the scores bunch together with no clear winner. I had designed the scoring formula carefully, but I had not thought hard enough about the data underneath it. Seeing the system silently degrade instead of failing loudly taught me that data quality is not a detail you handle after building the algorithm. It is the first thing you have to get right. A good formula on bad data still gives bad recommendations.

**How AI tools helped — and when I needed to double-check them**

AI tools helped me move fast on parts that would have been slow to figure out alone: structuring the algorithm recipe, thinking through the mood group fix, writing the proximity formula, and catching the import path bug when switching from `python src/main.py` to `python -m src.main`. The suggestions were almost always directionally correct, but I still needed to verify the actual point values added up to 100, check that the CSV types were being cast correctly, and run each profile manually to confirm the output matched the reasoning. The most important double-check was the weight-shift experiment: the AI described what would change, but I had to actually run it and read the ranked lists to feel whether the change made recommendations better or just different. That judgment could not be delegated.

**What surprised me about simple algorithms feeling like recommendations**

The most surprising thing was how quickly a formula with six rules started feeling like it "knew" something. When Sunrise City scored 97.8 for the pop/happy profile, or when Storm Runner hit a perfect 100 for the rock/intense profile, the output felt correct in a way that was almost intuitive. But the formula has no understanding at all — it is just subtraction and multiplication. What makes it feel smart is that the features were chosen to carry real meaning. Energy, mood, and genre are things humans actually use to describe music, so matching on them produces results that match human intuition. The algorithm does not understand music. It mirrors the categories we already use to think about it.

**What I would try next**

If I extended this project, the first thing I would build is an automatic profile generator that takes a list of liked songs and computes the user's targets by averaging their features — so the user never has to type a number like "energy: 0.39" by hand. After that I would add a diversity constraint so the top 5 always spans at least three different genres, which would force the system to recommend across genre boundaries instead of clustering inside one. The most ambitious extension would be adding a second scoring pass using collaborative filtering: find other users whose liked songs overlap with yours, then surface songs they loved that you have not heard yet. That is the step that turns a content matcher into something that can actually surprise you.
