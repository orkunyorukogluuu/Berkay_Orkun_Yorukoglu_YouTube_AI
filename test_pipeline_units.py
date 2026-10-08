"""
test_pipeline_units.py
-----------------------
Unit tests for the YouTube AI Scraping Agent's Genius lyrics pipeline.

Tests cover:
  - lyrics_processor.clean_lyrics: metadata stripping, encoding, section-less songs
  - lyrics_processor.is_lyrics_clean: cache validation logic
  - album_processor.validate_genius_url: punctuation, legitimate vs. bad URLs
  - album_processor._normalize_genius_slug: slug generation edge cases
  - album_processor.load_cached_song: contaminated / stale cache handling

Run with:
    python -m pytest test_pipeline_units.py -v
or:
    python test_pipeline_units.py
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------
from lyrics_processor import clean_lyrics, is_lyrics_clean
from album_processor import (
    validate_genius_url,
    _normalize_genius_slug,
    cache_path,
    load_cached_song,
    save_cached_song,
    CACHE_DIR,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _make_cache(artist, song_name, lyrics, tmp_dir, genius_url="https://genius.com/test-lyrics"):
    """Write a cache entry into *tmp_dir* and return the path."""
    slug_artist = artist.lower().replace(" ", "_")
    slug_song = song_name.lower().replace(" ", "_")
    path = Path(tmp_dir) / f"{slug_artist}__{slug_song}.json"
    data = {
        "artist": artist,
        "song_name": song_name,
        "genius_url": genius_url,
        "lyrics": lyrics,
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


# ===========================================================================
# clean_lyrics — metadata stripping
# ===========================================================================

class TestCleanLyricsMetadataStripping(unittest.TestCase):

    def test_strips_contributor_count_prefix(self):
        raw = (
            "44 ContributorsTranslationsPolski"
            "Got to Be There Lyrics"
            "\u201cGot to Be There\u201d is the debut single\u2026 Read More "
            "[Verse 1]\nGot to be there\nIn the morning"
        )
        result = clean_lyrics(raw)
        self.assertTrue(result.startswith("[Verse 1]"), repr(result[:60]))
        self.assertNotIn("Contributors", result)
        self.assertNotIn("Translations", result)
        self.assertNotIn("Read More", result)

    def test_strips_single_contributor(self):
        raw = "1 ContributorTranslationsEnglishSong Lyrics[Chorus]\nHello world"
        result = clean_lyrics(raw)
        self.assertNotIn("Contributor", result)
        self.assertTrue(result.startswith("[Chorus]"), repr(result[:40]))

    def test_strips_read_more_block(self):
        raw = (
            '36 ContributorsTranslationsPolskiAin\'t No Sunshine Lyrics'
            '\u201cAin\'t No Sunshine\u201d is the first song\u2026 Read More '
            '[Intro]\nYou ever want something'
        )
        result = clean_lyrics(raw)
        self.assertTrue(result.startswith("[Intro]"), repr(result[:40]))

    def test_strips_translations_no_section_label(self):
        """Song with no section labels — metadata is still stripped."""
        raw = (
            "5 ContributorsTranslationsFrançaisHello World Lyrics"
            "Hello\nWorld\nThis is fine"
        )
        result = clean_lyrics(raw)
        self.assertNotIn("Contributors", result)
        self.assertIn("Hello", result)

    def test_preserves_section_labels(self):
        raw = "[Verse 1]\nLine one\nLine two\n\n[Chorus]\nRefrain line"
        result = clean_lyrics(raw)
        self.assertIn("[Verse 1]", result)
        self.assertIn("[Chorus]", result)

    def test_preserves_all_section_label_types(self):
        sections = ["Intro", "Verse 1", "Pre-Chorus", "Chorus",
                    "Post-Chorus", "Bridge", "Hook", "Interlude",
                    "Outro", "Breakdown", "Spoken"]
        for section in sections:
            raw = f"[{section}]\nSome lyrics here"
            result = clean_lyrics(raw)
            self.assertIn(f"[{section}]", result, f"Missing section: {section}")

    def test_preserves_repeated_lines(self):
        raw = (
            "[Chorus]\n"
            "Ain't no sunshine when she's gone\n"
            "Ain't no sunshine when she's gone\n"
            "Ain't no sunshine when she's gone"
        )
        result = clean_lyrics(raw)
        self.assertEqual(result.count("Ain't no sunshine when she's gone"), 3)

    def test_normalises_section_spacing(self):
        """There should be exactly one blank line before each section label."""
        raw = (
            "[Verse 1]\nLine one\n\n\n\n\n[Chorus]\nRefrain"
        )
        result = clean_lyrics(raw)
        # No more than two consecutive newlines anywhere
        self.assertNotIn("\n\n\n", result)

    def test_strips_whitespace_per_line(self):
        raw = "  [Verse 1]  \n  Line one  \n  Line two  "
        result = clean_lyrics(raw)
        self.assertEqual(result, "[Verse 1]\nLine one\nLine two")


# ===========================================================================
# clean_lyrics — Unicode / encoding
# ===========================================================================

class TestCleanLyricsUnicode(unittest.TestCase):

    def test_fixes_mojibake_left_quote(self):
        # â€œ is the Mojibake for U+201C "
        raw = "[Verse 1]\n\u00e2\u20ac\u0153Hello world\nSome lyric"
        result = clean_lyrics(raw)
        self.assertNotIn("â€", result)
        self.assertIn("\u201c", result)  # " repaired

    def test_fixes_mojibake_apostrophe(self):
        # â€™ is the Mojibake for U+2019 '
        raw = "[Verse 1]\nAinâ€™t no sunshine"
        result = clean_lyrics(raw)
        self.assertNotIn("â€™", result)
        self.assertIn("\u2019", result)  # ' repaired

    def test_legitimate_unicode_preserved(self):
        """Non-ASCII characters in actual lyrics must not be corrupted."""
        raw = "[Verse 1]\nNaïve cœur résumé"
        result = clean_lyrics(raw)
        self.assertIn("Naïve", result)
        self.assertIn("cœur", result)
        self.assertIn("résumé", result)

    def test_curly_quotes_preserved(self):
        raw = "[Intro]\n\u201cHello,\u201d she said"
        result = clean_lyrics(raw)
        self.assertIn("\u201c", result)
        self.assertIn("\u201d", result)


# ===========================================================================
# clean_lyrics — songs without section labels
# ===========================================================================

class TestCleanLyricsNoSectionLabels(unittest.TestCase):

    def test_song_without_section_labels_not_truncated(self):
        raw = "I know, I know, I know\nSomething happened long ago\nAnd now it's gone"
        result = clean_lyrics(raw)
        self.assertIn("I know, I know, I know", result)
        self.assertIn("Something happened long ago", result)
        self.assertIn("And now it's gone", result)

    def test_song_without_section_labels_metadata_stripped(self):
        raw = (
            "7 ContributorsTranslationsPolski"
            "Some Song Lyrics"
            "Some song description\u2026 Read More "
            "I know, I know, I know\n"
            "Something happened long ago"
        )
        result = clean_lyrics(raw)
        self.assertNotIn("Contributors", result)
        self.assertIn("I know", result)

    def test_raises_on_empty_input(self):
        with self.assertRaises(ValueError):
            clean_lyrics("")

    def test_raises_on_whitespace_only(self):
        with self.assertRaises(ValueError):
            clean_lyrics("   \n\n  ")


# ===========================================================================
# is_lyrics_clean — cache validation
# ===========================================================================

class TestIsLyricsClean(unittest.TestCase):

    def test_clean_lyrics_returns_true(self):
        lyrics = "[Verse 1]\nGot to be there\nIn the morning"
        self.assertTrue(is_lyrics_clean(lyrics))

    def test_contributor_prefix_returns_false(self):
        lyrics = "44 ContributorsTranslationsPolskiGot to Be There Lyrics[Verse 1]\n..."
        self.assertFalse(is_lyrics_clean(lyrics))

    def test_translations_prefix_returns_false(self):
        lyrics = "TranslationsPolskiSome song lyrics\n[Verse 1]\n..."
        self.assertFalse(is_lyrics_clean(lyrics))

    def test_mojibake_returns_false(self):
        lyrics = "[Verse 1]\nâ€œHello worldâ€"
        self.assertFalse(is_lyrics_clean(lyrics))

    def test_empty_returns_false(self):
        self.assertFalse(is_lyrics_clean(""))
        self.assertFalse(is_lyrics_clean(None))

    def test_single_contributor_returns_false(self):
        self.assertFalse(is_lyrics_clean("1 ContributorSome stuff"))


# ===========================================================================
# _normalize_genius_slug — slug generation
# ===========================================================================

class TestNormalizeGeniusSlug(unittest.TestCase):

    def test_simple_artist(self):
        self.assertEqual(_normalize_genius_slug("Michael Jackson"), "michael-jackson")

    def test_apostrophe_dropped(self):
        # "Ain't" → "aint" (Genius drops apostrophes in slugs)
        self.assertEqual(_normalize_genius_slug("Ain't No Sunshine"), "aint-no-sunshine")

    def test_parentheses_become_hyphens(self):
        result = _normalize_genius_slug("Maria (You Were the Only One)")
        self.assertEqual(result, "maria-you-were-the-only-one")

    def test_trailing_punctuation(self):
        result = _normalize_genius_slug("Rockin' Robin")
        self.assertEqual(result, "rockin-robin")

    def test_ampersand(self):
        result = _normalize_genius_slug("Simon & Garfunkel")
        self.assertEqual(result, "simon-garfunkel")

    def test_no_double_hyphens(self):
        result = _normalize_genius_slug("Hello -- World")
        self.assertNotIn("--", result)

    def test_curly_apostrophe(self):
        result = _normalize_genius_slug("Girl Don\u2019t Take Your Love from Me")
        self.assertEqual(result, "girl-dont-take-your-love-from-me")


# ===========================================================================
# validate_genius_url — URL validation
# ===========================================================================

class TestValidateGeniusUrl(unittest.TestCase):

    def test_accepts_simple_url(self):
        validate_genius_url(
            "https://genius.com/Michael-jackson-got-to-be-there-lyrics",
            "Michael Jackson",
            "Got to Be There",
        )

    def test_accepts_url_with_parentheses_in_title(self):
        """
        Regression test: Maria (You Were the Only One) must be accepted.
        The old exact-match validator rejected this because parentheses
        were stripped from the expected slug but not matched in the path.
        """
        validate_genius_url(
            "https://genius.com/Michael-jackson-maria-you-were-the-only-one-lyrics",
            "Michael Jackson",
            "Maria (You Were the Only One)",
        )

    def test_accepts_url_with_apostrophe_in_title(self):
        validate_genius_url(
            "https://genius.com/Michael-jackson-aint-no-sunshine-lyrics",
            "Michael Jackson",
            "Ain't No Sunshine",
        )

    def test_accepts_url_with_apostrophe_in_title_curly(self):
        validate_genius_url(
            "https://genius.com/Michael-jackson-rockin-robin-lyrics",
            "Michael Jackson",
            "Rockin\u2019 Robin",
        )

    def test_accepts_www_subdomain(self):
        validate_genius_url(
            "https://www.genius.com/Michael-jackson-got-to-be-there-lyrics",
            "Michael Jackson",
            "Got to Be There",
        )

    def test_rejects_non_genius_domain(self):
        with self.assertRaises(ValueError, msg="Should reject non-Genius domains"):
            validate_genius_url(
                "https://example.com/Michael-jackson-got-to-be-there-lyrics",
                "Michael Jackson",
                "Got to Be There",
            )

    def test_rejects_wrong_artist(self):
        with self.assertRaises(ValueError, msg="Should reject wrong artist slug"):
            validate_genius_url(
                "https://genius.com/Madonna-got-to-be-there-lyrics",
                "Michael Jackson",
                "Got to Be There",
            )

    def test_rejects_missing_lyrics_suffix(self):
        with self.assertRaises(ValueError, msg="Should reject URLs without -lyrics suffix"):
            validate_genius_url(
                "https://genius.com/Michael-jackson-got-to-be-there",
                "Michael Jackson",
                "Got to Be There",
            )

    def test_rejects_wrong_song(self):
        with self.assertRaises(ValueError):
            validate_genius_url(
                "https://genius.com/Michael-jackson-thriller-lyrics",
                "Michael Jackson",
                "Got to Be There",
            )


# ===========================================================================
# load_cached_song — cache validation (uses temp directories)
# ===========================================================================

class TestLoadCachedSong(unittest.TestCase):

    def setUp(self):
        self._orig_cache = CACHE_DIR
        # Redirect CACHE_DIR to a temp directory for test isolation
        import album_processor
        self._tmp = tempfile.TemporaryDirectory()
        self._tmp_path = Path(self._tmp.name)
        album_processor.CACHE_DIR = self._tmp_path

    def tearDown(self):
        import album_processor
        album_processor.CACHE_DIR = self._orig_cache
        self._tmp.cleanup()

    def _write(self, artist, song_name, lyrics):
        import album_processor
        path = album_processor.cache_path(artist, song_name)
        path.write_text(
            json.dumps({
                "artist": artist,
                "song_name": song_name,
                "genius_url": "https://genius.com/test-lyrics",
                "lyrics": lyrics,
            }),
            encoding="utf-8",
        )
        return path

    def test_returns_clean_cached_lyrics(self):
        self._write("Test Artist", "Test Song", "[Verse 1]\nClean lyrics here")
        result = load_cached_song("Test Artist", "Test Song")
        self.assertEqual(result, "[Verse 1]\nClean lyrics here")

    def test_deletes_and_returns_none_for_contaminated_cache(self):
        path = self._write(
            "Test Artist", "Test Song",
            "44 ContributorsTranslationsPolskiTest Song Lyrics[Verse 1]\nLyrics"
        )
        result = load_cached_song("Test Artist", "Test Song")
        self.assertIsNone(result, "Contaminated cache should return None")
        self.assertFalse(path.exists(), "Contaminated cache file should be deleted")

    def test_returns_none_when_no_cache(self):
        result = load_cached_song("Unknown Artist", "Unknown Song")
        self.assertIsNone(result)

    def test_deletes_and_returns_none_for_artist_mismatch(self):
        path = self._write("Wrong Artist", "Test Song", "[Verse 1]\nLyrics")
        result = load_cached_song("Test Artist", "Test Song")
        self.assertIsNone(result)

    def test_deletes_corrupt_json(self):
        import album_processor
        path = album_processor.CACHE_DIR / "test_artist__test_song.json"
        path.write_text("{ not valid json", encoding="utf-8")
        result = load_cached_song("Test Artist", "Test Song")
        self.assertIsNone(result)
        self.assertFalse(path.exists(), "Corrupt JSON cache file should be deleted")


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
