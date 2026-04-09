# Reflection: Profile Comparison Notes

## Profile 1 vs Profile 2 — High-Energy Pop Fan vs Chill Lofi Listener

These two profiles are almost opposites, and the results show it clearly.

The Pop Fan (energy 0.9) gets "Sunrise City" at the top. The Lofi Listener (energy 0.35) gets
"Library Rain" at the top. Not a single song appears in both top-5 lists. That is exactly what
should happen — the system is doing its job of separating high-energy and low-energy taste.

What is interesting is the *confidence gap*. The Lofi Listener's top song scores 96.39, and the
second-place song (Midnight Coding) scores 95.06 — almost identical. Two songs fit equally well.
The Pop Fan's top song scores 94.61, but second place drops to 73.00 — a much larger gap. That
tells us there is only one song in the catalog that perfectly matches the pop/happy/high-energy
profile, whereas the chill/lofi profile has two strong options.

In plain language: if you are a lofi listener, this recommender has good choices for you. If you
are a pop fan, the first pick is great, but the catalog runs out of good matches quickly.

---

## Profile 1 vs Profile 3 — High-Energy Pop Fan vs Deep Intense Rock

Both profiles want high energy (0.9 vs 0.95). That is their main similarity. But mood and genre
are completely different: pop/happy vs rock/intense.

The results diverge immediately at #1: "Sunrise City" for pop, "Storm Runner" for rock. No overlap
in the top 3. This confirms that mood and genre (worth 48 combined points) are the dominant
signals that separate users with similar energy preferences.

The more interesting finding is what shows up at #3 for each profile. For the Pop Fan it is
"Gym Hero" (pop/intense — genre match but wrong mood). For the Rock profile it is also "Gym Hero"
(pop/intense — mood match but wrong genre). Gym Hero appears for both users but for different
reasons. This is a realistic outcome: a high-energy, danceable song will appeal to multiple taste
profiles even if none of those profiles describe it perfectly. In a real app, "Gym Hero" would be
a crowd-pleaser — a song that gets recommended to many types of users because it sits in a dense
part of the feature space.

---

## Profile 3 vs Profile 4 — Deep Intense Rock vs Edge Case (Classical but High Energy)

Both profiles want high energy (~0.9–0.95). One wants rock/intense; the other wants
classical/peaceful. This is where the system breaks down for Profile 4.

The Rock profile produces tight, sensible results: Storm Runner (#1, 96.48), then mood-matched
songs fill the rest. The Edge Case profile's best score is only 61.03, and no classical song
appears in the top 3. Why?

Think of it this way. The system gives 28 points for mood match and 20 points for genre match.
The only classical song in the catalog (Dawn Sonata) has energy 0.22, which is almost the
opposite of what the user wants (0.9). That energy gap costs it about 9 out of 14 energy points,
nearly all of the tempo points, and most of the danceability points. So even though Dawn Sonata
matches on genre, it cannot recover enough points to beat a folk song (Forest Lantern) that
matches on mood.

In plain language: if you tell this system you love classical music but you also want high energy,
it will look at every song in the catalog and say "none of these really fit — here is the least
wrong option." That is not a recommendation; it is a polite shrug. The lesson is that a
recommender can only surface preferences that actually exist in the dataset. If there are no
high-energy classical songs in the catalog, the system cannot magically invent one.

---

## Weight-Shift Experiment — What Changed and Why

Doubling the energy weight (14 → 28) and halving the genre weight (20 → 10) changed the
rankings most visibly for the edge-case profile. Before the experiment, Dawn Sonata (classical,
low energy) ranked #2. After the experiment it fell out of the top 5 entirely, replaced by
Storm Runner, Gym Hero, and Iron Anthem — all high-energy songs from rock/pop/metal.

That result is mathematically correct: when energy is worth twice as much, a song's energy gap
hurts twice as hard. Dawn Sonata's energy mismatch became too expensive to overcome even with the
genre bonus.

For the clean profiles (Pop Fan, Lofi Listener, Rock Fan), the #1 result did not change, but the
gaps widened. This tells us those profiles are robust — the correct song wins under multiple
weight configurations. Only the edge-case profile was sensitive enough to the weight change to
produce a meaningfully different list.

One important side-effect: the total possible score became 104 instead of 100 (because +14 from
energy and -10 from genre is a net gain of 4). The Lofi Listener's top song scored 100.39 — over
the supposed maximum. This shows that weight experiments must always check that the weights still
sum to the intended total, or scores across profiles become incomparable.
