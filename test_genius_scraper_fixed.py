"""Real Apify integration test. Uses the production Genius scraper."""
import sys
from genius_scraper import scrape_genius_lyrics


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else 'https://genius.com/Madonna-lucky-star-lyrics'
    print('TEST STARTED: production Genius scraper', flush=True)
    print('URL:', url, flush=True)
    lyrics = scrape_genius_lyrics(url)
    print('Characters:', len(lyrics))
    print('First 200 characters:', repr(lyrics[:200]))
    print('Last 200 characters:', repr(lyrics[-200:]))
    forbidden = ('Contributors', 'TranslationsPortugu', 'LyricsReleased in')
    found = [phrase for phrase in forbidden if phrase.lower() in lyrics.lower()]
    assert not found, f'Metadata contamination: {found}'
    assert len(lyrics.strip()) >= 100, 'Lyrics unexpectedly short'
    assert '\n' in lyrics, 'Missing line breaks'
    assert lyrics.lstrip().startswith('['), 'Missing opening section marker'
    print('PASS: production scraper extracted lyric sections without known metadata.')


if __name__ == '__main__':
    main()
