
import json
import re
from pathlib import Path

DATA_FILE = Path("album_result.json")

EXPECTED_SONGS = [
    "Lucky Star",
    "Borderline",
    "Burning Up",
    "I Know It",
    "Holiday",
    "Think of Me",
    "Physical Attraction",
    "Everybody",
]


def validate_album():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    errors = []

    songs = data.get("songs", [])

    if data.get("artist") != "Madonna":
        errors.append("Artist incorrect")

    if data.get("album_name") != "Madonna":
        errors.append("Album name incorrect")

    if len(songs) != 8:
        errors.append(f"Expected 8 songs, found {len(songs)}")

    actual_names = [song.get("name") for song in songs]

    if actual_names != EXPECTED_SONGS:
        errors.append(
            f"Song order mismatch: {actual_names}"
        )

    total_tokens = 0

    for index, song in enumerate(songs, start=1):
        name = song.get("name", "UNKNOWN")

        chars = song.get("lyrics_length_chars")
        words = song.get("lyrics_length_words")
        tokens = song.get("lyrics_length_tokens")
        ratio = song.get("tokens_per_word")
        lyrics_hash = song.get("lyrics_hash")

        for field, value in [
            ("lyrics_length_chars", chars),
            ("lyrics_length_words", words),
            ("lyrics_length_tokens", tokens),
        ]:
            if type(value) is not int or value <= 0:
                errors.append(
                    f"{name}: invalid {field}: {value}"
                )

        if isinstance(chars, int) and chars < 100:
            errors.append(f"{name}: suspiciously short lyrics")

        if isinstance(words, int) and isinstance(tokens, int):
            if words > 0 and tokens > 0:
                expected_ratio = tokens / words

                if not isinstance(ratio, (int, float)):
                    errors.append(f"{name}: invalid tokens_per_word")
                elif abs(ratio - expected_ratio) > 0.02:
                    errors.append(
                        f"{name}: tokens_per_word mismatch"
                    )

        if not isinstance(lyrics_hash, str) or not lyrics_hash.strip():
            errors.append(f"{name}: missing lyrics_hash")
        elif not re.fullmatch(r"[0-9a-fA-F]{32,128}", lyrics_hash):
            errors.append(f"{name}: unexpected hash format")

        if type(tokens) is int and tokens > 0:
            total_tokens += tokens

        print(f"[{index}/8] {name}: checked")

    reported_total = data.get("total_tokens_all_songs")

    if reported_total != total_tokens:
        errors.append(
            f"Total tokens mismatch: "
            f"reported={reported_total}, calculated={total_tokens}"
        )

    if songs:
        expected_avg = total_tokens / len(songs)
        reported_avg = data.get("avg_tokens_per_song")

        if not isinstance(reported_avg, (int, float)):
            errors.append("Invalid average tokens")
        elif abs(reported_avg - expected_avg) > 1:
            errors.append(
                f"Average tokens mismatch: "
                f"reported={reported_avg}, calculated={expected_avg}"
            )

    print("\n--- TEST RESULTS ---")

    if errors:
        for error in errors:
            print("FAIL:", error)
        print(f"\nFAILED: {len(errors)} issue(s)")
        raise SystemExit(1)

    print("PASS: All structural and numerical checks passed!")
    print("Total tokens:", total_tokens)


if __name__ == "__main__":
    validate_album()
