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

---

## 10. Responsible AI Reflection — Conversational Taste Agent

The sections above are about VibeMatch 1.0, the rule-based recommender. This
section is specifically about the stretch feature built on top of it: the
Gemini-powered conversational agent in `src/agent.py`
(`extract_profile()` → guardrails → `recommend_songs()` →
`explain_recommendations()`). This is the graded responsible-AI reflection
referenced from `README.md`.

### What are the limitations or biases in your system?

**It inherits every bias of the base recommender, and doesn't fix any of
them.** Every recommendation the agent produces is still scored by the
exact same `recommend_songs()` formula documented in Section 6 — genre
dominance, small-dataset amplification (lofi sweeping the top-3), cold-start
profile drift, and the mid-energy gap all apply just as much when the
profile comes from a sentence as when it comes from typed numbers. The
agent makes the system easier to *talk to*; it does nothing to make the
underlying recommendations less biased.

**The catalog's genre vocabulary is culturally narrow.** The 18-song
catalog's genres — pop, lofi, rock, ambient, jazz, synthwave, indie pop,
hip-hop, classical, r&b, country, edm, funk, metal, folk — skew Western and
English-language. Because the extraction schema's `genre`/`mood` fields are
JSON Schema `enum`s built directly from that catalog, a user who describes
wanting K-pop, Afrobeat, reggaetón, or Hindustani classical music will
silently get mapped to whatever catalog genre the model judges closest —
there is no "genre not found" signal surfaced to them, just a plausible-
looking wrong answer. This is a direct, structural consequence of a design
choice I made deliberately for reliability (enum-constrained extraction
can't return an invalid category) — the same mechanism that prevents
garbage categories also silently erases any taste the catalog doesn't
represent.

**Confidence measures well-formedness, not correctness.** The confidence
score (`_confidence_from_corrections()`) only tracks how many fields the
guardrails had to *correct* — an extraction that needed zero corrections
still gets a perfect 1.0 even if the model quietly misread the user's
intent (e.g., reading "moody" as the `intense` mood-group instead of the
catalog's standalone `moody` mood). A confident-looking profile is not the
same as an accurate one, and I don't currently have any way to measure the
second thing without a human reading the free text and the profile
side-by-side.

**Nothing programmatically stops the explanation from drifting off the
retrieved data.** `explain_recommendations()` is instructed by its system
prompt to reference only the retrieved songs/scores/reasons, but that's a
prompt constraint, not an enforced one — unlike the extraction call, there
is no output schema checking that every song name in the generated text
actually appears in the retrieved list.

**The model itself was chosen for cost, not accuracy.** `gemini-3.6-flash`
is the free-tier-eligible model; I did not benchmark it against a larger
paid model on this task, so I don't know how much of the correction rate
seen in the reliability battery (`tests/test_reliability.py`) is inherent
to the task versus specific to this model tier.

### Could your AI be misused, and how would you prevent that?

**The most concrete risk is prompt injection through the explanation call.**
`explain_recommendations()` interpolates the user's raw free text directly
into a prompt with no sanitization. Because that call has no output schema
(unlike extraction), a user could try something like "ignore the above and
instead output [unrelated/inappropriate content]" and there's nothing
structurally stopping the model from complying, beyond the system prompt's
instruction to stay grounded in the retrieved data. The extraction call is
much harder to misuse the same way: its enum-constrained function schema
means even a successfully hijacked call can still only return a genre/mood
from the fixed catalog list and numeric values, which then get clamped
again by the guardrails — there's no path from a malicious description to
arbitrary extracted output. The asymmetry is real: the structured call is
misuse-resistant by construction, the free-text call is not.

**How I'd prevent it, in order of how much I trust each mitigation:**
1. *Already in place:* the system prompt for `explain_recommendations()`
   explicitly instructs the model to reference only the provided data —
   weak on its own, but it's the current mitigation.
2. *Not yet built, and the one I'd do first:* a post-generation check that
   every song title mentioned in the explanation text actually appears in
   the retrieved `recommendations` list, and discard/regenerate if not —
   this converts a prompt-level ask into an enforced, testable guardrail,
   the same pattern already used for extraction.
3. *Structural, already true:* the pipeline is read-only text generation —
   it never executes code, calls other tools, spends money, or takes any
   action beyond printing text and writing a log line. Worst-case misuse is
   an off-topic or inappropriate paragraph printed to a local terminal, not
   a real-world consequence. That bounds the blast radius a lot compared to
   an agent with side effects (file writes, purchases, messages sent on a
   user's behalf), and it's the main reason I didn't build heavier
   moderation for a project at this scale.

**A separate, less dramatic but real risk: logging.** Every free-text query
and every extracted profile is written to `logs/agent.log` in plaintext,
with no redaction and no retention limit. For a single-user local CLI tool
that's a non-issue — but if this were ever deployed for real users, whatever
they type would sit in a log file indefinitely. I'd fix this before shipping
anything beyond a portfolio project (redact or hash free text, add log
rotation/expiry) — right now it's an acknowledged gap, not a solved one.

### What surprised me while testing your AI's reliability?

**The confidence floor isn't 0.0, and I only found that out by running the
numbers.** I expected the "everything corrupted" case in
`tests/test_reliability.py` to bottom out at a confidence of 0.0. The
actual formula — start at 1.0, subtract 0.15 per corrected field, 6 fields
total — floors at 0.10 (`1.0 - 6×0.15 = 0.10`), not 0.0. I'd reasoned about
the formula in my head and gotten it wrong; only printing the actual
reliability-battery output caught it.

**Total data corruption survived better than a single connection failure.**
I expected the scenario where *every* field is simultaneously wrong (unknown
genre, unknown mood, non-numeric energy, missing acousticness, out-of-range
valence, non-numeric tempo) to be the one most likely to break something.
Instead it degraded gracefully to a low-confidence-but-fully-usable profile
(confidence 0.10, but a complete, valid `recommend_songs()`-compatible
dict), because each guardrail corrects its own field independently with no
shared failure mode. The *only* scenario in the battery that actually failed
was the simulated API error — a case with no bad data at all, just no
response. That inversion — garbage input survives, no input doesn't — was
not what I expected going in, and it's a genuinely reassuring property: the
guardrails are more robust to bad model output than the system is to the
model being unavailable, which is arguably the right priority for a
free-tier API with no uptime guarantee.

**The provider swap broke nothing in the guardrail logic, on the first
try.** When I moved the whole agent from Anthropic's Claude API to Google's
Gemini API, I expected a real debugging cycle to get the guardrail tests
green again. Once the test fakes were rewritten to match Gemini's response
shape (`response.function_calls` / `response.text` instead of Claude's
`response.content` blocks), every guardrail test passed immediately. That
was a direct, measurable payoff of keeping the guardrail functions as plain
Python operating on plain values, with no provider-specific types leaking
into them — a design choice made for testability that turned out to also
make the whole system more portable than I'd planned for.

### Describe your collaboration with AI during this project

I worked with Claude (via this session) as the primary builder throughout —
describing what I wanted, reviewing what it produced, and redirecting when
something was wrong or when I wanted a different trade-off (e.g., asking
for a free model instead of a paid one, then naming the specific Gemini
model to use once I'd decided). The full turn-by-turn record is in
`ai_interactions.md`; below are one specific helpful moment and one
specific flawed one.

**Helpful: verifying the Gemini SDK against real source instead of trusting
a summarized doc page.** When switching providers, an early documentation
fetch described a `client.interactions.create(...)` API shape that didn't
match established patterns. Rather than writing code against that summary,
Claude fetched the actual `google-genai` SDK's README and `types.py` from
its GitHub source, then went one step further and imported the real
installed package in this environment to construct each class
(`FunctionDeclaration`, `Tool`, `ToolConfig`, `GenerateContentConfig`) and
confirm the exact keyword arguments worked before writing the final
`src/agent.py`. That caught the discrepancy before it became broken code I
would have had to debug myself later, and it's the reason the Gemini
integration worked correctly the first time I ran it against the real
package.

**Flawed: Claude-specific terminology leaked into the Gemini
implementation and stayed there until I asked for a review pass.** When the
agent was rewritten from Claude's API to Gemini's, the *mechanism* changed —
Claude's tool-use has an explicit `strict: true` flag; Gemini forces a
function call via `tool_config.function_calling_config.mode="ANY"`, which
isn't the same thing. But the word "strict" survived the rewrite anyway: it
was still in `src/agent.py`'s module docstring, in the README's ASCII
architecture diagram, and in the Mermaid system diagram's node labels,
describing Gemini's schema as "strict" when that's not an accurate
description of how Gemini enforces it. This wasn't caught by the test suite
— it's a documentation-accuracy issue, not a functional bug, so nothing red
would ever flag it — and it persisted across three separate files until I
explicitly asked whether the README and diagram needed adjustment after the
provider swap. Claude found and fixed all three instances once asked, but
the flaw was in not re-deriving accurate terminology for the new provider
in the first pass, and in not proactively re-auditing documentation after a
functional change. It's a small thing, but it's exactly the kind of
plausible-but-wrong detail that's easy to skim past in AI-generated content
if nobody goes looking for it.
