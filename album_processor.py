
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from apify_client import ApifyClient

from genius_finder import find_genius_url
from genius_scraper import scrape_genius_lyrics
from lyrics_processor import calculate_metrics

load_dotenv(dotenv_path=".env")

CACHE_DIR = Path("lyrics_cache")
CACHE_DIR.mkdir(exist_ok=True)

# Previously completed Madonna scrape
EXISTING_RUNS = {
    ("Madonna", "Lucky Star"): "iEvYVcwXvNXMfMHYE"
}


def cache_path(artist, song_name):
    def safe(value):
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")

    return CACHE_DIR / f"{safe(artist)}__{safe(song_name)}.json"


def load_cached_song(artist, song_name):
    new_path = cache_path(artist, song_name)

    # Support existing Madonna cache files without re-scraping.
    legacy_name = "".join(
        c if c.isalnum() else "_" for c in song_name
    )
    legacy_path = CACHE_DIR / f"{legacy_name}.json"

    candidates = [new_path]
    if artist.casefold() == "madonna":
        candidates.append(legacy_path)

    for path in candidates:
        if not path.exists():
            continue

        data = json.loads(path.read_text(encoding="utf-8"))

        if (
            data.get("artist", "").casefold() != artist.casefold()
            or data.get("song_name") != song_name
            or not data.get("lyrics")
        ):
            raise ValueError(f"Gecersiz cache: {path}")

        return data["lyrics"]

    return None


def save_cached_song(artist, song_name, lyrics, genius_url):
    path = cache_path(artist, song_name)

    data = {
        "artist": artist,
        "song_name": song_name,
        "genius_url": genius_url,
        "lyrics": lyrics,
    }

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_existing_run_lyrics(run_id):
    client = ApifyClient(os.getenv("APIFY_API_KEY"))
    run = client.run(run_id).get()

    if not run or not run.get("defaultDatasetId"):
        raise RuntimeError("Apify run bulunamadi.")

    item = next(
        client.dataset(
            run["defaultDatasetId"]
        ).iterate_items(),
        None,
    )

    if not item or not item.get("lyrics"):
        raise RuntimeError("Kayitli lyrics bulunamadi.")

    return item["lyrics"]


def validate_genius_url(url, artist, song_name):
    parsed = urlparse(url)

    if parsed.hostname not in ("genius.com", "www.genius.com"):
        raise ValueError(f"Genius disi URL: {url}")

    # Keep strict matching for existing workflow.
    expected = (
        f"{artist}-{song_name}"
        .lower()
        .replace(" ", "-")
        .replace("'", "")
    )

    actual = parsed.path.lower().strip("/")

    if actual != f"{expected}-lyrics":
        raise ValueError(
            f"Beklenmeyen Genius URL: {url}\n"
            f"Beklenen: {expected}-lyrics"
        )


def get_song_lyrics(artist, song_name):
    cached = load_cached_song(artist, song_name)

    if cached:
        print(f"CACHE: {artist} - {song_name}", file=sys.stderr)
        return cached

    run_id = EXISTING_RUNS.get((artist, song_name))

    if run_id:
        print(f"APIFY KAYIT: {song_name}", file=sys.stderr)
        lyrics = get_existing_run_lyrics(run_id)

        save_cached_song(
            artist,
            song_name,
            lyrics,
            "https://genius.com/Madonna-lucky-star-lyrics",
        )
        return lyrics

    print(f"ARAMA: {artist} - {song_name}", file=sys.stderr)

    genius_url = find_genius_url(artist, song_name)
    validate_genius_url(genius_url, artist, song_name)

    print(f"SCRAPING: {genius_url}", file=sys.stderr)

    lyrics = scrape_genius_lyrics(genius_url)

    if not lyrics or not lyrics.strip():
        raise RuntimeError(f"Bos lyrics: {song_name}")

    save_cached_song(artist, song_name, lyrics, genius_url)

    return lyrics


def process_album(artist, album_name, tracks):
    if not tracks:
        raise ValueError("Album sarki listesi bos.")

    songs = []

    for index, song_name in enumerate(tracks, start=1):
        print(
            f"[{index}/{len(tracks)}] {song_name}",
            file=sys.stderr,
        )

        lyrics = get_song_lyrics(artist, song_name)
        metrics = calculate_metrics(lyrics, song_name)
        songs.append(metrics)

    total_tokens = sum(
        song["lyrics_length_tokens"] for song in songs
    )

    return {
        "artist": artist,
        "album_name": album_name,
        "songs": songs,
        "total_tokens_all_songs": total_tokens,
        "avg_tokens_per_song": total_tokens / len(songs),
    }


if __name__ == "__main__":
    print(
        "Bu modul main.py tarafindan kullanilir.",
        file=sys.stderr,
    )
