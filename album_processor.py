
"""Process albums with lyrics caching, checkpoints and debug output."""

import json
import re
import sys
from pathlib import Path

from genius_finder import (
    find_genius_url,
    valid_genius_url,
    song_variants,
)
from genius_scraper import scrape_genius_lyrics
from lyrics_processor import (
    calculate_metrics,
    clean_lyrics,
    is_lyrics_clean,
)


CACHE_DIR = Path("lyrics_cache")


def _slug(text):
    return re.sub(
        r"[^a-z0-9]+", "_", text.casefold()
    ).strip("_")


def cache_path(artist, song_name):
    return CACHE_DIR / (
        f"{_slug(artist)}__{_slug(song_name)}.json"
    )


def url_matches_song(url, artist, song_name):
    """Accept the original or cleaned song title."""
    return any(
        valid_genius_url(url, artist, variant)
        for variant in song_variants(song_name)
    )


def load_cached_song_data(artist, song_name):
    path = cache_path(artist, song_name)

    if not path.exists():
        return None

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )

        lyrics = data.get("lyrics", "")

        if (
            data.get("artist", "").casefold()
            != artist.casefold()
            or data.get("song_name") != song_name
            or not is_lyrics_clean(lyrics)
            or not url_matches_song(
                data.get("genius_url", ""),
                artist,
                song_name,
            )
        ):
            raise ValueError("Cache data invalid")

        cleaned = clean_lyrics(lyrics)

        if not is_lyrics_clean(cleaned):
            raise ValueError("Cache lyrics contaminated")

        return {
            "lyrics": cleaned,
            "genius_url": data["genius_url"],
        }

    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(
            f"CACHE INVALID: {path}: {exc}",
            file=sys.stderr,
        )
        return None


def load_cached_song(artist, song_name):
    """Keep compatibility with the previous API."""
    data = load_cached_song_data(artist, song_name)
    return data["lyrics"] if data else None


def save_cached_song(artist, song_name, lyrics, genius_url):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    path = cache_path(artist, song_name)

    data = {
        "artist": artist,
        "song_name": song_name,
        "genius_url": genius_url,
        "lyrics": lyrics,
    }

    write_json_atomic(path, data)


def write_json_atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")

    temporary.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temporary.replace(path)


def get_song_lyrics_data(artist, song_name):
    cached = load_cached_song_data(
        artist,
        song_name,
    )

    if cached is not None:
        print(
            f"CACHE HIT: {artist} - {song_name}",
            file=sys.stderr,
        )
        return cached

    url = find_genius_url(artist, song_name)

    if not url_matches_song(url, artist, song_name):
        raise ValueError(
            f"Genius URL does not match song: {url}"
        )

    print(
        f"SCRAPING: {artist} - {song_name}",
        file=sys.stderr,
    )

    lyrics = clean_lyrics(
        scrape_genius_lyrics(url)
    )

    if not is_lyrics_clean(lyrics):
        raise ValueError(
            f"Lyrics contain metadata: "
            f"{artist} - {song_name}"
        )

    save_cached_song(
        artist,
        song_name,
        lyrics,
        url,
    )

    return {
        "lyrics": lyrics,
        "genius_url": url,
    }


def get_song_lyrics(artist, song_name):
    """Keep compatibility with the previous API."""
    return get_song_lyrics_data(
        artist,
        song_name,
    )["lyrics"]


def save_lyrics_file(
    lyrics_dir,
    artist,
    album_name,
    index,
    song_name,
    lyrics,
):
    folder = (
        Path(lyrics_dir)
        / _slug(artist)
        / _slug(album_name)
    )

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        f"{index:02d}_{_slug(song_name)}.txt"
    )

    path = folder / filename

    path.write_text(
        lyrics,
        encoding="utf-8",
    )

    return str(path)


def build_result(artist, album_name, songs):
    total = sum(
        song["lyrics_length_tokens"]
        for song in songs
    )

    return {
        "artist": artist,
        "album_name": album_name,
        "songs": songs,
        "total_tokens_all_songs": total,
        "avg_tokens_per_song": (
            total / len(songs) if songs else 0
        ),
    }


def process_album(
    artist: str,
    album_name: str,
    tracks: list[str],
    checkpoint_file="album_checkpoint.json",
    lyrics_dir="lyrics_output",
    show_lyrics=True,
) -> dict:

    if not tracks:
        raise ValueError("Track list is empty.")

    checkpoint_path = Path(checkpoint_file)

    songs = []
    completed = {}

    # Load checkpoint from an earlier run.
    if checkpoint_path.exists():
        try:
            checkpoint = json.loads(
                checkpoint_path.read_text(
                    encoding="utf-8"
                )
            )

            if (
                checkpoint.get("artist") == artist
                and checkpoint.get("album_name")
                == album_name
                and checkpoint.get("track_list")
                == tracks
            ):
                completed = {
                    song["name"]: song
                    for song in checkpoint.get(
                        "songs", []
                    )
                    if song.get("status")
                    == "completed"
                }

                print(
                    f"RESUME: {len(completed)} "
                    f"completed songs found.",
                    file=sys.stderr,
                )

            else:
                print(
                    "Checkpoint belongs to a "
                    "different album. Starting fresh.",
                    file=sys.stderr,
                )

        except (OSError, ValueError, TypeError):
            print(
                "Checkpoint invalid. Starting fresh.",
                file=sys.stderr,
            )

    for index, name in enumerate(tracks, 1):
        print(
            f"\n[{index}/{len(tracks)}] {name}",
            file=sys.stderr,
        )

        try:
            if name in completed:
                song = completed[name]

                # Only skip if saved lyrics are available.
                lyrics_file = song.get("lyrics_file")

                if (
                    lyrics_file
                    and Path(lyrics_file).exists()
                ):
                    lyrics = Path(
                        lyrics_file
                    ).read_text(encoding="utf-8")

                    # Recalculate to ensure the
                    # saved metrics still match.
                    recalculated = calculate_metrics(
                        lyrics,
                        name,
                    )

                    metric_keys = (
                        "lyrics_length_chars",
                        "lyrics_length_words",
                        "lyrics_length_tokens",
                        "lyrics_hash",
                    )

                    if all(
                        recalculated.get(key)
                        == song.get(key)
                        for key in metric_keys
                    ):
                        print(
                            "CHECKPOINT HIT: SKIPPED",
                            file=sys.stderr,
                        )

                        songs.append(song)
                        continue

                    print(
                        "Checkpoint metrics mismatch. "
                        "Reprocessing song.",
                        file=sys.stderr,
                    )

            song_data = get_song_lyrics_data(
                artist,
                name,
            )

            lyrics = song_data["lyrics"]
            genius_url = song_data["genius_url"]

            metrics = calculate_metrics(
                lyrics,
                name,
            )

            lyrics_file = save_lyrics_file(
                lyrics_dir,
                artist,
                album_name,
                index,
                name,
                lyrics,
            )

            song = {
                **metrics,
                "status": "completed",
                "genius_url": genius_url,
                "lyrics_file": lyrics_file,
            }

            if show_lyrics:
                print(
                    "\n" + "=" * 65,
                    file=sys.stderr,
                )
                print(
                    f"LYRICS: {artist} - {name}",
                    file=sys.stderr,
                )
                print(
                    "=" * 65,
                    file=sys.stderr,
                )
                print(
                    lyrics,
                    file=sys.stderr,
                )
                print(
                    "=" * 65,
                    file=sys.stderr,
                )

            print(
                f"Chars: "
                f"{song['lyrics_length_chars']}",
                file=sys.stderr,
            )
            print(
                f"Words: "
                f"{song['lyrics_length_words']}",
                file=sys.stderr,
            )
            print(
                f"Tokens: "
                f"{song['lyrics_length_tokens']}",
                file=sys.stderr,
            )
            print(
                f"MD5: {song['lyrics_hash']}",
                file=sys.stderr,
            )
            print(
                f"Lyrics saved: {lyrics_file}",
                file=sys.stderr,
            )

            songs.append(song)

            write_json_atomic(
                checkpoint_path,
                {
                    **build_result(
                        artist,
                        album_name,
                        songs,
                    ),
                    "track_list": tracks,
                    "completed_tracks": len(songs),
                    "total_tracks": len(tracks),
                    "is_complete": (
                        len(songs) == len(tracks)
                    ),
                },
            )

            print(
                f"CHECKPOINT SAVED: "
                f"{len(songs)}/{len(tracks)}",
                file=sys.stderr,
            )

        except Exception as exc:
            raise RuntimeError(
                f"Album processing stopped at track "
                f"{index}/{len(tracks)} "
                f"({name}): {exc}"
            ) from exc

    return build_result(
        artist,
        album_name,
        songs,
    )
