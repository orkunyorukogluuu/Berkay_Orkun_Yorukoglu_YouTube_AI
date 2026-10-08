
"""
test_madonna_regression.py

Verify Madonna's saved lyrics against the
original token counts and MD5 hashes.

No API calls. No scraping. No file modifications.
"""

import json
import re
import sys
from pathlib import Path

from lyrics_processor import calculate_metrics


BASE_DIR = Path(__file__).resolve().parent
RESULT_FILE = BASE_DIR / "madonna_result.json"
CACHE_DIR = BASE_DIR / "lyrics_cache"

EXPECTED_TRACKS = 8
EXPECTED_TOTAL_TOKENS = 4913

EXPECTED_TOKEN_COUNTS = [
    618, 587, 633, 458,
    567, 613, 549, 888,
]


def slugify(text: str) -> str:
    return re.sub(
        r"_+", "_",
        re.sub(r"[^a-z0-9]+", "_", text.lower())
    ).strip("_")


def run_test() -> bool:
    if not RESULT_FILE.exists():
        print("FAIL: madonna_result.json not found")
        return False

    result = json.loads(
        RESULT_FILE.read_text(encoding="utf-8")
    )

    songs = result.get("songs", [])

    if len(songs) != EXPECTED_TRACKS:
        print(
            f"FAIL: Expected {EXPECTED_TRACKS} songs, "
            f"found {len(songs)}"
        )
        return False

    passed = 0
    calculated_total = 0

    for index, song in enumerate(songs):
        name = song["name"]

        cache_file = (
            CACHE_DIR / f"madonna__{slugify(name)}.json"
        )

        if not cache_file.exists():
            print(f"FAIL: {name} - cache missing")
            continue

        data = json.loads(
            cache_file.read_text(encoding="utf-8")
        )

        lyrics = (
            data.get("lyrics")
            or data.get("text")
        )

        if not isinstance(lyrics, str) or not lyrics.strip():
            print(f"FAIL: {name} - lyrics missing")
            continue

        metrics = calculate_metrics(lyrics, name)

        actual_tokens = metrics["lyrics_length_tokens"]
        expected_tokens = EXPECTED_TOKEN_COUNTS[index]

        token_match = (
            actual_tokens == expected_tokens
            and actual_tokens == song["lyrics_length_tokens"]
        )

        hash_match = (
            metrics["lyrics_hash"] == song["lyrics_hash"]
        )

        roundtrip_match = metrics[
            "token_roundtrip_valid"
        ]

        tokenizer_match = (
            metrics["tokenizer"] == "cl100k_base"
        )

        if (
            token_match
            and hash_match
            and roundtrip_match
            and tokenizer_match
        ):
            passed += 1
            calculated_total += actual_tokens

            print(
                f"PASS: {name} | "
                f"{actual_tokens} tokens | "
                "MD5 OK | Roundtrip OK"
            )
        else:
            print(
                f"FAIL: {name} | "
                f"tokens_ok={token_match} | "
                f"hash_ok={hash_match} | "
                f"roundtrip_ok={roundtrip_match} | "
                f"tokenizer_ok={tokenizer_match}"
            )

    total_match = (
        calculated_total == EXPECTED_TOTAL_TOKENS
        and result.get("total_tokens_all_songs")
        == EXPECTED_TOTAL_TOKENS
    )

    print()
    print(
        f"MADONNA REGRESSION: "
        f"{passed}/{EXPECTED_TRACKS} PASS"
    )
    print(f"Calculated total tokens: {calculated_total}")
    print(f"Total tokens match: {total_match}")

    success = (
        passed == EXPECTED_TRACKS
        and total_match
    )

    if success:
        print("MADONNA REGRESSION TEST PASSED")
    else:
        print("MADONNA REGRESSION TEST FAILED")

    return success


if __name__ == "__main__":
    try:
        sys.exit(0 if run_test() else 1)
    except Exception as error:
        print(f"TEST ERROR: {error}")
        sys.exit(1)
