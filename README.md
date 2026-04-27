# Agentic Music Recommender (Gemini + Feedback Loop)

## Title and Summary
This project is an interactive music recommender that learns from user feedback over multiple rounds and updates recommendations in-session. It matters because it demonstrates an agentic AI workflow: initialize preferences, gather outcomes, adapt profile state, and re-rank results in a transparent loop.

## Original Project (Modules 1-3)
The original project was **Music Recommender Simulation**. It used a weighted, explainable scoring function (genre, mood, energy, tempo-related similarity, valence, danceability, and acousticness) to rank songs from a fixed CSV catalog for predefined profile types. It could produce top-k recommendations and explanations, but it did not support iterative human feedback, blended profile percentages, or Gemini-driven adaptation.

## Architecture Overview
The system flow is:
1. Load song candidates from `data/songs.csv`.
2. Show a diverse starter set (including a wildcard option) to bootstrap user taste.
3. Infer a blended profile (Gemini when available, deterministic fallback otherwise).
4. Rank songs with diversity constraints (artist variety, adjacent option, cross-genre fallback).
5. Let the user give feedback (`liked`, `partial`, `early_stop`, `skipped_without_listening`).
6. Update profile blend and re-rank, or let the user keep the same list and continue feedback.
7. Log each round to JSONL for traceability and testing.

See system diagram: `assets/agentic_workflow_diagram.md`.

## Setup Instructions
1. Go to project folder:
```bash
cd applied-ai-system-project
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
```
Set API key in `.env`:
```bash
GEMINI_API_KEY=your_real_key_here
```

5. Run app:
```bash
python -m src.main --rounds 5
```

6. Optional deterministic mode (no Gemini calls):
```bash
python -m src.main --no-gemini --rounds 5
```

7. Run tests:
```bash
pytest
```

## Sample Interactions
### Example 1: Starter selection initializes profile blend
**Input**
- User selects starter option `5` (wildcard).

**AI Output**
- App prints initial blend source (`starter_song_gemini` or deterministic fallback).
- App prints blended profile mix (for example: `Chill Lofi Listener: 52%, High-Energy Pop Fan: 28%, ...`).
- Round 1 recommendations are generated from that blend.

### Example 2: On-demand metrics for all songs
**Input**
- User types `details all` (or `metrics`) at recommendation prompt.

**AI Output**
- App prints full metrics for all five songs (score, genre, mood, energy, tempo, valence, danceability, acousticness, explanation).

### Example 3: Feedback loop with user-controlled next step
**Input**
- User selects song `2`.
- User feedback: `liked`.
- User chooses `2` at next-step prompt (keep current recommendations).

**AI Output**
- Profile blend updates and is printed.
- Log event is written.
- Same recommendation list remains available for more feedback instead of forcing a new round.

## Design Decisions
- **Catalog-grounded retrieval:** recommendations come from CSV, not generated songs, to keep outputs testable and reproducible.
- **Blended profile representation:** user taste is modeled as percentages across base profiles, avoiding a rigid single-label profile.
- **Gemini + deterministic fallback:** system remains functional in offline/no-key scenarios and in CI.
- **Controlled diversity policy:** adds exploration (adjacent + cross-genre) while preserving relevance bounds.
- **Human-in-the-loop control:** after feedback, user chooses whether to continue with current set or fetch new recommendations.

**Trade-offs**
- Strong guardrails improve reliability and clarity, but can reduce novelty versus unconstrained recommenders.
- CSV-based retrieval is robust for class scope, but less expressive than embedding-based systems at large scale.

## Testing Summary
**What worked**
- Unit tests for ranking, artist diversity, adjacent recommendations, genre diversity fallback, and bounded quality behavior pass.
- CLI helper tests for feedback parsing and next-step routing pass.
- Deterministic mode (`--no-gemini`) enables repeatable behavior for debugging and grading.

**What did not work initially**
- Early-return logic in diversity ranking bypassed post-processing rules, causing single-genre top-5 outputs.
- CLI placeholder confusion around `details <number>` caused invalid-command loops.
- Startup flow briefly caused duplicate profile prompting.

**What we learned**
- Guardrail logic should be tested against real edge profiles, not only synthetic happy paths.
- CLI command ergonomics need explicit aliases (`details all`, `metrics`) and clearer guidance.
- Regression tests are essential after ranking-policy changes because control-flow mistakes can silently break diversity guarantees.

## Reflection
**What are the limitations or biases in your system?**  
The recommender is still catalog-bounded and feature-engineered, so it can only choose from what exists in `songs.csv`, and its behavior reflects the feature distributions and labeling choices in that dataset. Weighted scoring may over-prefer whichever genres/moods are more densely represented, and profile blending simplifies real taste into a small set of predefined profile archetypes.

**Could your AI be misused, and how would you prevent that?**  
A misuse risk is over-trusting recommendations as objective truth or using feedback signals in a way that profiles users too aggressively. To reduce this, the project keeps updates transparent, uses bounded/validated profile changes, allows human override at each step, and logs decisions for auditability; in a production system I would also add stricter privacy rules and explicit consent controls for stored feedback history.

**What surprised you while testing your AI's reliability?**  
A small control-flow bug (an early return in diversity ranking) was enough to silently disable later guardrails and produce repeated single-genre recommendations, even when alternatives existed. That was a strong reminder that reliability failures are often in orchestration logic, not only in model calls.

**Describe your collaboration with AI during this project. Include one helpful and one flawed suggestion.**  
AI collaboration was most helpful when iterating quickly on architecture and implementation details, especially for turning the static recommender into a full feedback loop with deterministic fallback and clearer CLI commands (`details all`, same-list vs new-list flow). One flawed AI suggestion occurred during diversity tuning: an earlier version claimed genre variety was enforced, but due to an early-return path it still produced all-same-genre outputs in practice; catching this through runtime checks and then adding regression tests was essential.

This project says I approach AI engineering as a reliability-first systems discipline, not just prompt writing or model calls. I prioritize transparent decision logic, fallback behavior, test coverage, and human-in-the-loop controls so the system stays useful and debuggable even when model responses are imperfect. It also reflects my iterative mindset: I use real runtime evidence to diagnose failures, tighten guardrails, and improve user experience.

## Key Files
- `src/main.py` - interactive session loop, starter onboarding, Gemini/fallback profile-blend updates, logging.
- `src/recommender.py` - scoring and diversity-aware recommendation selection.
- `data/songs.csv` - 500-song catalog.
- `tests/test_recommender.py` - recommender/ranking/diversity tests.
- `tests/test_agent_loop.py` - interaction/helper tests.
- `assets/agentic_workflow_diagram.md` - Mermaid architecture diagram.
