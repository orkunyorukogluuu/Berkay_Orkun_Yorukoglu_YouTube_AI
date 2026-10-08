

import argparse
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

import requests
from dotenv import load_dotenv
from apify_client import ApifyClient

from album_processor import process_album
from hash_generator import generate_hash

load_dotenv(dotenv_path=".env")


def get_artist_from_youtube(url):
    api_key = os.getenv("APIFY_API_KEY")
    if not api_key:
        raise ValueError("APIFY_API_KEY eksik.")

    client = ApifyClient(api_key)

    print("YouTube bilgileri aliniyor...", file=sys.stderr)

    run = client.actor("streamers/youtube-scraper").call(
        run_input={
            "startUrls": [{"url": url}],
            "maxResults": 1,
        }
    )

    if not run or run.get("status") != "SUCCEEDED":
        raise RuntimeError("YouTube scraper basarisiz.")

    items = list(
        client.dataset(run["defaultDatasetId"]).iterate_items()
    )

    if not items:
        raise ValueError("YouTube videosu bulunamadi.")

    artist = items[0].get("channelName")

    if not artist:
        raise ValueError("Kanal adi bulunamadi.")

    print(f"Bulunan sanatci: {artist}", file=sys.stderr)
    return artist


def get_first_album(artist):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY eksik.")

    print("GPT-5.2 albumu ariyor...", file=sys.stderr)

    prompt = f"""
Find the first officially released studio album
of this music artist: {artist}.

Return all songs in the original release order.
Exclude bonus tracks, reissues, and deluxe editions.

Return ONLY valid JSON:
{{
  "artist": "Artist name",
  "album_name": "Album name",
  "songs": ["Song 1", "Song 2"]
}}
"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openai/gpt-5.2",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
        },
        timeout=180,
    )

    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    album = json.loads(content)

    if not isinstance(album.get("songs"), list) or not album["songs"]:
        raise ValueError("Album sarki listesi bos.")

    return album


def main():
    parser = argparse.ArgumentParser(
        description="YouTube AI Scraping Agent"
    )

    parser.add_argument("youtube_url")
    parser.add_argument(
        "mode",
        choices=["json", "hash"],
        help="Output format",
    )

    parser.add_argument(
        "--checkpoint",
        default="album_checkpoint.json",
        help="Checkpoint JSON file",
    )

    parser.add_argument(
        "--lyrics-dir",
        default="lyrics_output",
        help="Directory for lyrics files",
    )

    args = parser.parse_args()

    try:
        with redirect_stdout(sys.stderr):
            artist = get_artist_from_youtube(args.youtube_url)
            album = get_first_album(artist)

            result = process_album(
                artist=album.get("artist") or artist,
                album_name=album["album_name"],
                tracks=album["songs"],
                checkpoint_file=args.checkpoint,
                lyrics_dir=args.lyrics_dir,
                show_lyrics=True,
            )

            if args.mode == "hash":
                output = generate_hash(result)
            else:
                output = json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                )

        print(output)

    except Exception as error:
        print(f"HATA: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
