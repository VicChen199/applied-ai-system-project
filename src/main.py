"""
Command line runner for the Music Recommender Simulation.

Run with:
    python -m src.main
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from urllib import request, error

try:
    from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
except ModuleNotFoundError:
    def load_dotenv() -> None:
        """No-op when python-dotenv is not installed."""
        return None

from .recommender import MOOD_TO_VALENCE, build_listen_link, load_songs, recommend_songs_diverse

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
    "Edge Case - Classical but High Energy": {
        "favorite_genre": "classical",
        "favorite_mood": "peaceful",
        "target_energy": 0.9,
        "likes_acoustic": True,
    },
}

FEEDBACK_OPTIONS = {
    "1": "liked",
    "2": "partial",
    "3": "early_stop",
    "4": "skipped_without_listening",
}

ALLOWED_PROFILE_FIELDS = {"favorite_genre", "favorite_mood", "target_energy", "likes_acoustic"}
PROFILE_NAMES = list(PROFILES.keys())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive agentic music recommender.")
    parser.add_argument("--rounds", type=int, default=5, help="Maximum rounds to run.")
    parser.add_argument(
        "--no-gemini",
        action="store_true",
        help="Use deterministic profile updates instead of Gemini API calls.",
    )
    parser.add_argument(
        "--log-file",
        default="logs/feedback_log.jsonl",
        help="Path for feedback session logs.",
    )
    return parser.parse_args()


def clamp_energy(value: float) -> float:
    return max(0.0, min(1.0, value))


def parse_feedback_choice(choice: str) -> str:
    choice = choice.strip().lower()
    if choice in FEEDBACK_OPTIONS:
        return FEEDBACK_OPTIONS[choice]
    if choice in FEEDBACK_OPTIONS.values():
        return choice
    raise ValueError("Invalid feedback choice")


def extract_json_object(raw_text: str) -> Dict:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found")
    return json.loads(raw_text[start : end + 1])


def normalize_profile_blend(raw_blend: Dict[str, float], fallback: Dict[str, float]) -> Dict[str, float]:
    """Normalize a profile blend to sum to 1.0 over known profile names."""
    cleaned: Dict[str, float] = {name: 0.0 for name in PROFILE_NAMES}
    for key, value in raw_blend.items():
        if key in cleaned:
            try:
                cleaned[key] = max(0.0, float(value))
            except (TypeError, ValueError):
                continue

    total = sum(cleaned.values())
    if total <= 0.0:
        return dict(fallback)
    return {name: cleaned[name] / total for name in PROFILE_NAMES}


def profile_from_blend(profile_blend: Dict[str, float]) -> Dict:
    """Convert weighted profile percentages into a single recommender profile."""
    blend = normalize_profile_blend(profile_blend, fallback={PROFILE_NAMES[0]: 1.0, **{n: 0.0 for n in PROFILE_NAMES[1:]}})
    genre_votes: Dict[str, float] = {}
    mood_votes: Dict[str, float] = {}
    energy = 0.0
    acoustic_prob = 0.0

    for profile_name, weight in blend.items():
        prefs = PROFILES[profile_name]
        genre = prefs["favorite_genre"]
        mood = prefs["favorite_mood"]
        genre_votes[genre] = genre_votes.get(genre, 0.0) + weight
        mood_votes[mood] = mood_votes.get(mood, 0.0) + weight
        energy += weight * float(prefs["target_energy"])
        acoustic_prob += weight * (1.0 if prefs["likes_acoustic"] else 0.0)

    favorite_genre = max(genre_votes, key=genre_votes.get)
    favorite_mood = max(mood_votes, key=mood_votes.get)
    return {
        "favorite_genre": favorite_genre,
        "favorite_mood": favorite_mood,
        "target_energy": clamp_energy(energy),
        "likes_acoustic": acoustic_prob >= 0.5,
    }


def format_blend(profile_blend: Dict[str, float]) -> str:
    items = sorted(profile_blend.items(), key=lambda x: x[1], reverse=True)
    top = [f"{name}: {pct * 100:.0f}%" for name, pct in items if pct > 0.01]
    return ", ".join(top[:3]) if top else "No blend"


def build_starter_recommendations(songs: List[Dict]) -> List[Tuple[Dict, float, str]]:
    """
    Build an intentionally diverse starter set so the user can indicate taste quickly.
    Includes one explicit wildcard song at the end.
    """
    anchor_genres = ["pop", "lofi", "rock", "classical"]
    selected: List[Dict] = []
    used_artists = set()

    for genre in anchor_genres:
        candidate = next(
            (
                s
                for s in songs
                if s["genre"] == genre and s["artist"] not in used_artists and s not in selected
            ),
            None,
        )
        if candidate:
            selected.append(candidate)
            used_artists.add(candidate["artist"])

    wildcard = next(
        (
            s
            for s in songs
            if s["genre"] not in anchor_genres and s["artist"] not in used_artists and s not in selected
        ),
        None,
    )
    if wildcard is None:
        wildcard = next((s for s in songs if s not in selected), None)
    if wildcard:
        selected.append(wildcard)

    # Ensure exactly 5 starter choices if possible.
    if len(selected) < 5:
        for song in songs:
            if song in selected:
                continue
            if song["artist"] in used_artists:
                continue
            selected.append(song)
            used_artists.add(song["artist"])
            if len(selected) >= 5:
                break

    # Mark final slot as wildcard if there are enough songs.
    starter = []
    for idx, song in enumerate(selected[:5]):
        tag = "wildcard candidate" if idx == 4 else "starter candidate"
        starter.append((song, 0.0, tag))
    return starter


def sanitize_profile_update(
    current_profile: Dict,
    proposed_update: Dict,
    allowed_genres: List[str],
    allowed_moods: List[str],
) -> Dict:
    """Return a safe profile update bounded by schema and known value sets."""
    next_profile = dict(current_profile)
    for key, value in proposed_update.items():
        if key not in ALLOWED_PROFILE_FIELDS:
            continue
        if key == "favorite_genre" and str(value) in allowed_genres:
            next_profile[key] = str(value)
        elif key == "favorite_mood" and str(value) in allowed_moods:
            next_profile[key] = str(value)
        elif key == "target_energy":
            try:
                next_profile[key] = clamp_energy(float(value))
            except (TypeError, ValueError):
                continue
        elif key == "likes_acoustic":
            next_profile[key] = bool(value)
    return next_profile


def deterministic_profile_update(current_profile: Dict, selected_song: Dict, feedback: str) -> Dict:
    """Fallback profile updater for repeatable testing and no-Gemini mode."""
    updated = dict(current_profile)
    song_energy = float(selected_song["energy"])
    song_acoustic = float(selected_song["acousticness"])

    if feedback == "liked":
        updated["favorite_genre"] = selected_song["genre"]
        updated["favorite_mood"] = selected_song["mood"]
        updated["target_energy"] = clamp_energy(0.65 * updated["target_energy"] + 0.35 * song_energy)
        updated["likes_acoustic"] = song_acoustic >= 0.5
    elif feedback == "partial":
        updated["target_energy"] = clamp_energy(0.8 * updated["target_energy"] + 0.2 * song_energy)
    elif feedback == "early_stop":
        delta = 0.1 if updated["target_energy"] < song_energy else -0.1
        updated["target_energy"] = clamp_energy(updated["target_energy"] - delta)
    return updated


def closest_profile_name(song: Dict) -> str:
    """Find the closest base profile to a song for deterministic blend fallback."""
    best_name = PROFILE_NAMES[0]
    best_score = -1.0
    for name, prefs in PROFILES.items():
        score = 0.0
        if prefs["favorite_genre"] == song["genre"]:
            score += 1.0
        if prefs["favorite_mood"] == song["mood"]:
            score += 1.0
        score += 1.0 - abs(float(prefs["target_energy"]) - float(song["energy"]))
        target_acoustic = 0.8 if prefs["likes_acoustic"] else 0.2
        score += 1.0 - abs(target_acoustic - float(song["acousticness"]))
        if score > best_score:
            best_score = score
            best_name = name
    return best_name


def deterministic_blend_update(current_blend: Dict[str, float], selected_song: Dict, feedback: str) -> Dict[str, float]:
    """Fallback blend updater when Gemini is unavailable."""
    blend = dict(current_blend)
    target = closest_profile_name(selected_song)

    if feedback == "liked":
        blend[target] = blend.get(target, 0.0) + 0.20
    elif feedback == "partial":
        blend[target] = blend.get(target, 0.0) + 0.08
    elif feedback == "early_stop":
        blend[target] = max(0.0, blend.get(target, 0.0) - 0.12)
    elif feedback == "skipped_without_listening":
        blend[target] = max(0.0, blend.get(target, 0.0) - 0.05)

    return normalize_profile_blend(blend, fallback=current_blend)


def gemini_profile_update(
    api_key: str,
    current_profile: Dict,
    selected_song: Dict,
    feedback: str,
    feedback_history: List[Dict],
) -> Dict:
    """
    Ask Gemini for the next user profile.
    Must return only fields that belong to the user profile schema.
    """
    prompt = {
        "instruction": (
            "You are updating a music user profile after one listening outcome. "
            "Return ONLY JSON with any subset of: "
            "favorite_genre, favorite_mood, target_energy, likes_acoustic."
        ),
        "current_profile": current_profile,
        "selected_song": selected_song,
        "feedback": feedback,
        "feedback_history_recent": feedback_history[-5:],
        "constraints": {
            "target_energy_range": [0.0, 1.0],
            "return_json_only": True,
        },
    }

    payload = json.dumps(
        {
            "contents": [{"parts": [{"text": json.dumps(prompt)}]}],
            "generationConfig": {"temperature": 0.2},
        }
    ).encode("utf-8")
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    req = request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=25) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    text = (
        body.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "{}")
    )
    return extract_json_object(text)


def gemini_profile_blend_update(
    api_key: str,
    current_blend: Dict[str, float],
    selected_song: Dict,
    feedback: str,
    feedback_history: List[Dict],
) -> Dict[str, float]:
    """Ask Gemini for updated profile percentages across base profiles."""
    prompt = {
        "instruction": (
            "Update user taste profile percentages based on song feedback. "
            "Return ONLY JSON with key 'profile_percentages'. "
            "Include all profile names with numeric percentages that sum to 100."
        ),
        "available_profiles": PROFILES,
        "current_profile_percentages": {k: round(v * 100, 2) for k, v in current_blend.items()},
        "selected_song": selected_song,
        "feedback": feedback,
        "recent_feedback_history": feedback_history[-5:],
        "output_schema": {
            "profile_percentages": {
                "High-Energy Pop Fan": "number",
                "Chill Lofi Listener": "number",
                "Deep Intense Rock": "number",
                "Edge Case - Classical but High Energy": "number",
            }
        },
    }

    payload = json.dumps(
        {
            "contents": [{"parts": [{"text": json.dumps(prompt)}]}],
            "generationConfig": {"temperature": 0.2},
        }
    ).encode("utf-8")
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    req = request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=25) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    text = (
        body.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "{}")
    )
    parsed = extract_json_object(text)
    percentages = parsed.get("profile_percentages", {})
    if not isinstance(percentages, dict):
        raise ValueError("Invalid Gemini blend response")
    ratio_blend = {k: float(v) / 100.0 for k, v in percentages.items()}
    return normalize_profile_blend(ratio_blend, fallback=current_blend)


def log_feedback_event(log_file: str, event: Dict) -> None:
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def pick_starting_profile() -> Dict:
    print("\nChoose a starting profile:")
    profile_names = list(PROFILES.keys())
    for idx, name in enumerate(profile_names, start=1):
        print(f"  {idx}. {name}")
    while True:
        raw = input("Enter profile number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(profile_names):
            return dict(PROFILES[profile_names[int(raw) - 1]])
        print("Invalid profile selection. Try again.")


def pick_starting_profile_blend(api_key: str, no_gemini: bool) -> Tuple[Dict[str, float], str]:
    """
    Build initial profile percentages.
    Uses Gemini when available; falls back to manual one-profile initialization.
    """
    if not no_gemini and api_key:
        print("\nDescribe your music taste in 1-2 sentences.")
        print("Example: 'I like upbeat pop and some mellow lofi while studying.'")
        description = input("Taste description (or press Enter to choose manually): ").strip()
        if description:
            prompt = {
                "instruction": (
                    "Infer user profile percentages across the available profiles. "
                    "Return ONLY JSON under key 'profile_percentages' summing to 100."
                ),
                "available_profiles": PROFILES,
                "user_description": description,
                "output_schema": {
                    "profile_percentages": {
                        "High-Energy Pop Fan": "number",
                        "Chill Lofi Listener": "number",
                        "Deep Intense Rock": "number",
                        "Edge Case - Classical but High Energy": "number",
                    }
                },
            }
            try:
                payload = json.dumps(
                    {
                        "contents": [{"parts": [{"text": json.dumps(prompt)}]}],
                        "generationConfig": {"temperature": 0.2},
                    }
                ).encode("utf-8")
                endpoint = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    f"gemini-2.0-flash:generateContent?key={api_key}"
                )
                req = request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
                with request.urlopen(req, timeout=25) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                text = (
                    body.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "{}")
                )
                parsed = extract_json_object(text)
                percentages = parsed.get("profile_percentages", {})
                ratio_blend = {k: float(v) / 100.0 for k, v in percentages.items()}
                return normalize_profile_blend(ratio_blend, fallback={PROFILE_NAMES[0]: 1.0}), "gemini"
            except (ValueError, KeyError, IndexError, error.URLError, TimeoutError, json.JSONDecodeError):
                pass

    base_profile = pick_starting_profile()
    blend = {name: 0.0 for name in PROFILE_NAMES}
    selected_name = next(name for name, prefs in PROFILES.items() if prefs == base_profile)
    blend[selected_name] = 1.0
    return blend, "manual"


def print_round_menu(round_index: int, profile: Dict, recommendations: List) -> None:
    print("\n" + "=" * 70)
    print(f"Round {round_index}")
    print(
        f"Profile -> genre={profile['favorite_genre']} | mood={profile['favorite_mood']} | "
        f"target_energy={profile['target_energy']:.2f} | likes_acoustic={profile['likes_acoustic']}"
    )
    print("-" * 70)
    for idx, (song, _, _) in enumerate(recommendations, start=1):
        print(f"{idx}. {song['title']} - {song['artist']} | genre={song['genre']}")
    print("\nTip: type `details 2` for one song, or `details all` / `metrics` for all songs.")
    print("=" * 70)


def print_song_details(recommendations: List, index: int) -> None:
    song, score, explanation = recommendations[index]
    print("\n" + "-" * 70)
    print(f"Details for #{index + 1}: {song['title']} - {song['artist']}")
    print(f"Score: {score:.2f}")
    print(
        f"Genre={song['genre']} | Mood={song['mood']} | Energy={song['energy']:.2f} | "
        f"Tempo={song['tempo_bpm']} | Valence={song['valence']:.2f} | "
        f"Danceability={song['danceability']:.2f} | Acousticness={song['acousticness']:.2f}"
    )
    print(f"Why: {explanation}")
    print("-" * 70)


def print_all_song_details(recommendations: List) -> None:
    print("\nShowing full metrics for all current recommendations:")
    for idx in range(len(recommendations)):
        print_song_details(recommendations, idx)


def select_song_from_menu(recommendations: List, allow_wildcard_shortcut: bool = False) -> Dict:
    while True:
        raw = input(
            "Select a song number (1-5), `details <number>`, or `details all`: "
        ).strip()
        lowered = raw.lower()
        if allow_wildcard_shortcut and lowered in {"w", "wildcard"} and recommendations:
            return recommendations[min(4, len(recommendations) - 1)][0]
        if lowered in {"details all", "metrics", "all", "show metrics", "show all"}:
            print_all_song_details(recommendations)
            continue
        if lowered.startswith("details ") or lowered.startswith("d "):
            parts = lowered.split()
            if len(parts) == 2 and parts[1].isdigit():
                idx = int(parts[1]) - 1
                if 0 <= idx < len(recommendations):
                    print_song_details(recommendations, idx)
                    continue
        if "<number>" in lowered:
            print("Use a real number, e.g. `details 2`, or use `details all`.")
            continue
        if raw.isdigit() and 1 <= int(raw) <= len(recommendations):
            return recommendations[int(raw) - 1][0]
        print("Invalid song choice. Try again.")


def initial_blend_from_song(selected_song: Dict) -> Dict[str, float]:
    """Seed a blended profile from a starter-song choice."""
    closest = closest_profile_name(selected_song)
    blend = {name: 0.10 for name in PROFILE_NAMES}
    blend[closest] = 0.70
    return normalize_profile_blend(blend, fallback={PROFILE_NAMES[0]: 1.0})


def gemini_initial_blend_from_song(
    api_key: str,
    selected_song: Dict,
    starter_options: List[Dict],
) -> Dict[str, float]:
    """Infer initial profile percentages from the starter choice."""
    prompt = {
        "instruction": (
            "Infer initial user profile percentages from their first chosen starter song. "
            "Return ONLY JSON with key 'profile_percentages' summing to 100."
        ),
        "available_profiles": PROFILES,
        "selected_song": selected_song,
        "starter_options": starter_options,
        "output_schema": {
            "profile_percentages": {
                "High-Energy Pop Fan": "number",
                "Chill Lofi Listener": "number",
                "Deep Intense Rock": "number",
                "Edge Case - Classical but High Energy": "number",
            }
        },
    }
    payload = json.dumps(
        {
            "contents": [{"parts": [{"text": json.dumps(prompt)}]}],
            "generationConfig": {"temperature": 0.2},
        }
    ).encode("utf-8")
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    req = request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=25) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    text = (
        body.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "{}")
    )
    parsed = extract_json_object(text)
    percentages = parsed.get("profile_percentages", {})
    if not isinstance(percentages, dict):
        raise ValueError("Invalid Gemini initial blend response")
    ratio_blend = {k: float(v) / 100.0 for k, v in percentages.items()}
    return normalize_profile_blend(ratio_blend, fallback=initial_blend_from_song(selected_song))


def collect_feedback() -> str:
    print("\nHow did this song go?")
    print("  1. liked")
    print("  2. partial")
    print("  3. early_stop")
    print("  4. skipped_without_listening")
    while True:
        raw = input("Enter feedback (1-4 or label): ").strip()
        try:
            return parse_feedback_choice(raw)
        except ValueError:
            print("Invalid feedback choice. Try again.")


def prompt_next_step_after_feedback() -> str:
    """
    Ask whether to refresh recommendations or keep the current set.
    Returns: "new", "same", or "quit".
    """
    print("\nWhat would you like to do next?")
    print("  1. Get new recommendations")
    print("  2. Keep current recommendations and give more feedback")
    print("  3. End session")
    while True:
        raw = input("Enter 1/2/3 (or new/same/quit): ").strip().lower()
        if raw in {"1", "new", "next"}:
            return "new"
        if raw in {"2", "same", "old", "current"}:
            return "same"
        if raw in {"3", "quit", "q", "end"}:
            return "quit"
        print("Invalid choice. Try again.")


def run_session(songs: List[Dict], args: argparse.Namespace) -> None:
    feedback_history: List[Dict] = []
    profile: Dict = {}
    allowed_genres = sorted({song["genre"] for song in songs})
    allowed_moods = sorted(set(MOOD_TO_VALENCE.keys()) | {song["mood"] for song in songs})
    api_key = os.getenv("GEMINI_API_KEY", "")

    starter_recs = build_starter_recommendations(songs)
    print("\nChoose a starter song to bootstrap your taste profile:")
    print("(Songs are intentionally different; option 5 is the wildcard.)")
    for idx, (song, _, _) in enumerate(starter_recs, start=1):
        wildcard_tag = " [Wildcard]" if idx == min(5, len(starter_recs)) else ""
        print(f"  {idx}. {song['title']} - {song['artist']} | genre={song['genre']}{wildcard_tag}")
    print("Tip: type `details 2`, `details all`, or `w` for wildcard.")

    starter_song = select_song_from_menu(starter_recs, allow_wildcard_shortcut=True)
    if args.no_gemini or not api_key:
        profile_blend = initial_blend_from_song(starter_song)
        init_source = "starter_song_deterministic"
    else:
        try:
            profile_blend = gemini_initial_blend_from_song(
                api_key=api_key,
                selected_song=starter_song,
                starter_options=[item[0] for item in starter_recs],
            )
            init_source = "starter_song_gemini"
        except (ValueError, KeyError, IndexError, error.URLError, TimeoutError, json.JSONDecodeError):
            profile_blend = initial_blend_from_song(starter_song)
            init_source = "starter_song_fallback"

    profile = profile_from_blend(profile_blend)
    profile = sanitize_profile_update(profile, profile, allowed_genres, allowed_moods)
    print(f"\nInitial profile blend source: {init_source}")
    print(f"Initial profile mix -> {format_blend(profile_blend)}")

    round_index = 1
    recommendations = recommend_songs_diverse(profile, songs, k=5, max_per_artist=1)
    if not recommendations:
        print("No recommendations available.")
        return

    while round_index <= args.rounds:
        print_round_menu(round_index, profile, recommendations)
        selected_song = select_song_from_menu(recommendations)
        listen_url = build_listen_link(selected_song, provider="youtube")
        print(f"\nListen link: {listen_url}")

        feedback = collect_feedback()
        previous_profile = dict(profile)
        previous_blend = dict(profile_blend)

        if args.no_gemini or not api_key:
            profile_blend = deterministic_blend_update(profile_blend, selected_song, feedback)
            update_source = "deterministic_blend"
        else:
            try:
                profile_blend = gemini_profile_blend_update(
                    api_key=api_key,
                    current_blend=profile_blend,
                    selected_song=selected_song,
                    feedback=feedback,
                    feedback_history=feedback_history,
                )
                update_source = "gemini_blend"
            except (ValueError, KeyError, IndexError, error.URLError, TimeoutError, json.JSONDecodeError):
                profile_blend = deterministic_blend_update(profile_blend, selected_song, feedback)
                update_source = "deterministic_blend_fallback"

        profile = profile_from_blend(profile_blend)
        profile = sanitize_profile_update(profile, profile, allowed_genres, allowed_moods)

        event = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "round": round_index,
            "feedback": feedback,
            "song_id": selected_song["id"],
            "song_title": selected_song["title"],
            "song_artist": selected_song["artist"],
            "listen_url": listen_url,
            "profile_before": previous_profile,
            "profile_after": profile,
            "profile_blend_before": previous_blend,
            "profile_blend_after": profile_blend,
            "update_source": update_source,
        }
        feedback_history.append(event)
        log_feedback_event(args.log_file, event)
        print(f"Updated profile source: {update_source}")
        print(f"Updated profile mix -> {format_blend(profile_blend)}")

        next_step = prompt_next_step_after_feedback()
        if next_step == "quit":
            break
        if next_step == "new":
            round_index += 1
            recommendations = recommend_songs_diverse(profile, songs, k=5, max_per_artist=1)
            if not recommendations:
                print("No recommendations available.")
                break

    print("\nSession complete.")


def main() -> None:
    load_dotenv()
    args = parse_args()
    songs = load_songs("data/songs.csv")
    run_session(songs=songs, args=args)


if __name__ == "__main__":
    main()
