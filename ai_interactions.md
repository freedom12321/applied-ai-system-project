# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agentic Workflow (SF8)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

Extend the static recommender into a natural-language interface: a user
describes what they want to hear in plain English, an agent extracts a
structured taste profile from that text, the existing scoring engine ranks
the catalog against it, and a second call explains the picks — all without
hand-typing numeric preferences. The requirement was that the AI step had to
*change* how the system behaves (drive the actual recommendation), not just
print alongside a canned answer.

**Design — plan, check, act, explain:**

- **Plan:** `extract_profile()` (`src/agent.py`) calls the Gemini API with a
  function-calling schema (`tool_config.function_calling_config.mode="ANY"`
  forces the call) whose `genre`/`mood` parameters are JSON Schema `enum`s
  built dynamically from `data/songs.csv` at call time. This makes an
  invalid category structurally impossible rather than something to catch
  after the fact.
- **Check:** JSON Schema can't express numeric bounds, so `energy`,
  `acousticness`, `valence`, and `tempo_bpm` are clamped client-side as a
  second guardrail layer. Retryable errors (rate limits, 5xx) get a short
  backoff retry; non-retryable errors (bad auth, malformed request) fail
  closed immediately with a logged reason instead of looping or crashing.
- **Act:** the checked profile is passed straight into the *existing*
  `recommend_songs()` — no scoring logic was duplicated for the AI path.
- **Explain:** `explain_recommendations()` sends the actual scored results
  (titles, scores, per-feature reasons) into the prompt and instructs the
  model to reference only that data. This is what makes the explanation
  grounded in retrieved data rather than a generic LLM answer bolted onto
  the side of the real output.

**What did the agent (Claude, via this session) generate or change?**

- `src/agent.py` — new module: guardrails (`_clamp01`, `_clamp_tempo`,
  `_validate_categorical`, `catalog_vocab`), `extract_profile()`,
  `explain_recommendations()`, and the `run_agentic_recommendation()`
  orchestration function, plus file+console logging to `logs/agent.log`.
- `src/main.py` — added a `--chat` flag and `run_chat()` interactive loop;
  left the default `python -m src.main` demo path untouched.
- `tests/test_agent.py` — 13 tests covering guardrail behavior and the
  extract/explain pipeline against a fake Gemini client (no network
  calls, no API key required, deterministic).
- `requirements.txt` — added `google-genai`.
- `.gitignore` — added `logs/` and `.env`.
- `README.md` — new "AI Feature" section with setup steps and a worked
  example transcript.

**What did I verify or fix manually?**

- Ran the full test suite (`pytest`) after the change — confirmed all new
  tests pass and, along the way, found two *pre-existing* failures in
  `tests/test_recommender.py` (the `UserProfile` dataclass had grown three
  required fields the tests never supplied — unrelated to this feature).
  Fixed those two test call sites so the whole suite is green rather than
  leaving a partially-broken baseline.
- Manually ran `python -m src.main` to confirm the static demo output is
  byte-for-byte unchanged.
- Manually ran `python -m src.main --chat` with `GEMINI_API_KEY` unset to
  confirm the guardrail path prints a clear setup message and exits cleanly
  instead of throwing a raw stack trace.
- Inspected `logs/agent.log` after a run to confirm every guardrail
  correction, retry, and failure is actually recorded, not just designed to
  be.

**Provider swap: Anthropic Claude → Google Gemini (same session, later
prompt).** The agent was originally built against the Claude API. When asked
to move to a model that's genuinely free to use — no billing setup, no
credit card — I proposed two different kinds of "free" (fully local via
Ollama vs. a free-tier hosted API) and let the user pick, rather than
guessing which trade-off they wanted. They chose Google Gemini, and named a
specific model (`gemini-3.6-flash`) to use as the default.

Before writing any code, I fetched the actual `google-genai` SDK source
(`raw.githubusercontent.com/googleapis/python-genai`) rather than trusting
a summarized doc page — an earlier WebFetch of Google's docs page returned
an "Interactions API" shape (`client.interactions.create(...)`) that looked
inconsistent with established patterns and turned out to be either stale or
a different, newer surface; a second fetch of the SDK's own README and
`types.py` confirmed the actual, current, verified path is
`client.models.generate_content(model=..., contents=..., config=...)` with
`types.FunctionDeclaration(parameters_json_schema=...)` for tool schemas.
I then imported the real installed package in this environment and
constructed each class I intended to use (`FunctionDeclaration`, `Tool`,
`ToolConfig`, `GenerateContentConfig`) to confirm the exact kwargs worked,
instead of shipping code based on the doc summary alone.

Rewriting `src/agent.py` against the verified API, then rewriting
`tests/test_agent.py`'s fakes to match Gemini's response shape
(`response.function_calls` / `response.text` instead of Claude's
`response.content` list of typed blocks) and re-running the full suite
(all 15 tests passing, same guardrail behavior) was what gave confidence
the swap didn't silently change what the guardrails actually do — only
which client they talk to.

**Reliability/confidence-scoring pass (same session, later prompt).** Asked
to prove the AI system's reliability rather than just assert it, I refactored
the three guardrail helpers (`_clamp01`, `_clamp_tempo`,
`_validate_categorical`) to each return `(value, was_corrected)` instead of
just `value`, and added `_confidence_from_corrections()`: a deterministic
0.0–1.0 score that starts at 1.0 and drops 0.15 per field the guardrails had
to fix. This is explicitly *not* a self-reported model probability — Gemini's
function-calling API doesn't expose log-probabilities in a simple way, and I
didn't want to reach for an unverified field just to have a number — it's a
transparent, code-computed signal for "how much did we have to correct."
`extract_profile()` now embeds `confidence` in the returned profile dict and
logs it; `main.py --chat` prints it.

I then wrote `tests/test_reliability.py`: a battery of 6 scripted extraction
scenarios (clean → increasingly corrupted → a simulated unrecoverable API
error) run through the real `extract_profile()`, with a dedicated
`test_reliability_summary` test that prints a human-readable pass-rate and
confidence summary (`pytest tests/test_reliability.py -v -s`). I ran it and
copied the actual output into the README's Testing Summary rather than
writing example numbers by hand — 5/6 scenarios succeeded, the one designed
failure correctly failed closed instead of returning a guessed profile, and
confidence across the 5 successes ranged 1.00→0.10, averaging 0.67. Updating
the existing guardrail unit tests to match the new tuple return type (and
adding assertions on the resulting `confidence` field) kept the full suite
at 19/19 passing — a real regression check that the refactor didn't change
guardrail behavior, only added a measurement on top of it.

---

## Design Pattern (SF10)

> Document how AI helped you choose or implement a design pattern.

**Which design pattern did you use?**

<!-- e.g., Strategy, Factory, Observer, etc. -->

**How did AI help you brainstorm or implement it?**

<!-- Describe the conversation or suggestions that led to your decision -->

**How does the pattern appear in your final code?**

<!-- Point to the relevant class or method -->
