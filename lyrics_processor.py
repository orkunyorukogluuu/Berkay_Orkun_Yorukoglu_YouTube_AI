
"""
lyrics_processor.py

Clean Genius lyrics and calculate quality metrics.

Features:
- Remove Genius metadata
- Normalize lyric formatting
- Repair common encoding problems
- Calculate character and word counts
- Count real tokens using cl100k_base
- Save token IDs
- Verify token decoding
- Generate MD5 fingerprint
"""

import hashlib
import re

import tiktoken


TOKENIZER_NAME = "cl100k_base"
ENCODING = tiktoken.get_encoding(TOKENIZER_NAME)


# --------------------------------------------------
# SECTION LABELS
# --------------------------------------------------

_SECTION_RE = re.compile(
    r"\[(?:Intro|Verse|Chorus|Pre-Chorus|Post-Chorus|"
    r"Bridge|Hook|Refrain|Interlude|Outro|Instrumental|"
    r"Breakdown|Spoken|Skit|Fade)(?:[^\]]*)\]",
    flags=re.IGNORECASE,
)


# --------------------------------------------------
# GENIUS METADATA
# --------------------------------------------------

_CONTRIBUTORS_RE = re.compile(
    r"^\d+\s+Contributors?\s*",
    flags=re.IGNORECASE,
)

_TRANSLATIONS_RE = re.compile(
    r"^Translations\w+\s*",
    flags=re.IGNORECASE,
)

_TITLE_LYRICS_RE = re.compile(
    r"^.{1,120} Lyrics\s*",
    flags=re.DOTALL,
)

_READ_MORE_RE = re.compile(
    r"^.*?\u2026\s*Read More\s*",
    flags=re.DOTALL,
)


# --------------------------------------------------
# ENCODING REPAIR
# --------------------------------------------------

_MOJIBAKE_CHARS = (
    "\u00e2\u20ac",
    "\u00c2",
)


def _has_mojibake(text: str) -> bool:
    return any(
        sequence in text
        for sequence in _MOJIBAKE_CHARS
    )


def _fix_encoding(text: str) -> str:
    replacements = {
        "\u00e2\u20ac\u2122": "\u2019",
        "\u00e2\u20ac\u0153": "\u201c",
        "\u00e2\u20ac\u009d": "\u201d",
        "\u00e2\u20ac\u00a6": "\u2026",
        "\u00c2\u00a0": " ",
    }

    for broken, correct in replacements.items():
        text = text.replace(broken, correct)

    return text


# --------------------------------------------------
# REMOVE GENIUS PAGE METADATA
# --------------------------------------------------

def _strip_genius_metadata(text: str) -> str:
    text = _CONTRIBUTORS_RE.sub(
        "", text, count=1
    )

    text = _TRANSLATIONS_RE.sub(
        "", text, count=1
    )

    match = _TITLE_LYRICS_RE.match(text)

    if match:
        rest = text[match.end():].lstrip()

        if rest and (
            rest[0] == "["
            or rest[0].isupper()
        ):
            text = text[match.end():]

    match = _READ_MORE_RE.match(text)

    if match:
        text = text[match.end():]

    return text


# --------------------------------------------------
# CLEAN LYRICS
# --------------------------------------------------

def clean_lyrics(raw_lyrics: str) -> str:
    if not isinstance(raw_lyrics, str):
        raise ValueError(
            "Lyrics must be a string."
        )

    # Normalize line endings.
    text = raw_lyrics.replace(
        "\r\n", "\n"
    ).replace("\r", "\n")

    # Repair encoding artifacts.
    text = _fix_encoding(text)

    # Remove Genius metadata.
    text = _strip_genius_metadata(
        text.lstrip()
    )

    # Remove metadata before first section label,
    # but preserve actual multiline lyric content.
    section_match = _SECTION_RE.search(text)

    if (
        section_match
        and section_match.start() > 0
    ):
        prefix = text[
            :section_match.start()
        ]

        if "\n" not in prefix.strip():
            text = text[
                section_match.start():
            ]

    # Normalize whitespace on each line.
    lines = [
        line.strip()
        for line in text.split("\n")
    ]

    text = "\n".join(lines).strip()

    # Exactly one blank line before section labels.
    text = re.sub(
        r"\n*\n(?=\[(?:Intro|Verse|Chorus|Pre-Chorus|"
        r"Post-Chorus|Bridge|Hook|Refrain|Interlude|"
        r"Outro|Instrumental|Breakdown|Spoken|Skit|Fade)\b)",
        "\n\n",
        text,
        flags=re.IGNORECASE,
    )

    # Collapse excessive blank lines.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    text = text.strip()

    if not text:
        raise ValueError(
            "Cleaned lyrics are empty."
        )

    if re.match(
        r"^\d+\s+Contributor",
        text,
        re.IGNORECASE,
    ):
        raise ValueError(
            "Lyrics still contain Genius metadata."
        )

    return text


# --------------------------------------------------
# VALIDATE LYRICS
# --------------------------------------------------

def is_lyrics_clean(lyrics: str) -> bool:
    if not isinstance(lyrics, str):
        return False

    if not lyrics.strip():
        return False

    if re.match(
        r"^\d+\s+Contributor",
        lyrics,
        re.IGNORECASE,
    ):
        return False

    if re.match(
        r"^Translations",
        lyrics,
        re.IGNORECASE,
    ):
        return False

    if _has_mojibake(lyrics):
        return False

    return True


# --------------------------------------------------
# TOKENIZATION
# --------------------------------------------------

def tokenize_lyrics(lyrics: str) -> list[int]:
    """
    Return token IDs for cleaned lyrics.
    """
    cleaned = clean_lyrics(lyrics)

    return ENCODING.encode(cleaned)


def verify_token_roundtrip(
    lyrics: str,
    token_ids: list[int],
) -> bool:
    """
    Check whether decoding token IDs
    reproduces the cleaned lyrics exactly.
    """
    cleaned = clean_lyrics(lyrics)

    decoded = ENCODING.decode(token_ids)

    return decoded == cleaned


# --------------------------------------------------
# CALCULATE METRICS
# --------------------------------------------------

def calculate_metrics(
    raw_lyrics: str,
    song_name: str,
) -> dict:
    """
    Calculate lyrics metrics including
    token IDs and tokenizer validation.
    """

    lyrics = clean_lyrics(raw_lyrics)

    char_count = len(lyrics)

    word_count = len(
        lyrics.split()
    )

    token_ids = ENCODING.encode(lyrics)

    token_count = len(token_ids)

    tokens_per_word = (
        token_count / word_count
        if word_count
        else 0.0
    )

    lyrics_hash = hashlib.md5(
        lyrics.encode("utf-8")
    ).hexdigest()

    roundtrip_valid = (
        ENCODING.decode(token_ids)
        == lyrics
    )

    if not roundtrip_valid:
        raise ValueError(
            f"Token roundtrip failed: {song_name}"
        )

    return {
        "name": song_name,
        "lyrics_length_chars": char_count,
        "lyrics_length_words": word_count,
        "lyrics_length_tokens": token_count,
        "tokens_per_word": tokens_per_word,
        "lyrics_hash": lyrics_hash,
        "tokenizer": TOKENIZER_NAME,
        "token_ids": token_ids,
        "token_roundtrip_valid": roundtrip_valid,
    }
