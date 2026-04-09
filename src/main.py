"""
Command line runner for the Music Recommender Simulation.

Run with:
    python -m src.main
"""

from .recommender import load_songs, recommend_songs


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------
PROFILES = {
    "High-Energy Pop Fan": {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.9,
        "likes_acoustic": False,
    },
    "Chill Lofi Listener": {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.35,
        "likes_acoustic": True,
    },
    "Deep Intense Rock": {
        "favorite_genre": "rock",
        "favorite_mood": "intense",
        "target_energy": 0.95,
        "likes_acoustic": False,
    },
    # Edge case: classical genre is inherently low-energy, but user targets high energy.
    # This tests whether the system handles conflicting preferences gracefully.
    "Edge Case — Classical but High Energy": {
        "favorite_genre": "classical",
        "favorite_mood": "peaceful",
        "target_energy": 0.9,
        "likes_acoustic": True,
    },
}


def print_recommendations(label: str, user_prefs: dict, songs: list, k: int = 5) -> None:
    """Print a formatted recommendation block for one user profile."""
    recommendations = recommend_songs(user_prefs, songs, k=k)
    print("\n" + "=" * 60)
    print(f"  Profile: {label}")
    print(
        f"  Genre: {user_prefs['favorite_genre']}  |  "
        f"Mood: {user_prefs['favorite_mood']}  |  "
        f"Energy: {user_prefs['target_energy']}  |  "
        f"Acoustic: {user_prefs['likes_acoustic']}"
    )
    print("=" * 60)
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n  #{rank}  {song['title']}  —  {song['artist']}")
        print(f"       Score : {score:.2f} / 100")
        print(f"       Genre : {song['genre']}  |  Mood: {song['mood']}")
        print(f"       Why   : {explanation}")
    print()


def main() -> None:
    songs = load_songs("data/songs.csv")

    for label, prefs in PROFILES.items():
        print_recommendations(label, prefs, songs)


if __name__ == "__main__":
    main()
