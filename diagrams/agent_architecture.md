# Agent Architecture — Conversational Taste Agent

System diagram for the agentic pipeline in [`src/agent.py`](../src/agent.py)
(`run_agentic_recommendation()`). GitHub renders the Mermaid block below
inline; open it in the [Mermaid Live Editor](https://mermaid.live) if your
viewer doesn't.

**Legend:** 🤖 agent (Gemini API call) · 🛡️ guardrail/validator ·
🔎 retriever/scorer · 📚/📝 data stores · 👤 human checkpoint ·
🧪 automated tester · ⚠️ failure path.

```mermaid
%%{init: {"flowchart": {"htmlLabels": true}} }%%
flowchart TD
    U["User\n(free-text taste description)\ne.g. 'something moody for a rainy afternoon'"]

    subgraph LIVE["Live request path — src/agent.py :: run_agentic_recommendation()"]
        direction TB

        AGENT1["🤖 Agent — PLAN\nextract_profile()\nGemini API call, forced function-calling schema\n(genre/mood enums built from catalog)"]

        GUARD{"🛡️ Guardrail — CHECK\n- clamp numeric fields to valid range\n- fall back unknown genre/mood to catalog default\n- retry transient API errors (backoff)\n- fail closed on non-retryable errors\n- compute confidence score from correction count"}

        CATALOG[("📚 Catalog\ndata/songs.csv\n(18 songs)")]

        RETRIEVER["🔎 Retriever / Scorer\nrecommend_songs()\nsrc/recommender.py\nscores every song 0–100 + reasons"]

        AGENT2["🤖 Agent — EXPLAIN\nexplain_recommendations()\nGemini API call, grounded ONLY in the\nretrieved (song, score, reasons) list"]

        OUT["Output to user\nranked recommendations + grounded explanation"]

        AGENT1 --> GUARD
        GUARD -- "valid profile" --> RETRIEVER
        CATALOG --> RETRIEVER
        RETRIEVER -- "scored, ranked results" --> AGENT2
        AGENT2 --> OUT
    end

    LOG[("📝 logs/agent.log\nevery extraction, guardrail correction,\nretry, and failure is recorded")]

    subgraph OFFLINE["Offline evaluation — human-in-the-loop"]
        direction TB
        DEV["👤 Developer"]
        FAKE["🧪 Tester / Evaluator\ntests/test_agent.py + test_reliability.py\nfake Gemini client\n(no network, deterministic)"]
        CASES["Guardrail test cases:\n- out-of-range numerics get clamped\n- unknown genre/mood falls back\n- non-retryable error → fails closed\n- explanation is grounded in retrieved data"]
        DEV -- "runs `pytest`" --> FAKE
        FAKE --> CASES
        CASES -- "pass/fail" --> DEV
        DEV -- "reads log history,\ntunes prompts / guardrails" --> AGENT1
    end

    U --> AGENT1
    OUT --> HUMAN["👤 User\nreads recommendations + explanation\nmay re-describe taste if unsatisfied"]
    HUMAN -. "new description\n(feedback loop)" .-> U

    AGENT1 -. logs .-> LOG
    GUARD -. logs .-> LOG
    RETRIEVER -. logs .-> LOG
    AGENT2 -. logs .-> LOG
    GUARD -- "extraction failed after retries" --> ERR["⚠️ Fail closed\nuser-facing error message\n(no crash, no silent bad data)"]
    ERR --> HUMAN

    classDef agent fill:#5b8def,color:#fff,stroke:#274690,stroke-width:1px;
    classDef guard fill:#f4a259,color:#3a2a12,stroke:#a9600b,stroke-width:1px;
    classDef data fill:#e8e8e8,color:#222,stroke:#888,stroke-width:1px;
    classDef human fill:#7dbf7d,color:#0d2c0d,stroke:#2e6b2e,stroke-width:1px;
    classDef err fill:#e15759,color:#fff,stroke:#8a1c1e,stroke-width:1px;

    class AGENT1,AGENT2 agent;
    class GUARD guard;
    class CATALOG,LOG,RETRIEVER data;
    class DEV,HUMAN,FAKE human;
    class ERR err;
```

## Reading the diagram

- **Input → process → output:** a free-text description enters at the top,
  flows through PLAN (extraction) → CHECK (guardrails) → the retriever
  (scoring against `data/songs.csv`) → EXPLAIN (grounded write-up), and
  exits as a ranked list plus explanation.
- **Where AI acts vs. where the system checks it:** the two 🤖 nodes are the
  only places Gemini is called. Every other node is deterministic code —
  in particular, the 🛡️ guardrail node sits *between* the two agent calls
  and can reject or repair the agent's output before it ever reaches the
  scoring engine.
- **Where humans/testing are involved:**
  - **Live path:** the 👤 user is both the source of input and the final
    reviewer of output — if the recommendations miss, they re-describe
    their taste, which re-enters the loop (dashed feedback edge).
  - **Failure path:** if extraction can't be validated even after retries,
    the guardrail fails closed (⚠️) with a clear message instead of passing
    bad data downstream.
  - **Offline path:** a separate, human-run test suite
    (`tests/test_agent.py` + `tests/test_reliability.py`) exercises the
    guardrail logic and the resulting confidence score against a fake
    client — no network calls — so a developer can verify guardrail
    correctness and iterate on prompts without touching the live API.
    `test_reliability.py` prints a real pass-rate and confidence summary
    (`pytest -v -s`), not just pass/fail.
