# Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Intended Use

VibeFinder 1.0 suggests up to 5 songs from a small hand-curated catalog based on a user's preferred genre, mood, energy level, and acoustic preference. It is designed for classroom exploration of how content-based recommenders work, not for real-world deployment. The system assumes each user has a single, stable taste profile — it does not track listening history, skip patterns, or context (e.g., time of day or activity).

---

## 3. How the Model Works

Every song in the catalog gets a score out of 100. The score is built from eight ingredients:

- **Mood match** (28 points): If the song's mood exactly matches what the user asked for, it gets full points. No partial credit.
- **Genre match** (20 points): Same idea — exact match only.
- **Energy closeness** (14 points): The system measures how far the song's energy level is from the user's target. A song that is very close to the target gets nearly all 14 points; a song that is far away gets fewer.
- **Tempo closeness** (10 points): Since users do not pick a target tempo directly, the system guesses an expected tempo from the user's energy preference (high energy → fast tempo).
- **Valence closeness** (10 points): Valence means "how positive the song feels." The system infers an expected valence from the user's mood (e.g., "happy" → high valence).
- **Danceability closeness** (8 points): Inferred from energy — higher energy target → higher expected danceability.
- **Acousticness closeness** (6 points): If the user likes acoustic music, songs that are more acoustic score better; otherwise, low-acoustic songs are preferred.
- **Artist diversity** (4 points): Every song receives a flat 4 points at the single-song scoring stage, representing the baseline benefit of catalog variety.

The song with the highest total is recommended first. Think of it like a checklist: the song that checks the most boxes — and checks them most closely — wins.

---

## 4. Data

The catalog contains **18 songs** stored in `data/songs.csv`. Each song has a genre, mood, energy level (0–1), tempo in BPM, valence (0–1), danceability (0–1), and acousticness (0–1).

Genres represented: pop, lofi, rock, ambient, jazz, synthwave, indie pop, classical, hip hop, house, country, metal, r&b, folk, and reggae.

Moods represented: happy, chill, intense, relaxed, focused, moody, nostalgic, confident, euphoric, heartbroken, angry, romantic, peaceful, and playful.

No songs were added or removed from the starter dataset. The catalog is heavily weighted toward a specific kind of Western popular taste — it has multiple lofi and pop entries but only one classical, one country, one metal, and one reggae song. This means niche genres have almost no chance of appearing in recommendations for users who do not explicitly ask for them.

---

## 5. Strengths

The recommender works well for users whose preferences align with the most common genres and moods in the dataset. In testing:

- **Pop/happy profile**: "Sunrise City" correctly ranked #1 with a score of 96/100. The result matched musical intuition immediately.
- **Chill lofi profile**: Both lofi/chill songs ranked #1 and #2, with the third slot going to an ambient/chill song — a reasonable fallback since ambient and lofi share a similar vibe.
- **Intense rock profile**: "Storm Runner" (rock/intense) ranked #1 at 96/100, with "Gym Hero" (pop/intense) second because it matched the mood even without matching the genre.

The scoring is fully transparent — every recommendation comes with a breakdown of exactly why each point was awarded. That makes it easy to audit and explain.

---

## 6. Limitations and Bias

**Exact-match bottleneck.** The mood and genre checks together account for 48 out of 100 points, but they are binary — either an exact string match or zero. A user who likes "indie pop" will score zero for the genre component when "pop" songs appear, even though those songs are very similar. Real recommenders use embeddings or fuzzy matching to handle this; ours does not.

**Inferred features break for contradictory profiles.** The system derives an expected tempo, valence, and danceability from the user's mood and energy rather than asking for them directly. When a user has conflicting preferences — for example, `genre: classical` but `target_energy: 0.9` — the inferred features pull in opposite directions. The classical song in the catalog (Dawn Sonata) has energy 0.22, so even though it matches the genre, it scores poorly on energy, tempo, and danceability. The result is that the top recommendation ends up being a folk song that matched mood but not genre, and the classical song drops to #2 with a score of only 48/100. The system cannot surface a "high-energy classical" song because that song does not exist in the catalog and the scoring cannot bridge the gap.

**Small catalog amplifies genre imbalance.** With only 18 songs, any genre with a single entry is effectively invisible unless the user explicitly asks for it. Pop has more representation than folk, reggae, country, or classical, so pop songs appear more often in the lower-ranked slots of profiles that do not ask for pop at all.

**No listening history or context.** The system treats every recommendation session identically. It has no memory of what a user already heard, cannot adjust for time of day or activity, and does not learn from skips or replays.

**Artist diversity is not enforced at the ranking stage.** The 4-point diversity bonus is awarded equally to every song at scoring time, so it does not actually prevent two songs by the same artist from appearing back-to-back in the top 5.

---

## 7. Evaluation

Four user profiles were tested:

1. **High-Energy Pop Fan** (`pop / happy / energy 0.9 / not acoustic`): Results matched intuition perfectly. "Sunrise City" scored 94.61 and was the obvious correct answer. "Rooftop Lights" (indie pop / happy) ranked second — it matched the mood but not the genre, which is exactly the right tradeoff.

2. **Chill Lofi Listener** (`lofi / chill / energy 0.35 / acoustic`): Both lofi/chill songs ranked in the top two. "Spacewalk Thoughts" (ambient/chill) came third despite not being lofi — a pleasant and musically reasonable surprise. This profile produced the most confident results of the four.

3. **Deep Intense Rock** (`rock / intense / energy 0.95 / not acoustic`): "Storm Runner" ranked first as expected. The surprise was that "Gym Hero" (pop/intense) ranked second above "Iron Anthem" (metal/intense). The system prefers mood match over genre match when genre is not available, which is defensible but may feel wrong to a hardcore rock listener.

4. **Edge Case — Classical but High Energy** (`classical / peaceful / energy 0.9 / acoustic`): This profile exposed the clearest weakness. The top score was only 61/100, compared to 94–96 for the other three profiles. "Forest Lantern" (folk/peaceful) won because peaceful mood matched, even though the user asked for classical. "Dawn Sonata" (the only classical song) ranked second with 48 points because its low energy (0.22) cost it heavily on five of the eight scoring components. The system cannot reconcile a genre that inherently implies low energy with a user who wants high energy.

**Weight-shift experiment.** Doubling the energy weight (14→28) and halving the genre weight (20→10) changed the rankings for the edge-case profile most dramatically: the classical song dropped out of the top 5 entirely, replaced by rock and metal songs with high energy. For the clean profiles (pop, lofi, rock), the top song did not change but the score gaps between #1 and #5 widened, meaning energy became a stronger separator. Importantly, the total possible score became 104 instead of 100 because the weight changes were not budget-neutral — a reminder that any weight change must be recalculated against the total budget to keep scores comparable across profiles.

---

## 8. Future Work

- **Fuzzy genre and mood matching**: Instead of all-or-nothing, award partial points for related genres (e.g., "indie pop" vs. "pop") using a genre similarity map.
- **Ask for tempo and valence directly**: Let users optionally specify a BPM range or a "positive/negative" vibe preference so the inferred values are not needed.
- **Budget-neutral weight adjustments**: Enforce that all weights always sum to 100 so any experiment stays comparable.
- **Diversity enforcement at ranking time**: After scoring, penalize any song whose artist already appears in the top results.
- **Larger, more balanced catalog**: Add more songs in underrepresented genres so niche-taste users get meaningful results.

---

## 9. Personal Reflection

Building this recommender made the cost of a "simple" scoring rule very concrete. The mood and genre weights felt intuitive at first — of course you want a happy pop song when you ask for happy pop — but the edge-case experiment showed that any time two signals point in opposite directions, the system has no way to reason about the conflict; it just adds up numbers and picks the winner. Real recommenders like Spotify invest heavily in learned representations precisely because hand-coded weights cannot handle the full range of listener tastes.

The most surprising result was that the Chill Lofi profile produced the most accurate and confident recommendations, while the Classical/High-Energy profile produced the least. That asymmetry is entirely a dataset artifact: lofi has multiple well-matched entries, classical has one — and that one is incompatible with the energy preference. It is a good reminder that a recommender is only as good as its catalog. A beautiful algorithm applied to a biased or thin dataset will still produce biased or thin results.
