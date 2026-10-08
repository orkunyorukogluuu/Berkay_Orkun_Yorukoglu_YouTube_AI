

"""Find and validate Genius song URLs with fallback searches and caching."""

import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import requests
from apify_client import ApifyClient
from dotenv import load_dotenv


load_dotenv(".env")

CACHE_FILE = Path(__file__).resolve().parent / "genius_url_cache.json"

KNOWN_URLS = {
    ("madonna", "lucky star"):
        "https://genius.com/Madonna-lucky-star-lyrics",
}


def slug(value):
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    value = re.sub(r"['\u2019\u2018]", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


def clean_song_title(song_name):
    """Remove featured-artist annotations from a song title."""
    cleaned = re.sub(
        r"\s*[\(\[]\s*(?:with|feat\.?|ft\.?|featuring)\s+"
        r"[^\)\]]+[\)\]]",
        "",
        song_name,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def song_variants(song_name):
    """Return original and simplified titles without duplicates."""
    original = song_name.strip()
    cleaned = clean_song_title(original)

    variants = [original]

    if cleaned and cleaned.casefold() != original.casefold():
        variants.append(cleaned)

    return variants


def valid_genius_url(url, artist, song):
    if not isinstance(url, str):
        return False

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return False

    if parsed.hostname not in ("genius.com", "www.genius.com"):
        return False

    path = parsed.path.lower().strip("/")

    if "/" in path or not path.endswith("-lyrics"):
        return False

    actual = path[:-len("-lyrics")]
    expected = f"{slug(artist)}-{slug(song)}"

    return actual == expected


def cache_key(artist, song):
    return f"{artist.strip().casefold()}::{song.strip().casefold()}"


def load_cache():
    if not CACHE_FILE.exists():
        return {}

    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(cache):
    temporary = CACHE_FILE.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    temporary.replace(CACHE_FILE)


def url_is_accessible(url):
    """Check whether a candidate Genius page is accessible."""
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
            allow_redirects=True,
        )

        return (
            response.status_code == 200
            and urlparse(response.url).hostname
            in ("genius.com", "www.genius.com")
        )

    except requests.RequestException:
        return False


def google_search(client, query, artist, song):
    run = client.actor("apify/google-search-scraper").call(
        run_input={
            "queries": query,
            "maxPagesPerQuery": 1,
            "resultsPerPage": 10,
        }
    )

    if not run or run.get("status") != "SUCCEEDED":
        return None

    dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        return None

    for item in client.dataset(dataset_id).iterate_items():
        for result in item.get("organicResults") or []:
            url = result.get("url", "")

            if valid_genius_url(url, artist, song):
                return url

    return None


def find_genius_url(artist, song_name):
    artist = artist.strip()
    song_name = song_name.strip()

    if not artist or not song_name:
        raise ValueError("Artist ve song_name bos olamaz.")

    variants = song_variants(song_name)

    if len(variants) > 1:
        print(
            f"Alternative title: {song_name} -> {variants[1]}",
            file=sys.stderr,
        )

    original_key = cache_key(artist, song_name)
    cache = load_cache()

    # 1. Check known and cached URLs.
    for variant in variants:
        key = (artist.casefold(), variant.casefold())

        known_url = KNOWN_URLS.get(key)

        if known_url and valid_genius_url(known_url, artist, variant):
            cache[original_key] = known_url
            save_cache(cache)
            return known_url

        cached_url = cache.get(cache_key(artist, variant))

        if cached_url and valid_genius_url(
            cached_url, artist, variant
        ):
            cache[original_key] = cached_url
            save_cache(cache)
            return cached_url

    # 2. Try direct canonical URLs before using Apify.
    for variant in variants:
        direct_url = (
            f"https://genius.com/"
            f"{slug(artist)}-{slug(variant)}-lyrics"
        )

        if url_is_accessible(direct_url):
            cache[original_key] = direct_url
            cache[cache_key(artist, variant)] = direct_url
            save_cache(cache)
            return direct_url

    # 3. Fall back to Google searches.
    api_key = os.getenv("APIFY_API_KEY")

    if not api_key:
        raise ValueError("APIFY_API_KEY eksik.")

    client = ApifyClient(api_key)

    search_tasks = []

    for variant in variants:
        search_tasks.extend([
            (
                f'site:genius.com "{artist}" "{variant}" lyrics',
                variant,
            ),
            (
                f"site:genius.com/"
                f"{slug(artist)}-{slug(variant)}-lyrics",
                variant,
            ),
            (
                f"{artist} {variant} Genius lyrics",
                variant,
            ),
        ])

    for index, (query, variant) in enumerate(
        search_tasks, start=1
    ):
        print(
            f"Genius URL search {index}/{len(search_tasks)}: "
            f"{artist} - {variant}",
            file=sys.stderr,
        )

        try:
            url = google_search(
                client, query, artist, variant
            )
        except Exception as exc:
            print(
                f"Search attempt failed: {exc}",
                file=sys.stderr,
            )
            continue

        if url:
            cache[original_key] = url
            cache[cache_key(artist, variant)] = url
            save_cache(cache)
            return url

    raise ValueError(
        f"Dogrulanmis Genius URL bulunamadi: "
        f"{artist} - {song_name}"
    )


if __name__ == "__main__":
    artist = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Madonna"
    )

    song = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "Everybody"
    )

    print(find_genius_url(artist, song))
