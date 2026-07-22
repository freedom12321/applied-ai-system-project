# Presentation Script — VibeMatch (5–7 minutes)

Target runtime: **~6:30**. Every number and transcript line below is copied
from this repo's README/tests — nothing here is invented for the talk.
Practice out loud once with a timer before presenting; the live demo is the
part most likely to run long, so know your fallback (see Segment 4).

Slide deck to present alongside this script: open the published Artifact
link, or `presentation/slides.html` if you saved a local copy. Advance with
→ / ←, or click the arrows in the bottom corner.

---

## Segment 1 — Hook (0:00–0:20) · Slide 1: Title

> "This is VibeMatch — a music recommender I built for CodePath, extended
> with a real AI agent. The pitch is simple: the scoring is 100% transparent
> arithmetic, and the one place I use an LLM is wrapped in guardrails tight
> enough that it can't corrupt the deterministic part underneath it. I'm
> going to show you both halves, prove the reliability claims with real test
> output, and tell you what actually surprised me building it."

**Cue:** advance to Slide 2 as you finish the last sentence.

---

## Segment 2 — Where this started (0:20–1:05, 45s) · Slide 2

> "I started from CodePath's `module3show-musicrecommendersimulation-starter`
> template. The assignment: represent songs and a listener's taste as data,
> design a transparent scoring rule, and reflect on how it mirrors real
> recommenders like Spotify. I built the scoring engine — that part's
> `src/recommender.py` — and then went further: I added a conversational
> agent on top of it, because typing `energy: 0.39, acousticness: 0.78` by
> hand is not how anyone actually describes music they want to hear."

**Cue:** advance to Slide 3.

---

## Segment 3 — Architecture (1:05–2:20, 75s) · Slide 3

> "The system is two layers. Layer one is the original scoring engine —
> completely rule-based, no ML, no embeddings. Every song gets scored out of
> 100 points: 30 for genre match, 20 for mood, 20 for energy proximity, 15
> for acousticness, 10 for valence, 5 for tempo. Every point is traceable —
> that's the whole point of the original assignment.
>
> Layer two is what I added: a Gemini-powered agent, in four steps. PLAN —
> it extracts a structured taste profile from free text, using a
> function-calling schema where the genre and mood fields are enums built
> straight from the song catalog, so the model is *structurally* incapable
> of returning a genre that doesn't exist. CHECK — every numeric field gets
> clamped, and I compute a confidence score based on how much correction was
> needed. ACT — the checked profile goes through the *exact same* scoring
> engine as layer one, no shortcuts. EXPLAIN — a second call writes the
> explanation, but it's only allowed to reference the songs and scores that
> were actually retrieved — it can't just make something up."

**Cue:** advance to Slide 4 (Live Demo cue) and switch your screen share to
the terminal now.

---

## Segment 4 — LIVE DEMO (2:20–4:50, ~2:30) · Slide 4 stays up as a title card

Run these in order. If `GEMINI_API_KEY` isn't set or the network drops
mid-talk, say so out loud and fall back to reading the captured transcript
from the README's "Execution Evidence" section — it's the same code path,
just pre-recorded, and the README is explicit about that distinction, so
it's not a stretch to cite it live.

**Demo A — base system, no AI, 15s of narration**

```bash
python -m src.main
```

> "This is layer one on its own — six fixed profiles scored against the
> catalog. Look at High-Energy Pop: Sunrise City wins at 97.8, and you can
> read exactly why — genre match plus-30, mood match plus-20, and so on down
> the line. No black box."

**Demo B — the agent, natural language (the centerpiece)**

```bash
python -m src.main --chat
```

Type this exact input (it's the same one captured in the README):

```
I want something low-key and moody for a rainy afternoon of reading
```

> "Watch what comes back: a full taste profile — ambient, chill, low
> energy, high acousticness — derived from that sentence, not typed by
> hand. Then five ranked, scored songs, and an explanation that's grounded
> in the actual numbers, not a canned response."

**Demo C — guardrails catching a bad extraction (optional if time is tight)**

Type something deliberately weird or type `quit` and instead **narrate**
the README's Example 2 if you're short on time:

> "In testing, I fed it a genre that isn't in the catalog — 'death metal' —
> and an energy value of 1.4, which is out of range. The guardrails caught
> both: fell back to a real catalog genre, clamped the energy to 1.0, and
> logged every correction. That's not something I'm claiming happens — it's
> in `logs/agent.log` every time it runs."

**Cue:** switch back to slides, advance to Slide 5.

---

## Segment 5 — Reliability, with receipts (4:50–5:35, 45s) · Slide 5

> "I didn't want to just claim this is reliable, so here's the proof. 19
> automated tests, all passing, and none of them need an API key — the
> agent tests run against a scripted stand-in for Gemini's response shape,
> so guardrail logic is verified deterministically.
>
> I also built a dedicated reliability battery — six scripted scenarios from
> a clean response to a simulated API failure. Here's the actual output:
> five out of six succeeded. The one that didn't was the simulated API
> error, and it correctly *failed closed* — no guessed profile, just a
> clear error. Confidence across the five successes ranged from 1.00 on
> clean input down to 0.10 when every field was corrupted, averaging 0.67.
> That confidence score isn't Gemini self-reporting — it's something I
> compute from how many fields the guardrails had to fix."

**Cue:** advance to Slide 6.

---

## Segment 6 — What I learned (5:35–6:20, 45s) · Slide 6

> "Two things stand out. First, an AI-collaboration moment: partway through,
> I switched the whole agent from Anthropic's Claude API to Google's Gemini
> API, specifically so anyone could run this for free. Before writing code,
> I had Claude verify the actual Gemini SDK source instead of trusting a
> summarized doc page — which was good, because that page described an API
> shape that didn't actually match the real package. But the same session
> also left Claude-specific wording — the word 'strict' — baked into three
> different files describing Gemini's *different* mechanism, and it sat
> there uncaught until I went back and asked for a documentation review.
> Small mistake, but a real one, and a good reminder that AI-written docs
> need the same scrutiny as AI-written code.
>
> Second, a limitations point I want to be upfront about: the confidence
> score measures how much correction was needed, not whether the result is
> actually right. A profile that needed zero corrections can still
> misread what someone meant. That's a real gap, and it's in the model card,
> not swept under the rug."

**Cue:** advance to Slide 7 / final slide.

---

## Segment 7 — Close (6:20–6:40, 20s) · Slide 7

> "So: a transparent scoring engine underneath, a guardrailed free AI agent
> on top, and reliability I can actually show you rather than just assert.
> Everything you saw is reproducible — the README has the exact commands.
> Thanks — happy to take questions."

---

## Timing cheat sheet

| Segment | Time | Cumulative |
|---|---|---|
| Hook | 0:20 | 0:20 |
| Where this started | 0:45 | 1:05 |
| Architecture | 1:15 | 2:20 |
| **Live demo** | 2:30 | 4:50 |
| Reliability | 0:45 | 5:35 |
| What I learned | 0:45 | 6:20 |
| Close | 0:20 | 6:40 |

If running long: cut Demo C (guardrails) and narrate it instead — that alone
saves ~30–40s. If running short: let Demo B breathe, or read one more line
from the "Why" explanation out loud.

## Before you present

- [ ] `export GEMINI_API_KEY=...` in the terminal you'll demo from (test it once beforehand)
- [ ] `python -m src.main --chat` warmed up in one tab, README open in another as fallback
- [ ] Font/terminal size large enough to read from the back of the room
- [ ] Know your fallback line if the live call fails: "this is the exact same code path as the transcript in the README, captured earlier"
