# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

In my understanding, real-world recommenders (like Spotify and YouTube) combine user behavior patterns with content signals, then rank many candidate songs by how likely each one is to fit the listener's current taste and context. My version prioritizes a transparent content-based approach because it scores each song by matching genre and mood before rewarding songs whose energy is closer to the user's target instead of simply higher or lower.

Song features in my simulation: "genre", "mood", "energy", "acousticness", "valence".

UserProfile features in my simulation: "favorite_genre", "favorite_mood", "target_energy", "likes_acoustic".

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

This recommender uses a weighted point system (out of 100) to score every song in "data/songs.csv" against a user profile.

Algorithm recipe:

1. Input user preferences: "favorite_genre", "favorite_mood", "target_energy", and "likes_acoustic".
2. Loop through each song in the CSV.
3. Compute a weighted score with these final weights:
   - "Mood" match = 28 points (exact match gets full points)
   - "Genre" match = 20 points (exact match gets full points)
   - "Energy" similarity = 14 points
   - "Tempo" similarity = 10 points
   - "Valence" similarity = 10 points
   - "Danceability" similarity = 8 points
   - "Acousticness" similarity = 6 points
   - "Artist" affinity/diversity factor = 4 points
   - "Scoring formula" = total score is the sum of all weighted components (max 100)
4. For numeric features, reward closeness to the user's target value using similarity, not raw high/low values.
5. Sum all component scores into one total per song.
6. Rank songs from highest to lowest score.
7. Return Top "K" recommendations.

Simple process view:

"Input (User Prefs) -> Process (score each song with weighted logic) -> Output (rank + Top K)"

Brief note on potential bias:

- The system can over-favor moods/genres that are more common in the dataset.
- It may under-recommend niche styles because exact mood/genre matching has high weight.
- Since this is a small hand-curated catalog, results reflect the dataset creator's taste more than global listener diversity.


---

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

## Terminal Output — Stress Test (4 Profiles)

Four profiles were run against the 18-song catalog. Output is copied directly from the terminal.

```
Loaded songs: 18

============================================================
  Profile: High-Energy Pop Fan
  Genre: pop  |  Mood: happy  |  Energy: 0.9  |  Acoustic: False
============================================================

  #1  Sunrise City  —  Neon Echo          Score: 94.61 / 100
  #2  Rooftop Lights  —  Indigo Parade    Score: 73.00 / 100
  #3  Gym Hero  —  Max Pulse              Score: 66.39 / 100
  #4  Storm Runner  —  Voltline           Score: 46.20 / 100
  #5  Neon Tide  —  Mar Azul              Score: 46.00 / 100

============================================================
  Profile: Chill Lofi Listener
  Genre: lofi  |  Mood: chill  |  Energy: 0.35  |  Acoustic: True
============================================================

  #1  Library Rain  —  Paper Lanterns     Score: 96.39 / 100
  #2  Midnight Coding  —  LoRoom          Score: 95.06 / 100
  #3  Spacewalk Thoughts  —  Orbit Bloom  Score: 73.78 / 100
  #4  Focus Flow  —  LoRoom              Score: 68.40 / 100
  #5  Coffee Shop Stories  —  Slow Stereo Score: 48.79 / 100

============================================================
  Profile: Deep Intense Rock
  Genre: rock  |  Mood: intense  |  Energy: 0.95  |  Acoustic: False
============================================================

  #1  Storm Runner  —  Voltline           Score: 96.48 / 100
  #2  Gym Hero  —  Max Pulse              Score: 71.83 / 100
  #3  Iron Anthem  —  Forge District      Score: 46.94 / 100
  #4  Night Drive Loop  —  Neon Echo      Score: 43.37 / 100
  #5  Neon Tide  —  Mar Azul              Score: 42.20 / 100

============================================================
  Profile: Edge Case — Classical but High Energy
  Genre: classical  |  Mood: peaceful  |  Energy: 0.9  |  Acoustic: True
============================================================

  #1  Forest Lantern  —  Hollow Pines     Score: 61.03 / 100  (folk/peaceful)
  #2  Dawn Sonata  —  Velvet Quill        Score: 48.55 / 100  (classical/nostalgic)
  #3  Storm Runner  —  Voltline           Score: 45.60 / 100  (rock/intense)
  #4  Gym Hero  —  Max Pulse              Score: 41.39 / 100  (pop/intense)
  #5  Iron Anthem  —  Forge District      Score: 41.34 / 100  (metal/angry)
```

**Why "Gym Hero" keeps appearing for multiple profiles:**
Gym Hero (pop / intense / energy 0.93) sits in a very dense part of the feature space — high energy, high danceability, moderate-to-high valence. Any profile that targets high energy but does not match another song on both mood AND genre will eventually land on Gym Hero as a backup. It is not that the system is "wrong"; it is that Gym Hero is the closest available song for users whose first-choice profile does not have an exact catalog match.

**Why "Sunrise City" scores 96/100 for the pop/happy profile:**
Sunrise City is pop/happy with energy 0.82 — almost exactly what the profile asks for. It earns 28 points for mood match, 20 for genre match, nearly full marks on energy (13.72/14), and solid scores on valence (9.9/10) and danceability (7.28/8). The only slight loss is on tempo, because its 118 BPM is a bit below the expected tempo for energy 0.9.

---

## Experiments You Tried

### Weight-Shift Experiment: Double Energy, Halve Genre

**Change applied:** Energy weight 14 → 28, Genre weight 20 → 10.

**Key findings:**

- Rankings for the Pop, Lofi, and Rock profiles stayed the same at #1 — those profiles are robust to this shift.
- The score gaps between #1 and #5 widened for all three clean profiles, meaning energy became a stronger separator.
- For the edge-case (Classical/High Energy) profile, the classical song (Dawn Sonata) fell out of the top 5 entirely, replaced by rock and metal songs that match the energy target but not the genre or mood.
- **Math finding:** The weight change was not budget-neutral. Doubling energy (+14) and halving genre (-10) added a net 4 points to the total, making the max possible score 104 instead of 100. The Lofi Listener's top result scored 100.39 — over the supposed maximum. Any weight experiment must verify the weights still sum to 100 to keep scores comparable.

**Conclusion:** Doubling energy made the recommendations *more different*, not more accurate. For users with coherent preferences (lofi, rock), the top song did not change. For users with contradictory preferences (classical + high energy), more energy weight just surfaced louder music, ignoring the genre request entirely.

---

## Limitations and Risks

- The catalog has only 18 songs. Niche genres (classical, reggae, country) have a single entry each, so users who prefer those styles will rarely get a genre match.
- Mood and genre are scored with all-or-nothing binary matching. "Indie pop" and "pop" score zero for each other even though they are very similar.
- The system derives expected tempo, valence, and danceability from mood and energy rather than asking the user. This works for coherent profiles but breaks when preferences conflict.
- There is no memory of past recommendations, so the same songs will always appear for the same profile input.
- Artist diversity is not enforced at the ranking stage — two songs by the same artist can appear back-to-back.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

See also: [**reflection.md**](reflection.md) for a profile-by-profile comparison of what changed and why.

Building this recommender made the cost of a "simple" scoring rule very concrete. The mood and genre weights felt intuitive at first, but the edge-case experiment showed that any time two signals point in opposite directions, the system has no way to reason about the conflict — it just adds up numbers and picks the winner. Real recommenders like Spotify invest heavily in learned representations precisely because hand-coded weights cannot handle the full range of listener tastes.

The most surprising result was that the Chill Lofi profile produced the most accurate and confident recommendations while the Classical/High-Energy profile produced the weakest. That asymmetry is entirely a dataset artifact: lofi has multiple well-matched entries, classical has one — and that one is incompatible with the energy preference. A recommender is only as good as its catalog.


---

## 7. `model_card_template.md`

Combines reflection and model card framing from the Module 3 guidance. :contentReference[oaicite:2]{index=2}

```markdown
# 🎧 Model Card - Music Recommender Simulation

## 1. Model Name

Give your recommender a name, for example:

> VibeFinder 1.0

---

## 2. Intended Use

- What is this system trying to do
- Who is it for

Example:

> This model suggests 3 to 5 songs from a small catalog based on a user's preferred genre, mood, and energy level. It is for classroom exploration only, not for real users.

---

## 3. How It Works (Short Explanation)

Describe your scoring logic in plain language.

- What features of each song does it consider
- What information about the user does it use
- How does it turn those into a number

Try to avoid code in this section, treat it like an explanation to a non programmer.

---

## 4. Data

Describe your dataset.

- How many songs are in `data/songs.csv`
- Did you add or remove any songs
- What kinds of genres or moods are represented
- Whose taste does this data mostly reflect

---

## 5. Strengths

Where does your recommender work well

You can think about:
- Situations where the top results "felt right"
- Particular user profiles it served well
- Simplicity or transparency benefits

---

## 6. Limitations and Bias

Where does your recommender struggle

Some prompts:
- Does it ignore some genres or moods
- Does it treat all users as if they have the same taste shape
- Is it biased toward high energy or one genre by default
- How could this be unfair if used in a real product

---

## 7. Evaluation

How did you check your system

Examples:
- You tried multiple user profiles and wrote down whether the results matched your expectations
- You compared your simulation to what a real app like Spotify or YouTube tends to recommend
- You wrote tests for your scoring logic

You do not need a numeric metric, but if you used one, explain what it measures.

---

## 8. Future Work

If you had more time, how would you improve this recommender

Examples:

- Add support for multiple users and "group vibe" recommendations
- Balance diversity of songs instead of always picking the closest match
- Use more features, like tempo ranges or lyric themes

---

## 9. Personal Reflection

A few sentences about what you learned:

- What surprised you about how your system behaved
- How did building this change how you think about real music recommenders
- Where do you think human judgment still matters, even if the model seems "smart"
```
