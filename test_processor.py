
import os
import json

from dotenv import load_dotenv
from apify_client import ApifyClient
from lyrics_processor import calculate_metrics

load_dotenv(dotenv_path=".env")

client = ApifyClient(os.getenv("APIFY_API_KEY"))

# Daha once basarili olan scraping calismamiz
run = client.run("6MHeKOHiXWtHM2USm").get()

item = next(
    client.dataset(
        run["defaultDatasetId"]
    ).iterate_items()
)

raw_lyrics = item.get("lyrics") or ""

result = calculate_metrics(
    raw_lyrics=raw_lyrics,
    song_name="Lucky Star"
)

print(json.dumps(result, ensure_ascii=False, indent=2))
