from src.main import (
    deterministic_profile_update,
    parse_feedback_choice,
    prompt_next_step_after_feedback,
    sanitize_profile_update,
)
from src.recommender import build_listen_link, recommend_songs_diverse


def test_parse_feedback_choice_accepts_numeric_and_label():
    assert parse_feedback_choice("1") == "liked"
    assert parse_feedback_choice("partial") == "partial"


def test_sanitize_profile_update_rejects_unknown_fields_and_clamps_energy():
    current = {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.5,
        "likes_acoustic": False,
    }
    proposed = {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 9.1,
        "likes_acoustic": True,
        "hack_field": "ignore-me",
    }
    updated = sanitize_profile_update(
        current_profile=current,
        proposed_update=proposed,
        allowed_genres=["pop", "lofi"],
        allowed_moods=["happy", "chill"],
    )
    assert updated["favorite_genre"] == "lofi"
    assert updated["favorite_mood"] == "chill"
    assert updated["target_energy"] == 1.0
    assert updated["likes_acoustic"] is True
    assert "hack_field" not in updated


def test_deterministic_profile_update_changes_profile_when_liked():
    current = {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.3,
        "likes_acoustic": False,
    }
    song = {
        "genre": "rock",
        "mood": "intense",
        "energy": 0.9,
        "acousticness": 0.8,
    }
    updated = deterministic_profile_update(current, song, "liked")
    assert updated["favorite_genre"] == "rock"
    assert updated["favorite_mood"] == "intense"
    assert updated["target_energy"] > current["target_energy"]
    assert updated["likes_acoustic"] is True


def test_recommend_songs_diverse_limits_duplicate_artists():
    songs = [
        {
            "id": 1,
            "title": "A",
            "artist": "Same Artist",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            "tempo_bpm": 120,
            "valence": 0.8,
            "danceability": 0.8,
            "acousticness": 0.2,
        },
        {
            "id": 2,
            "title": "B",
            "artist": "Same Artist",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.75,
            "tempo_bpm": 118,
            "valence": 0.78,
            "danceability": 0.75,
            "acousticness": 0.25,
        },
        {
            "id": 3,
            "title": "C",
            "artist": "Other Artist",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.7,
            "tempo_bpm": 116,
            "valence": 0.76,
            "danceability": 0.7,
            "acousticness": 0.3,
        },
    ]
    user = {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.8,
        "likes_acoustic": False,
    }
    ranked = recommend_songs_diverse(user, songs, k=2, max_per_artist=1)
    artists = [song["artist"] for song, _, _ in ranked]
    assert len(ranked) == 2
    assert len(set(artists)) == 2


def test_build_listen_link_contains_encoded_song_query():
    song = {"title": "Sunrise City", "artist": "Neon Echo"}
    url = build_listen_link(song)
    assert "youtube.com" in url
    assert "Sunrise+City+Neon+Echo" in url


def test_prompt_next_step_after_feedback_accepts_aliases(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "same")
    assert prompt_next_step_after_feedback() == "same"
