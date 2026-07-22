# 🎵 VibeMatch — Music Recommender Simulation + Conversational Taste Agent

A transparent, content-based music recommender extended with a real, guardrailed
AI agent: describe your mood in plain English and get scored, explained
recommendations — no numeric preference sliders required.

---

## Original Project

This repository started from CodePath's **`module3show-musicrecommendersimulation-starter`**
(Public) starter template. The original assignment's goal was to build and
explain a small music recommender: represent songs and a listener's "taste
profile" as data, design a transparent scoring rule that turns that data into
ranked recommendations, evaluate what the system gets right and wrong, and
reflect on how that mirrors real-world recommenders like Spotify. The starter
shipped a song catalog (`data/songs.csv`), empty `Song`/`UserProfile`/scoring
function stubs to fill in, and a starter test file — the core content-based
scoring engine in [`src/recommender.py`](src/recommender.py) is my completed
implementation of that assignment.

This README documents what I built **on top of** that starter: a Google
Gemini-API-powered conversational agent layer (`src/agent.py`) that sits in
front of the original scoring engine.

---

## Summary

**What it does:** VibeMatch scores an 18-song catalog against a listener's
taste profile using a transparent, hand-tunable weighted formula (genre, mood,
energy, acousticness, valence, tempo), and returns the top matches with a
plain-language, feature-by-feature explanation for every score. On top of
that deterministic core sits a conversational agent: type a free-text
description of what you want to hear, and an LLM-driven pipeline extracts a
structured taste profile, validates it, runs it through the *same* scoring
engine, and writes an explanation grounded in the real, computed results.

**Why it matters:** most "AI recommends X" demos either hide a black box
behind a chat interface, or bolt an LLM onto a system without changing how
it actually decides anything. This project deliberately does neither: the
scoring logic is 100% inspectable arithmetic (no embeddings, no hidden
model), and the one place an LLM *is* used is wrapped in guardrails — a
schema that makes invalid categories structurally impossible, numeric
clamping, retry-with-backoff, and fail-closed error handling — so the
non-deterministic part of the system can never silently corrupt the
deterministic part. That combination (explainable core + guarded AI layer)
is the pattern I wanted to practice, because it's the same tension every
real product team hits when they add an LLM feature to an existing system.

---

## Architecture Overview

Full system diagram (validated by actually rendering it, not just written
by hand): **[`diagrams/agent_architecture.md`](diagrams/agent_architecture.md)**.

The system has two layers:

1. **Deterministic core** (`src/recommender.py`, from the original
   assignment) — `load_songs()` reads the catalog, `score_song()` scores one
   song against a profile dict with a fixed weighted formula, and
   `recommend_songs()` scores every song and returns the top-k. No AI
   involved; fully unit-testable; identical output every run.
2. **Agentic layer** (`src/agent.py`, my extension) — a 4-step pipeline that
   sits in front of the core and never bypasses it:

   ```
   free-text input
        │
        ▼
   🤖 PLAN    extract_profile()       — Gemini call #1, forced enum-constrained
        │                                function schema built from the live catalog
        ▼
   🛡️ CHECK   guardrails              — clamp numerics, fall back unknown
        │                                categories, retry transient errors,
        │                                fail closed on non-retryable ones,
        │                                compute a confidence score from how
        │                                many corrections were needed
        ▼
   🔎 ACT     recommend_songs()       — the same deterministic scoring engine
        │                                the base demo uses (data/songs.csv)
        ▼
   🤖 EXPLAIN explain_recommendations() — Gemini call #2, prompt is grounded in
        │                                the actual scored results, instructed
        │                                to reference only that data
        ▼
   ranked recommendations + explanation → user
   ```

   Every step writes to `logs/agent.log`, including the confidence score for
   every extraction. A separate offline path (`tests/test_agent.py` and
   `tests/test_reliability.py`) exercises the guardrail logic and the
   confidence-scoring math against a scripted stand-in for the Gemini
   client, so reliability can be measured and verified without burning API
   quota or requiring network access — see
   [Testing Summary](#testing-summary) for the real numbers.

   **Why Gemini instead of a paid API:** the goal was for anyone cloning this
   repo to be able to run the full agent with zero cost and zero billing
   setup. Google AI Studio issues a free API key (no credit card) with a
   generous free-tier quota on the Flash model family, which is what
   `src/agent.py` targets by default (`gemini-3.6-flash`, overridable via
   `GEMINI_MODEL`).

---

## Setup Instructions

```bash
# 1. Clone and enter the repo
git clone <this-repo-url>
cd applied-ai-system-final

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the base recommender demo (no API key needed, no network calls)
python -m src.main
```

That last command scores six fixed taste profiles (three standard, three
adversarial edge cases) against the catalog and prints ranked, explained
results — see [Execution Evidence](#execution-evidence) for 2 of them in
full, or [Appendix A](#appendix-a-base-recommender-sample-output) for all six.

### Enable the conversational agent

```bash
# 5. Get a FREE API key (no credit card, no billing setup) at
#    https://aistudio.google.com/apikey, then export it
export GEMINI_API_KEY=“YOUR_API_KEY_HERE"

# 6. Run the interactive agent (google-genai is already in requirements.txt)
python -m src.main --chat
```

Type a description of what you want to hear; type `quit` to exit. If
`GEMINI_API_KEY` isn't set, `--chat` prints a clear setup message instead
of crashing — see [Design Decisions](#design-decisions).

### Run the tests

```bash
pytest
```

19 tests, no API key or network access required (the agent tests use a
scripted stand-in client — see [Testing Summary](#testing-summary)).

---

## Execution Evidence

Everything in this section was captured by actually running this codebase —
none of it is hand-written or hypothetical. It's split into exactly the
three things a reader needs to see to trust that this system works:

- ✅ **End-to-end system run** — 2 real invocations of the deterministic core
- ✅ **AI feature behavior** — 3 real invocations of the Gemini-powered agent
- ✅ **Reliability / guardrail behavior** — guardrails correcting bad input,
  a 6-scenario reliability battery, and the fail-closed error path

Every case below shows the exact command, the input, and the resulting
output, so it's reproducible by running the same command yourself.

### ✅ End-to-end system run (base recommender — 2 inputs)

Command:

```bash
python -m src.main
```

This loads the 18-song catalog and scores it against 6 fixed taste
profiles; the two below are copied verbatim from a real run (all six, plus
the underlying algorithm's data-flow docs, are in
[Appendix A](#appendix-a-base-recommender-sample-output)).

**Input 1 — High-Energy Pop** (`genre=pop, mood=happy, energy=0.85, ...`)

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

**Input 2 — Chill Lofi** (`genre=lofi, mood=chill, energy=0.39, ...`)

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

**Output summary:** both inputs produce a fully ranked, fully explained
top-5 list with a numeric score (0–100) and a feature-by-feature
justification for every song — the "Why" lines above are not templated
text, they're the literal points awarded by `score_song()` for that
specific song/profile pair, which is why they differ line to line.

### ✅ AI feature behavior (conversational agent — 3 inputs)

The three transcripts below were captured by actually **running the
production pipeline** (`run_agentic_recommendation()` in `src/agent.py`,
unmodified) end-to-end. Because this environment doesn't have a live
`GEMINI_API_KEY` configured, the Gemini *client* was swapped for a scripted
stand-in that returns fixed, representative responses in the same shape the
real `google-genai` SDK returns (`response.function_calls`, `response.text`)
— everything downstream of that response (schema validation, clamping,
retrieval against the real catalog, scoring, output formatting) is the exact
real code path. This is called out explicitly rather than presented as a
live run, in the interest of not overclaiming what was tested. With a real
free API key exported as `GEMINI_API_KEY`, `python -m src.main --chat`
produces the same shape of output against live model responses.

Command (once `GEMINI_API_KEY` is set):

```bash
python -m src.main --chat
```

#### Example 1 — clean extraction

```
> I want something low-key and moody for a rainy afternoon of reading

Derived taste profile:
  genre       : ambient
  mood        : chill
  energy      : 0.3
  acousticness: 0.85
  valence     : 0.4
  tempo_bpm   : 65.0

Top picks:
  #1  Spacewalk Thoughts — Orbit Bloom  (95.8/100)
  #2  Library Rain — Paper Lanterns  (66.5/100)
  #3  Midnight Coding — LoRoom  (63.3/100)
  #4  Focus Flow — LoRoom  (54.4/100)
  #5  Sunday Sonata — Elara Strings  (53.6/100)

Why:
  Spacewalk Thoughts is your top pick because it's an exact genre match
  (ambient) with a low, rainy-day energy of 0.28 and very high acousticness
  of 0.92, close to what you described. Sunday Sonata follows with a
  compatible chill-family mood even though its genre (classical) doesn't
  match exactly.
```

#### Example 2 — guardrails firing on a messy extraction

The scripted model response here deliberately returns an out-of-catalog
genre (`"death metal"` — the catalog has no such genre) and an out-of-range
energy value (`1.4`, outside `[0, 1]`) and tempo (`300` bpm), to demonstrate
the guardrail layer actually correcting bad values before they reach the
scoring engine, instead of just being designed to:

```
> something loud and aggressive, I don't care what genre

Derived taste profile:
  genre       : lofi          # "death metal" isn't in the catalog → fell back
  mood        : intense
  energy      : 1.0           # clamped from 1.4
  acousticness: 0.05
  valence     : 0.4
  tempo_bpm   : 220.0         # clamped from 300

Top picks:
  #1  Storm Runner — Voltline  (63.5/100)
  #2  Gym Hero — Max Pulse  (60.8/100)
  #3  Iron Curtain — Wraith Engine  (55.6/100)
  #4  Grid Collapse — Bass Architect  (51.5/100)
  #5  Midnight Coding — LoRoom  (50.3/100)

Why:
  Iron Curtain is the closest match to 'loud and aggressive' in the catalog,
  with a near-maximum energy of 0.97 and very low acousticness of 0.04,
  matching the intense mood you described.
```

`logs/agent.log` records each correction:
```
[WARNING] Guardrail: 'genre'='death metal' is outside the known catalog values; falling back to 'lofi'
[WARNING] Guardrail: 'energy'=1.4 out of [0,1]; clamped to 1.0
[WARNING] Guardrail: tempo_bpm=300.0 out of [40,220]; clamped to 220.0
```

#### Example 3 — failing closed instead of crashing

```
> asdkfjhasdkjfh???

[!] Could not understand that description -- try describing genre/mood more directly.
```

(Here the scripted client raises an error to simulate a malformed/failed API
response. `run_agentic_recommendation()` catches it, logs it, and returns a
user-facing message — the process never crashes and never silently invents a
default profile.)

### ✅ Reliability / guardrail behavior

Two kinds of evidence: guardrails firing on a live-shaped request (Example 2
above already shows this — an out-of-catalog genre and two out-of-range
numbers get corrected before scoring, and the correction is logged), and a
dedicated automated battery that measures it systematically.

Command:

```bash
pytest tests/test_reliability.py -v -s
```

`tests/test_reliability.py` runs `extract_profile()` through 6 scripted
inputs spanning a clean response to a simulated unrecoverable API failure.
The output below is copied verbatim from an actual run — not written by hand:

```
--- Reliability summary: 5/6 extractions succeeded ---
  - clean extraction -- all fields valid: OK (confidence=1.00)
  - one out-of-range numeric field (energy=1.4): OK (confidence=0.85)
  - one unknown category (genre='death metal'): OK (confidence=0.85)
  - three bad fields (genre, energy, tempo): OK (confidence=0.55)
  - all six fields malformed or missing: OK (confidence=0.10)
  - unrecoverable API failure (simulated): FAILED CLOSED (no profile returned)
Average confidence across successful extractions: 0.67
```

**Reading the result:** 5 of 6 scenarios succeeded and returned a usable,
scored profile; the 1 failure was a simulated unrecoverable API error, and
the system correctly *failed closed* — returning no profile and a clear
error message — instead of guessing one. That's the intended behavior
(pinned by `test_reliability_battery_fails_closed_on_error`), not a bug.
Confidence across the 5 successes ranged from 1.00 (clean input) down to
0.10 (every field corrupted), averaging 0.67, tracking guardrail-correction
load exactly as designed — see [Testing Summary](#testing-summary) for how
the confidence score itself is computed and what it does/doesn't measure.

---

## Design Decisions

- **Rule-based scoring core, not an ML model.** The base recommender is a
  hand-weighted formula, not a trained model or embeddings — every point in
  a song's score is traceable to one line of arithmetic. Trade-off: it
  can't learn from data or generalize past its six hand-tuned features, but
  for a system meant to be *explained*, an inspectable formula beats a more
  "accurate" black box.

- **The LLM extracts structure; it never scores.** I could have asked
  Gemini to just recommend songs directly from the catalog and a text
  description. I deliberately didn't: the LLM's only job is turning free
  text into a structured profile and turning results back into prose. The
  actual ranking always goes through the same deterministic
  `recommend_songs()` the static demo uses. Trade-off: this means the agent
  can only be as good as the underlying scoring formula's biases (see
  `model_card.md` for those) — it doesn't fix them, it just adds a friendlier
  front door.

- **Guardrails via schema, not via prompting.** The extraction function's
  `genre`/`mood` parameters are JSON Schema `enum`s built from the live
  catalog at call time, and `tool_config` forces the model to call that
  function (`function_calling_config.mode="ANY"`). This makes an invalid
  category a structural impossibility rather than something to catch after
  the fact with "please only use one of these values" prompt text, which
  models can and do ignore under adversarial or ambiguous input. Numeric
  fields *are* still clamped client-side, because JSON Schema can't express
  `minimum`/`maximum` in this API either — that's a known gap I closed with
  plain Python instead of pretending the schema covers it.

- **Two separate Gemini calls instead of one.** Extraction and explanation
  are two calls, not one combined prompt. Trade-off: strictly more latency
  and token cost than a single call (a real cost even on a free tier, since
  free-tier quotas are rate-limited per minute). I chose it anyway because
  it keeps the boundary between "turn text into structured data" (which must
  be strictly validated) and "turn results into prose" (which must be
  grounded in already-verified data) enforceable in code, not just in a
  prompt. It also means each half can be tested and logged independently.

- **Google Gemini over a paid API.** The agent originally targeted
  Anthropic's Claude API. I switched providers specifically so this repo
  runs on a genuinely free tier — Google AI Studio issues an API key with no
  credit card and a real (if rate-limited) free quota, where most
  competitors either require billing to be enabled or gate free usage behind
  a trial period. The trade-off is real: switching providers meant
  re-verifying every piece of SDK syntax (client construction, function-
  calling schema shape, response parsing, exception types) against Gemini's
  actual behavior instead of reusing what I already had working, and the
  two providers are not perfectly interchangeable (Gemini's forced-tool-call
  mechanism is `tool_config.function_calling_config.mode="ANY"` rather than
  naming a specific tool the way Claude's `tool_choice` does — with only one
  tool declared here, the effect is the same).

- **Fail closed, not fail soft.** If extraction can't produce a usable
  profile after retries, the pipeline returns an error message rather than
  falling back to a guessed or default profile. A recommender that silently
  returns *something* for un-parseable input is worse than one that says
  "I couldn't understand that" — a wrong-but-confident recommendation is a
  worse user experience than an honest failure.

- **File+console logging over no logging.** Every extraction, guardrail
  correction, retry, and failure is logged to `logs/agent.log`. For a
  project this size that's arguably more logging than strictly necessary,
  but it's what made Example 2 above possible to write honestly (I could
  point at the actual log lines instead of describing what the guardrails
  "should" do).

---

## Testing Summary

This project proves reliability three ways, not just by claiming it: **automated
tests** (19 tests, `pytest`), a **confidence score** the agent computes for every
extraction, and **logging** of every guardrail decision to `logs/agent.log`.

### Confidence scoring

`extract_profile()` doesn't just return a taste profile — it returns a
`confidence` score (0.0–1.0) alongside it. This is *not* a self-reported
model probability (Gemini's function-calling API doesn't expose one); it's a
transparent, deterministic measure computed in `src/agent.py`
(`_confidence_from_corrections()`): start at 1.0, subtract 0.15 for every
field the guardrails had to correct (an out-of-catalog genre/mood, or a
numeric value outside its valid range). Zero corrections → 1.0. Every field
wrong → 0.10. It's printed in `--chat` output and written to
`logs/agent.log` on every request, so low-confidence extractions are visible
to the user in real time, not just discoverable after the fact in a log
file.

### Reliability battery — real, runnable, not hand-written numbers

`tests/test_reliability.py` runs `extract_profile()` through 6 scripted
scenarios spanning a clean response to a simulated unrecoverable API
failure — run it yourself with `pytest tests/test_reliability.py -v -s`. The
full, verbatim output (5/6 succeeded, confidence 1.00→0.10, averaging 0.67)
is in the "Reliability / guardrail behavior" part of
[Execution Evidence](#execution-evidence) rather than duplicated here; this
section is about what that result means, not the raw numbers again.

### What worked

All 19 tests (14 in `tests/test_agent.py`, 3 in `tests/test_reliability.py`,
2 in `tests/test_recommender.py`) run against a scripted stand-in for the
Gemini client, so
guardrail correctness — numeric clamping, catalog-fallback, retry-vs-fail-closed
branching, "the explanation prompt actually contains the retrieved song
data," and now the confidence score itself — is verified deterministically,
with no network access and no API key. That also means the suite runs the
same way in CI as it does locally, which matters more than it sounds like
it should for anything touching an external API. It also meant that when I
later swapped providers (Anthropic Claude → Google Gemini, to get to a
genuinely free tier), the whole test suite acted as a regression check on
the swap: rewriting the fakes to match Gemini's response shape
(`response.function_calls` / `response.text` instead of Claude's
`response.content` blocks) and watching every test still pass gave real
confidence the guardrail logic itself didn't change, only the client it
talks to.

### What didn't work / what I couldn't test

The scripted-client approach can verify the *pipeline's* behavior (schema
shape, guardrail logic, confidence math, control flow) but can't verify
that the *live model* reliably produces good extractions or
non-hallucinated explanations for arbitrary free text — that requires
either a held-out eval set graded by a human or a second LLM judge, and I
didn't build that harness for this project. I also don't have an automated
check that the explanation text never references a song *outside* the
retrieved list (the prompt instructs against it, but nothing enforces it
programmatically) — that's a real gap, not a solved problem. And the
confidence score measures *how much the guardrails had to fix*, not
whether the corrected value is actually right — a profile that needed zero
corrections could still be a bad read of what the user meant; confidence
here is a proxy for "the model's raw output was well-formed," not for
"the recommendation is good."

### What I learned

While running the initial suite I discovered that `tests/test_recommender.py`
was already broken on `main` — `UserProfile` had grown three required
fields the starter tests never supplied — which had nothing to do with my
changes but would have made "all tests pass" false the whole time if I
hadn't run the full suite before and after my edits. The bigger lesson was
architectural: separating the deterministic scoring engine from the LLM
calls wasn't just a design preference, it's what made *any* of this
testable without an API key, and it's what made it possible to build a
confidence score from guardrail behavior instead of needing a live model's
self-reported (and not always available) probability. If extraction and
scoring had been one fused LLM call, there would be no way to unit-test the
guardrails — or measure confidence — at all.

---

## Reflection

Building the agent layer clarified something the base recommender only
hinted at: the hardest part of adding "AI" to a system usually isn't
getting a model to produce a plausible-looking answer — it's deciding what
you refuse to let it decide unsupervised. The scoring formula was already
transparent by construction; the interesting design work in the agent layer
was entirely about where to put a hard boundary (the enum schema, the
clamps, the fail-closed path) between "the model's guess" and "what the
rest of the system trusts." That's a more general lesson about
problem-solving with AI than about music recommendation specifically.

For the graded responsible-AI reflection — how I collaborated with AI
tools while building this, one specific helpful suggestion and one specific
flawed one, and a fuller accounting of this system's limitations and
biases — see **[`model_card.md`](model_card.md)**.

---

## Appendix A: Base-Recommender Sample Output

<details>
<summary>Full algorithm recipe, data flow, and bias table</summary>

Real-world recommenders like Spotify and YouTube operate at massive scale —
they blend collaborative filtering (patterns across millions of users), deep
audio analysis (neural nets on raw waveforms), NLP on playlists and reviews,
and real-time context — all re-ranked by models optimizing for engagement
metrics. This simulation prioritizes clarity over complexity: pure
content-based filtering on a single user's explicit preferences, scored with
a transparent weighted formula. No other users, no black-box neural nets, no
engagement optimization.

**`Song` object** — one row of `data/songs.csv`: `id`, `title`, `artist`,
`genre`, `mood`, `energy` (0–1), `tempo_bpm`, `valence` (0–1),
`danceability` (0–1), `acousticness` (0–1).

**`UserProfile` / preference dict** — `genre`, `mood` (most common among
liked songs), `energy`/`acousticness`/`valence` (averaged, 0–1),
`tempo_bpm`.

**Scoring recipe (100 points total, `score_song()` in `src/recommender.py`):**

```
STEP 1 — Genre match         (30 pts)  exact match only
STEP 2 — Mood match          (20 pts)  exact=20, same mood-group=10, else 0
                                        groups: chill/focused/peaceful,
                                        happy/upbeat/romantic,
                                        sad/melancholic/nostalgic,
                                        intense/energetic/angry,
                                        moody (standalone), relaxed (standalone)
STEP 3 — Energy proximity    (20 pts)  (1 - |song - target|) × 20
STEP 4 — Acousticness fit    (15 pts)  (1 - |song - target|) × 15
STEP 5 — Valence proximity   (10 pts)  (1 - |song - target|) × 10
STEP 6 — Tempo proximity     ( 5 pts)  normalized to dataset range, then
                                        (1 - |norm diff|) × 5
```

**Data flow:** `songs.csv` → `load_songs()` (cast types) → list of 18 song
dicts → `score_song(user_prefs, song)` called once per song → `(score,
reasons)` → `recommend_songs()` sorts descending and slices top-k.

| Bias | Where it comes from | Effect |
|---|---|---|
| Genre dominance | Genre is 30 pts — a categorical cliff | A perfect numeric match in the wrong genre can never beat a mediocre song in the right genre. |
| Small dataset amplification | Only 18 songs, multiple lofi entries | Lofi songs sweep the top-3 for a lofi user — no variety pressure. |
| Cold-start profile drift | Profile built from averages | One outlier liked song pulls all numeric targets off-center. |
| Unrepresented moods score 0 | Standalone moods (`moody`, `relaxed`) have no group | No partial credit available for those moods. |
| Tempo has lowest weight (5 pts) | By design | Barely differentiates at this dataset size. |

Full limitations and bias analysis (including the discovered bimodal
energy-gap issue): [`model_card.md`](model_card.md).

</details>

<details>
<summary>Six tested profiles, full ranked output (run with <code>python -m src.main</code>)</summary>

Profiles 1 and 2 are the same real output already shown, uncollapsed, in
[Execution Evidence](#execution-evidence) — repeated here for completeness
alongside all six.

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

</details>

---

## Repository Structure

```
src/
  recommender.py   # deterministic scoring engine (original assignment)
  agent.py          # conversational agent layer: extract → check → act → explain
  main.py           # CLI entry point: static demo (default) or --chat mode
data/
  songs.csv         # 18-song catalog
tests/
  test_recommender.py  # scoring engine tests
  test_agent.py         # agent pipeline + guardrail tests (scripted client)
  test_reliability.py   # confidence-scoring battery; run with -v -s for the summary
diagrams/
  agent_architecture.md  # system diagram (Mermaid, rendered on GitHub)
logs/
  agent.log         # git-ignored; written at runtime by src/agent.py
model_card.md        # model card + graded responsible-AI reflection
ai_interactions.md    # log of AI-assisted development for this project
```
