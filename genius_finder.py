
import os
import re
from urllib.parse import urlparse

from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv(dotenv_path=".env")

client = ApifyClient(os.getenv("APIFY_API_KEY"))


def find_genius_url(artist, song_name):
    query = f'site:genius.com "{artist}" "{song_name}" lyrics'

    run = client.actor("apify/google-search-scraper").call(
        run_input={
            "queries": query,
            "maxPagesPerQuery": 1,
            "resultsPerPage": 10
        }
    )

    dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        raise RuntimeError("Google Search dataset bulunamadi.")

    for item in client.dataset(dataset_id).iterate_items():
        results = item.get("organicResults", [])

        for result in results:
            url = result.get("url", "")
            parsed = urlparse(url)

            if (
                parsed.hostname in ("genius.com", "www.genius.com")
                and parsed.path.endswith("-lyrics")
            ):
                return url

    raise ValueError(
        f"Genius URL bulunamadi: {artist} - {song_name}"
    )


if __name__ == "__main__":
    artist = "Madonna"
    song_name = "Lucky Star"

    url = find_genius_url(artist, song_name)

    print("Sanatci:", artist)
    print("Sarki:", song_name)
    print("Genius URL:", url)
