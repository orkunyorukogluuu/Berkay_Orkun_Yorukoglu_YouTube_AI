
import os
import re
import hashlib
import tiktoken

from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv(dotenv_path=".env")

client = ApifyClient(os.getenv("APIFY_API_KEY"))

# Daha once basarili olan Apify calismasi
run = client.run("6MHeKOHiXWtHM2USm").get()

item = next(
    client.dataset(
        run["defaultDatasetId"]
    ).iterate_items()
)

raw_lyrics = item.get("lyrics") or ""

# Sarki sozlerinin baslangicini bul
match = re.search(
    r"\[(Verse|Chorus|Intro|Pre-Chorus|Bridge|Hook|Refrain|Interlude|Outro)(?:[^\]]*)\]",
    raw_lyrics,
    flags=re.IGNORECASE
)

if not match:
    raise ValueError(
        "Sarki sozlerinin baslangici bulunamadi."
    )

# Aciklama ve diger gereksiz bilgileri kaldir
clean_lyrics = raw_lyrics[match.start():].strip()

# Token sayisini hesapla
encoding = tiktoken.get_encoding("cl100k_base")
tokens = encoding.encode(clean_lyrics)

# MD5 hash hesapla
lyrics_hash = hashlib.md5(
    clean_lyrics.encode("utf-8")
).hexdigest()

words = clean_lyrics.split()

print("\n=== TEMIZLENMIS SARKI SOZLERI ===")
print("Ilk 150 karakter:", repr(clean_lyrics[:150]))
print("Son 150 karakter:", repr(clean_lyrics[-150:]))

print("\n=== METRIKLER ===")
print("Karakter sayisi:", len(clean_lyrics))
print("Kelime sayisi:", len(words))
print("Token sayisi:", len(tokens))
print("Tokens per word:", len(tokens) / len(words) if words else 0)
print("MD5:", lyrics_hash)
