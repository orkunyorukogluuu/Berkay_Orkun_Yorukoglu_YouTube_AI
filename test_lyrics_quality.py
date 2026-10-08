
import re
import unittest


SECTION_PATTERN = re.compile(
    r"\[(?:Intro|Verse(?:\s+\d+)?|Pre-Chorus|Chorus|"
    r"Post-Chorus|Bridge|Interlude|Outro|Hook|Refrain|"
    r"Instrumental|Breakdown|Skit|Spoken Word)"
    r"[^\]]*\]",
    re.IGNORECASE,
)

UNWANTED_PATTERNS = [
    r"Contributors",
    r"TranslationsPortugu",
    r"LyricsReleased in",
    r"Embed$",
    r"<script",
    r"<style",
    r"data-lyrics-container",
]


def validate_lyrics(lyrics: str):
    errors = []

    if not isinstance(lyrics, str):
        return ["Lyrics must be a string"]

    if not lyrics.strip():
        return ["Lyrics are empty"]

    if len(lyrics.strip()) < 100:
        errors.append("Lyrics suspiciously short")

    if not SECTION_PATTERN.search(lyrics):
        errors.append("No lyrics section marker found")

    for pattern in UNWANTED_PATTERNS:
        if re.search(pattern, lyrics, re.IGNORECASE):
            errors.append(f"Unwanted content: {pattern}")

    if "\ufffd" in lyrics:
        errors.append("Encoding replacement character detected")

    return errors


class TestLyricsQuality(unittest.TestCase):

    def test_valid_lyrics(self):
        sample = (
            "[Verse 1]\n"
            + "Example lyric line for testing.\n" * 10
            + "\n[Chorus]\n"
            + "Another example lyric line.\n" * 5
        )
        self.assertEqual(validate_lyrics(sample), [])

    def test_empty_lyrics(self):
        self.assertIn(
            "Lyrics are empty",
            validate_lyrics("")
        )

    def test_short_lyrics(self):
        self.assertIn(
            "Lyrics suspiciously short",
            validate_lyrics("[Chorus]\nHello")
        )

    def test_missing_section(self):
        sample = "Example text " * 30
        self.assertIn(
            "No lyrics section marker found",
            validate_lyrics(sample)
        )

    def test_metadata_contamination(self):
        sample = "[Verse 1]\n" + ("Example lyric line\n" * 20)
        sample += "\nContributors"
        errors = validate_lyrics(sample)
        self.assertTrue(
            any("Unwanted content" in error for error in errors)
        )

    def test_encoding_corruption(self):
        sample = "[Verse 1]\n" + ("Example lyric line\n" * 20)
        sample += "\ufffd"
        self.assertIn(
            "Encoding replacement character detected",
            validate_lyrics(sample)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
