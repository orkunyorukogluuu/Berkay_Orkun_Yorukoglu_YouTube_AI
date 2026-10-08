
import hashlib
import json

from genius_scraper import scrape_genius_lyrics

URL = "https://genius.com/Madonna-everybody-lyrics"

with open("album_result.json", encoding="utf-8") as file:
    album = json.load(file)

song = next(
    song for song in album["songs"]
    if song["name"] == "Everybody"
)

lyrics = scrape_genius_lyrics(URL)

calculated_hash = hashlib.md5(
    lyrics.encode("utf-8")
).hexdigest()

stored_hash = song["lyrics_hash"]

print("\n--- HASH VERIFICATION ---")
print("Song:", song["name"])
print("Stored MD5:", stored_hash)
print("Calculated MD5:", calculated_hash)

if calculated_hash == stored_hash:
    print("PASS: MD5 hashes match!")
else:
    print("FAIL: MD5 hashes do not match!")
    raise SystemExit(1)
