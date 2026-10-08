"""No-API smoke tests for album orchestration."""
import tempfile
from pathlib import Path
from unittest.mock import patch
import album_processor as ap
from genius_finder import valid_genius_url

assert valid_genius_url('https://genius.com/Madonna-lucky-star-lyrics', 'Madonna', 'Lucky Star')
assert not valid_genius_url('https://evil.com/Madonna-lucky-star-lyrics', 'Madonna', 'Lucky Star')
assert not valid_genius_url('https://genius.com/Madonna-holiday-lyrics', 'Madonna', 'Lucky Star')
with tempfile.TemporaryDirectory() as folder:
    with patch.object(ap, 'CACHE_DIR', Path(folder)):
        with patch.object(ap, 'find_genius_url', return_value='https://genius.com/Madonna-lucky-star-lyrics') as find:
            with patch.object(ap, 'scrape_genius_lyrics', return_value='[Verse 1]\nHello world') as scrape:
                result = ap.process_album('Madonna', 'Madonna', ['Lucky Star'])
                assert len(result['songs']) == 1
                assert result['total_tokens_all_songs'] == result['songs'][0]['lyrics_length_tokens']
                result2 = ap.process_album('Madonna', 'Madonna', ['Lucky Star'])
                assert result == result2
                assert scrape.call_count == 1
                assert find.call_count == 1
print('PASS: offline album processing, URL validation, cache and metrics')
