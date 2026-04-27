import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from urllib.parse import quote_plus

# Maps a mood string to an expected valence (0.0–1.0) for similarity scoring.
MOOD_TO_VALENCE = {
    "happy": 0.85,
    "euphoric": 0.90,
    "playful": 0.80,
    "romantic": 0.70,
    "confident": 0.65,
    "focused": 0.60,
    "relaxed": 0.65,
    "chill": 0.60,
    "peaceful": 0.55,
    "nostalgic": 0.50,
    "moody": 0.40,
    "intense": 0.45,
    "heartbroken": 0.30,
    "angry": 0.25,
    "sad": 0.20,
}


@dataclass
class Song:
    """Represents a song and its audio/metadata attributes."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """Represents a user's taste preferences."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


class Recommender:
    """OOP implementation of the recommendation logic."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5, max_per_artist: int = 1) -> List[Song]:
        """Return top-k songs with artist diversity constraints applied."""
        user_prefs = {
            "favorite_genre": user.favorite_genre,
            "favorite_mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        }
        song_dicts = [vars(song) for song in self.songs]
        ranked = recommend_songs_diverse(
            user_prefs=user_prefs,
            songs=song_dicts,
            k=k,
            max_per_artist=max_per_artist,
        )
        id_to_song = {song.id: song for song in self.songs}
        return [id_to_song[item[0]["id"]] for item in ranked if item[0]["id"] in id_to_song]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable explanation of why the song was recommended."""
        user_prefs = {
            "favorite_genre": user.favorite_genre,
            "favorite_mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        }
        _, reasons = score_song(user_prefs, vars(song))
        return "; ".join(reasons)


def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file and return a list of dicts with typed numeric values."""
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append({
                "id": int(row["id"]),
                "title": row["title"],
                "artist": row["artist"],
                "genre": row["genre"],
                "mood": row["mood"],
                "energy": float(row["energy"]),
                "tempo_bpm": float(row["tempo_bpm"]),
                "valence": float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })
    print(f"Loaded songs: {len(songs)}")
    return songs


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score a single song against user preferences, returning (total_score, reasons)."""
    score = 0.0
    reasons = []

    # Resolve preference keys — supports both short ("genre") and full ("favorite_genre") forms.
    genre = user_prefs.get("favorite_genre") or user_prefs.get("genre", "")
    mood = user_prefs.get("favorite_mood") or user_prefs.get("mood", "")
    target_energy = float(user_prefs.get("target_energy") or user_prefs.get("energy", 0.5))
    likes_acoustic = user_prefs.get("likes_acoustic", False)

    # 1. Mood match — 28 pts
    if song["mood"] == mood:
        score += 28.0
        reasons.append("mood match (+28.0)")

    # 2. Genre match — 20 pts
    if song["genre"] == genre:
        score += 20.0
        reasons.append("genre match (+20.0)")

    # 3. Energy similarity — 14 pts
    energy_pts = round(max(0.0, 1.0 - abs(target_energy - song["energy"])) * 14.0, 2)
    score += energy_pts
    reasons.append(f"energy similarity (+{energy_pts})")

    # 4. Tempo similarity — 10 pts (expected BPM derived from target energy)
    expected_bpm = 60.0 + target_energy * 110.0  # energy 0 → 60 BPM, energy 1 → 170 BPM
    tempo_pts = round(max(0.0, 1.0 - abs(expected_bpm - song["tempo_bpm"]) / 110.0) * 10.0, 2)
    score += tempo_pts
    reasons.append(f"tempo similarity (+{tempo_pts})")

    # 5. Valence similarity — 10 pts (expected valence derived from mood)
    target_valence = MOOD_TO_VALENCE.get(mood, 0.5)
    valence_pts = round(max(0.0, 1.0 - abs(target_valence - song["valence"])) * 10.0, 2)
    score += valence_pts
    reasons.append(f"valence similarity (+{valence_pts})")

    # 6. Danceability similarity — 8 pts (expected danceability derived from energy)
    target_dance = 0.3 + target_energy * 0.5  # energy 0 → 0.30, energy 1 → 0.80
    dance_pts = round(max(0.0, 1.0 - abs(target_dance - song["danceability"])) * 8.0, 2)
    score += dance_pts
    reasons.append(f"danceability similarity (+{dance_pts})")

    # 7. Acousticness similarity — 6 pts
    target_acoustic = 0.8 if likes_acoustic else 0.2
    acoustic_pts = round(max(0.0, 1.0 - abs(target_acoustic - song["acousticness"])) * 6.0, 2)
    score += acoustic_pts
    reasons.append(f"acousticness similarity (+{acoustic_pts})")

    # 8. Artist diversity — 4 pts (constant at single-song level)
    score += 4.0
    reasons.append("artist diversity (+4.0)")

    return round(score, 2), reasons


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score all songs, sort from highest to lowest, and return the top k results."""
    # sorted() returns a new sorted list without mutating the original;
    # .sort() would mutate the list in place — sorted() is safer here.
    scored = [(song, *score_song(user_prefs, song)) for song in songs]
    ranked = sorted(scored, key=lambda x: x[1], reverse=True)
    return [(song, score, "; ".join(reasons)) for song, score, reasons in ranked[:k]]


def recommend_songs_diverse(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    max_per_artist: int = 1,
    include_adjacent: bool = True,
    min_unique_genres: int = 2,
    min_relative_score: float = 0.85,
    adjacent_min_relative_score: float = 0.75,
) -> List[Tuple[Dict, float, str]]:
    """
    Return top-k songs while limiting repeats from the same artist.
    Optionally inject one "adjacent" song that is near-fit but not exact-fit.
    Also enforces a minimum number of unique genres when possible.
    Diversity substitutions are bounded by score floors to avoid straying too far.
    A single adjacent/wildcard slot can use a lower floor.
    Falls back to highest remaining scores if diversity constraint is too strict.
    """
    ranked = recommend_songs(user_prefs, songs, k=len(songs))
    artist_counts: Dict[str, int] = {}
    selected: List[Tuple[Dict, float, str]] = []
    deferred: List[Tuple[Dict, float, str]] = []

    for item in ranked:
        song, _, _ = item
        artist = song.get("artist", "")
        if artist_counts.get(artist, 0) < max_per_artist:
            selected.append(item)
            artist_counts[artist] = artist_counts.get(artist, 0) + 1
        else:
            deferred.append(item)
        if len(selected) >= k:
            break

    for item in deferred:
        selected.append(item)
        if len(selected) >= k:
            break

    if include_adjacent and selected:
        genre = user_prefs.get("favorite_genre") or user_prefs.get("genre", "")
        mood = user_prefs.get("favorite_mood") or user_prefs.get("mood", "")
        top_score = selected[0][1]
        selected_ids = {item[0].get("id") for item in selected}

        # "Adjacent" means not an exact genre+mood match, but still reasonably close.
        score_floor = top_score * adjacent_min_relative_score
        adjacent_pool = [
            item for item in ranked
            if item[0].get("id") not in selected_ids
            and not (item[0].get("genre") == genre and item[0].get("mood") == mood)
            and item[1] >= score_floor
        ]
        if adjacent_pool:
            adjacent_choice = adjacent_pool[0]
            replaced = False
            for idx in range(len(selected) - 1, -1, -1):
                song = selected[idx][0]
                if song.get("genre") == genre and song.get("mood") == mood:
                    selected[idx] = adjacent_choice
                    replaced = True
                    break
            if not replaced and len(selected) >= k:
                selected[-1] = adjacent_choice

    # Ensure at least N unique genres in the final set when possible.
    if min_unique_genres > 1 and selected:
        selected_genres = {item[0].get("genre") for item in selected}
        if len(selected_genres) < min_unique_genres:
            selected_ids = {item[0].get("id") for item in selected}
            top_score = selected[0][1]
            score_floor = top_score * adjacent_min_relative_score
            needed = min_unique_genres - len(selected_genres)
            candidates = [
                item
                for item in ranked
                if item[0].get("id") not in selected_ids
                and item[0].get("genre") not in selected_genres
                and item[1] >= score_floor
            ]
            for candidate in candidates:
                replace_idx = None
                for idx in range(len(selected) - 1, -1, -1):
                    if selected[idx][0].get("genre") in selected_genres:
                        replace_idx = idx
                        break
                if replace_idx is None:
                    break
                selected[replace_idx] = candidate
                selected_genres = {item[0].get("genre") for item in selected}
                needed = min_unique_genres - len(selected_genres)
                if needed <= 0:
                    break

    # Final hard fallback: force one cross-genre slot if any alternative exists.
    # This prevents all-5-same-genre outputs in live CLI rounds.
    if min_unique_genres > 1 and selected:
        selected_genres = {item[0].get("genre") for item in selected}
        if len(selected_genres) < min_unique_genres:
            selected_ids = {item[0].get("id") for item in selected}
            forced_candidate = next(
                (
                    item for item in ranked
                    if item[0].get("id") not in selected_ids
                    and item[0].get("genre") not in selected_genres
                ),
                None,
            )
            if forced_candidate is not None:
                selected[-1] = forced_candidate

    return selected


def build_listen_link(song: Dict, provider: str = "youtube") -> str:
    """Build a searchable listen URL for a song title + artist."""
    query = quote_plus(f"{song.get('title', '')} {song.get('artist', '')}".strip())
    if provider == "spotify":
        return f"https://open.spotify.com/search/{query}"
    return f"https://www.youtube.com/results?search_query={query}"
