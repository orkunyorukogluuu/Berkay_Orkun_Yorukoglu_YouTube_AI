
import json
import sys

from genius_finder import find_genius_url
from genius_scraper import scrape_genius_lyrics
from lyrics_processor import calculate_metrics


def process_song(artist, song_name):
    print(f"\nSarki isleniyor: {artist} - {song_name}")

    # 1. Genius URL'sini bul
    genius_url = find_genius_url(artist, song_name)
    print("Genius URL:", genius_url)

    # 2. Genius'tan sarki sozlerini cek
    raw_lyrics = scrape_genius_lyrics(genius_url)

    if not raw_lyrics.strip():
        raise RuntimeError("Sarki sozleri bos geldi.")

    # 3. Metrikleri hesapla
    result = calculate_metrics(raw_lyrics, song_name)

    return result


if __name__ == "__main__":
    try:
        result = process_song("Madonna", "Lucky Star")

        print("\n=== SONUC ===")
        print(json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ))

    except Exception as error:
        print(f"\nHATA: {error}", file=sys.stderr)
        sys.exit(1)
