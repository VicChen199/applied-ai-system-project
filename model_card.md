# Model Card: Agentic Music Recommender

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
# Model Card: Music Recommender Simulation

---

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Goal / Task

VibeFinder 1.0 suggests songs that match a listener's taste. Given a user's preferred genre, mood, energy level, and acoustic preference, it scores every song in the catalog and returns the top 5. It is not predicting what you will click. It is finding what fits a description you give it.

---

## 3. Data Used

- **Catalog size:** 18 songs in `data/songs.csv`
- **Song features:** genre, mood, energy (0–1), tempo (BPM), valence (0–1), danceability (0–1), acousticness (0–1)
- **User features:** favorite genre, favorite mood, target energy, likes acoustic (yes/no)
- **Genres covered:** pop, lofi, rock, ambient, jazz, synthwave, indie pop, classical, hip hop, house, country, metal, r&b, folk, reggae
- **Moods covered:** happy, chill, intense, relaxed, focused, moody, nostalgic, confident, euphoric, heartbroken, angry, romantic, peaceful, playful
- **Limits:** The catalog is small and hand-curated. Pop and lofi have multiple entries. Classical, country, metal, and reggae each have only one. Niche genres are nearly invisible unless the user asks for them directly. No songs were added or removed from the starter set.

---

## 4. Algorithm Summary

Every song gets a score out of 100. Here is how the points are split:

| Component | Points | How it works |
|---|---|---|
| Mood match | 28 | Full points if the song's mood matches the user's. Zero if not. |
| Genre match | 20 | Full points for an exact genre match. Zero if not. |
| Energy closeness | 14 | More points if the song's energy is close to the user's target. |
| Tempo closeness | 10 | Expected tempo is guessed from energy (high energy → fast BPM). |
| Valence closeness | 10 | Expected positivity is guessed from mood (happy → high valence). |
| Danceability closeness | 8 | Expected danceability is guessed from energy. |
| Acousticness closeness | 6 | Acoustic fans get points for acoustic songs. Non-acoustic fans do not. |
| Artist diversity | 4 | Every song gets a flat bonus to reward catalog variety. |

The song with the highest total score is recommended first. No machine learning is involved. It is just math on top of a spreadsheet.

---

## 5. Observed Behavior / Biases

**What worked well:**
- Pop/happy profiles got accurate results immediately. "Sunrise City" scored 94–96/100 across tests — the clear correct answer.
- Lofi/chill profiles had two near-perfect matches in the catalog. The system returned both in the top 2, with an ambient/chill song as a reasonable third.
- Rock/intense profiles surfaced the correct song first. When genre did not match, mood carried the ranking — "Gym Hero" (pop/intense) ranked above "Iron Anthem" (metal/intense) because mood is worth more than genre.

**What did not work well:**
- **Binary matching is harsh.** "Indie pop" scores zero for genre when the user asks for "pop," even though they are very similar styles.
- **Conflicting preferences break the system.** A user who wants classical music but high energy gets a broken result. The only classical song in the catalog has low energy (0.22). It loses so many points on energy, tempo, and danceability that a folk song beats it. The system cannot bridge preferences that contradict each other.
- **Small catalog amplifies bias.** Genres with one song lose almost every head-to-head. Pop appears as a fallback for many profiles, even when the user did not ask for it.
- **Artist diversity is not real.** The 4-point bonus is the same for every song. Two songs by the same artist can still appear back-to-back in the results.
- **No memory.** The same inputs always produce the same outputs. The system ignores what the user has already heard.

---

## 6. Evaluation Process

Four user profiles were tested:

1. **High-Energy Pop Fan** — genre: pop, mood: happy, energy: 0.9, not acoustic
   - Top result: "Sunrise City" at 94.61/100. Matched intuition exactly.
   - Second place dropped to 73.00 — the catalog runs out of good pop/happy options quickly.

2. **Chill Lofi Listener** — genre: lofi, mood: chill, energy: 0.35, acoustic
   - Top two results were both lofi/chill. Third was ambient/chill — a reasonable fallback.
   - Most confident profile tested. Two songs scored nearly identically (96.39 and 95.06).

3. **Deep Intense Rock** — genre: rock, mood: intense, energy: 0.95, not acoustic
   - "Storm Runner" (rock/intense) ranked first at 96.48/100. Expected result.
   - "Gym Hero" (pop/intense) ranked second — mood matched, genre did not. A surprise worth noting.

4. **Edge Case: Classical + High Energy** — genre: classical, mood: peaceful, energy: 0.9, acoustic
   - Best score was only 61/100. No single song in the catalog fits this profile.
   - A folk song won on mood. The actual classical song ranked second with 48/100.
   - This exposed the biggest weakness: the system cannot handle profiles where genre and energy contradict each other.

**Weight-shift experiment:** Energy weight was doubled (14→28) and genre weight was halved (20→10). The top song did not change for the three clean profiles. For the edge-case profile, the classical song fell out of the top 5 entirely — replaced by rock and metal. An unexpected math issue appeared: the weight change added 4 net points to the system, making the maximum possible score 104 instead of 100. One result scored 100.39. This showed that weight experiments must keep the total budget at 100 or scores become misleading.

---

## 7. Intended Use and Non-Intended Use

**Intended use:**
- Classroom exploration of how a content-based recommender works
- Learning how scoring rules and feature weights affect output
- Understanding the relationship between dataset size and recommendation quality

**Not intended for:**
- Real users making real music choices
- Any production or consumer-facing product
- Replacing systems that use actual listening history, collaborative filtering, or learned embeddings
- Making decisions about music licensing, playlist curation, or artist promotion

---

## 8. Ideas for Improvement

1. **Fuzzy genre and mood matching.** Award partial points for related genres (e.g., "indie pop" gets 12 of 20 points when the user asks for "pop"). A simple lookup table would handle most cases without needing machine learning.

2. **Ask users for more preferences directly.** Right now, expected tempo, valence, and danceability are all inferred from mood and energy. If users could optionally set a BPM range or a "happy vs. melancholy" slider, the inferred values could be skipped entirely. This would fix the conflicting-preference problem.

3. **Enforce artist diversity at ranking time.** After scoring, apply a penalty to any song whose artist already appears in the results. This would make the 4-point diversity bonus actually do something.

---

## 9. Personal Reflection

**Biggest learning moment:** The edge-case profile (classical + high energy) was the clearest lesson. Before building this, I assumed a good algorithm would gracefully handle any input. It does not. When preferences conflict — when the genre you want is inherently quiet but the energy you want is loud — the system has no way to reason about that. It just adds up numbers and calls the winner a recommendation. That is not intelligence. That is arithmetic. Realizing the gap between the two was the most valuable moment of the project.

**How AI tools helped, and when to double-check:** The AI was useful for translating the algorithm recipe into working Python quickly and for suggesting the `sorted()` vs `.sort()` distinction. But the scoring logic required careful human review. The AI initially suggested a scoring formula that could exceed 100 points for highly acoustic users — a bug I only caught by running the actual output and seeing numbers over 100 during the weight-shift experiment. The rule became: trust the AI for boilerplate, but verify any math on your own.

**What surprised me about simple algorithms feeling like recommendations:** The pop/happy and lofi/chill profiles felt genuinely good — like the system "knew" what I wanted. That feeling came entirely from the fact that those profiles had exact matches in the catalog. The moment I tried the edge case, the illusion broke. The system was never reasoning about music. It was matching strings and measuring gaps. The "recommendation feeling" was a side effect of having the right data, not a sign of intelligence in the algorithm. That distinction matters a lot when thinking about real recommender systems.

**What I would try next:** I would add a fuzzy genre similarity map as the first real improvement. Right now "indie pop" and "pop" score zero for each other, which is clearly wrong. A simple dictionary that maps related genres to a partial credit value (like 10 out of 20 points instead of 0) would make the recommendations feel more natural without adding any complexity to the core scoring loop. After that, I would expand the catalog to at least 50 songs so niche genres have more than one representative — because right now, asking for classical or country produces results that are mostly just energy-matched pop songs in disguise.
