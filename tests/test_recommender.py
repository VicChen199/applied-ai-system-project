from src.recommender import Song, UserProfile, Recommender

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_recommend_enforces_artist_diversity_when_possible():
    songs = [
        Song(
            id=1,
            title="Artist A Song 1",
            artist="Artist A",
            genre="pop",
            mood="happy",
            energy=0.82,
            tempo_bpm=122,
            valence=0.84,
            danceability=0.81,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Artist A Song 2",
            artist="Artist A",
            genre="pop",
            mood="happy",
            energy=0.80,
            tempo_bpm=120,
            valence=0.82,
            danceability=0.79,
            acousticness=0.22,
        ),
        Song(
            id=3,
            title="Artist B Song 1",
            artist="Artist B",
            genre="pop",
            mood="happy",
            energy=0.78,
            tempo_bpm=118,
            valence=0.80,
            danceability=0.77,
            acousticness=0.24,
        ),
    ]
    rec = Recommender(songs)
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )

    results = rec.recommend(user, k=2, max_per_artist=1)
    artists = [song.artist for song in results]
    assert len(results) == 2
    assert len(set(artists)) == 2


def test_recommend_includes_one_adjacent_song():
    songs = [
        Song(
            id=1,
            title="Exact 1",
            artist="Artist A",
            genre="pop",
            mood="happy",
            energy=0.82,
            tempo_bpm=122,
            valence=0.84,
            danceability=0.81,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Exact 2",
            artist="Artist B",
            genre="pop",
            mood="happy",
            energy=0.80,
            tempo_bpm=120,
            valence=0.82,
            danceability=0.79,
            acousticness=0.22,
        ),
        Song(
            id=3,
            title="Adjacent Mood",
            artist="Artist C",
            genre="pop",
            mood="playful",
            energy=0.79,
            tempo_bpm=121,
            valence=0.80,
            danceability=0.78,
            acousticness=0.23,
        ),
        Song(
            id=4,
            title="Far Song",
            artist="Artist D",
            genre="metal",
            mood="angry",
            energy=0.95,
            tempo_bpm=165,
            valence=0.20,
            danceability=0.50,
            acousticness=0.05,
        ),
    ]
    rec = Recommender(songs)
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    results = rec.recommend(user, k=3, max_per_artist=1)
    assert len(results) == 3
    # At least one recommendation should be adjacent (not exact genre+mood match).
    assert any(not (s.genre == "pop" and s.mood == "happy") for s in results)


def test_recommend_contains_at_least_two_genres_when_available():
    songs = [
        Song(
            id=1,
            title="Pop Exact 1",
            artist="Artist A",
            genre="pop",
            mood="happy",
            energy=0.82,
            tempo_bpm=122,
            valence=0.84,
            danceability=0.81,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Pop Exact 2",
            artist="Artist B",
            genre="pop",
            mood="happy",
            energy=0.80,
            tempo_bpm=120,
            valence=0.82,
            danceability=0.79,
            acousticness=0.22,
        ),
        Song(
            id=3,
            title="Rock Near",
            artist="Artist C",
            genre="rock",
            mood="confident",
            energy=0.78,
            tempo_bpm=118,
            valence=0.70,
            danceability=0.70,
            acousticness=0.18,
        ),
    ]
    rec = Recommender(songs)
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    results = rec.recommend(user, k=3, max_per_artist=1)
    assert len(results) == 3
    assert len({song.genre for song in results}) >= 2


def test_recommend_diversity_does_not_stray_too_far_from_top_score():
    songs = [
        Song(
            id=1,
            title="Top Match",
            artist="Artist A",
            genre="pop",
            mood="happy",
            energy=0.80,
            tempo_bpm=120,
            valence=0.85,
            danceability=0.82,
            acousticness=0.20,
        ),
        Song(
            id=2,
            title="Close Adjacent",
            artist="Artist B",
            genre="indie pop",
            mood="playful",
            energy=0.78,
            tempo_bpm=118,
            valence=0.82,
            danceability=0.79,
            acousticness=0.25,
        ),
        Song(
            id=3,
            title="Far Candidate",
            artist="Artist C",
            genre="classical",
            mood="peaceful",
            energy=0.25,
            tempo_bpm=65,
            valence=0.50,
            danceability=0.22,
            acousticness=0.95,
        ),
    ]
    user = {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.8,
        "likes_acoustic": False,
    }
    ranked = recommend_songs_diverse(
        user_prefs=user,
        songs=[vars(s) for s in songs],
        k=2,
        max_per_artist=1,
        include_adjacent=True,
        min_unique_genres=2,
        min_relative_score=0.85,
    )
    assert len(ranked) == 2
    top_score = ranked[0][1]
    assert all(score >= top_score * 0.85 for _, score, _ in ranked)


def test_recommend_uses_lower_floor_for_single_cross_genre_slot():
    user = {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.45,
        "likes_acoustic": True,
    }
    songs = [
        # Very strong lofi matches
        {
            "id": 1, "title": "Lofi A", "artist": "A", "genre": "lofi", "mood": "chill",
            "energy": 0.45, "tempo_bpm": 78, "valence": 0.60, "danceability": 0.58, "acousticness": 0.84
        },
        {
            "id": 2, "title": "Lofi B", "artist": "B", "genre": "lofi", "mood": "chill",
            "energy": 0.44, "tempo_bpm": 79, "valence": 0.61, "danceability": 0.57, "acousticness": 0.85
        },
        {
            "id": 3, "title": "Lofi C", "artist": "C", "genre": "lofi", "mood": "focused",
            "energy": 0.46, "tempo_bpm": 80, "valence": 0.58, "danceability": 0.56, "acousticness": 0.82
        },
        {
            "id": 4, "title": "Lofi D", "artist": "D", "genre": "lofi", "mood": "peaceful",
            "energy": 0.43, "tempo_bpm": 76, "valence": 0.59, "danceability": 0.55, "acousticness": 0.86
        },
        # Cross-genre option that should qualify for 0.75 floor but might miss 0.85
        {
            "id": 5, "title": "Indie Adjacent", "artist": "E", "genre": "indie pop", "mood": "chill",
            "energy": 0.55, "tempo_bpm": 96, "valence": 0.68, "danceability": 0.64, "acousticness": 0.55
        },
    ]
    ranked = recommend_songs_diverse(
        user_prefs=user,
        songs=songs,
        k=5,
        max_per_artist=1,
        include_adjacent=True,
        min_unique_genres=2,
        min_relative_score=0.85,
        adjacent_min_relative_score=0.75,
    )
    genres = {song["genre"] for song, _, _ in ranked}
    assert len(genres) >= 2


def test_recommend_forces_cross_genre_when_available_even_if_far():
    user = {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.45,
        "likes_acoustic": True,
    }
    songs = [
        {
            "id": 1, "title": "Lofi A", "artist": "A", "genre": "lofi", "mood": "chill",
            "energy": 0.45, "tempo_bpm": 78, "valence": 0.60, "danceability": 0.58, "acousticness": 0.84
        },
        {
            "id": 2, "title": "Lofi B", "artist": "B", "genre": "lofi", "mood": "chill",
            "energy": 0.44, "tempo_bpm": 79, "valence": 0.61, "danceability": 0.57, "acousticness": 0.85
        },
        {
            "id": 3, "title": "Lofi C", "artist": "C", "genre": "lofi", "mood": "focused",
            "energy": 0.46, "tempo_bpm": 80, "valence": 0.58, "danceability": 0.56, "acousticness": 0.82
        },
        {
            "id": 4, "title": "Lofi D", "artist": "D", "genre": "lofi", "mood": "peaceful",
            "energy": 0.43, "tempo_bpm": 76, "valence": 0.59, "danceability": 0.55, "acousticness": 0.86
        },
        # Very far cross-genre option; should still be used by hard fallback.
        {
            "id": 5, "title": "Metal Far", "artist": "E", "genre": "metal", "mood": "angry",
            "energy": 0.95, "tempo_bpm": 166, "valence": 0.20, "danceability": 0.50, "acousticness": 0.05
        },
    ]
    ranked = recommend_songs_diverse(
        user_prefs=user,
        songs=songs,
        k=5,
        max_per_artist=1,
        include_adjacent=True,
        min_unique_genres=2,
        min_relative_score=0.85,
        adjacent_min_relative_score=0.75,
    )
    genres = {song["genre"] for song, _, _ in ranked}
    assert len(genres) >= 2
