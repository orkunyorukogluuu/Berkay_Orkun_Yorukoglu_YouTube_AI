
import re
import hashlib
import tiktoken

ENCODING = tiktoken.get_encoding("cl100k_base")

SECTION_PATTERN = re.compile(
    r"\[(?:Intro|Verse|Chorus|Pre-Chorus|Post-Chorus|"
    r"Bridge|Hook|Refrain|Interlude|Outro|Instrumental|"
    r"Breakdown)(?:[^\]]*)\]",
    flags=re.IGNORECASE
)



def clean_lyrics(raw_lyrics):
    if not isinstance(raw_lyrics, str):
        raise ValueError("Sarki sozleri metin olmali.")

    text = raw_lyrics.replace("\r\n", "\n").replace("\r", "\n")

    # Genius aciklamalarini atla
    match = SECTION_PATTERN.search(text)

    if match:
        text = text[match.start():]

    # Her satirin basindaki ve sonundaki bosluklari temizle
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines).strip()

    # Bolum etiketlerinden once tek bir bos satir kullan
    text = re.sub(
        r"\n*\n(?=\[(?:Intro|Verse|Chorus|Pre-Chorus|"
        r"Post-Chorus|Bridge|Hook|Refrain|Interlude|"
        r"Outro|Instrumental|Breakdown)\b)",
        "\n\n",
        text,
        flags=re.IGNORECASE
    )

    # Fazla bos satirlari kaldir
    text = re.sub(r"\n{3,}", "\n\n", text)

    if not text:
        raise ValueError("Temizlenmis sarki sozleri bos.")

    return text



def calculate_metrics(raw_lyrics, song_name):
    lyrics = clean_lyrics(raw_lyrics)

    char_count = len(lyrics)
    word_count = len(lyrics.split())
    token_count = len(ENCODING.encode(lyrics))

    tokens_per_word = (
        token_count / word_count if word_count else 0.0
    )

    lyrics_hash = hashlib.md5(
        lyrics.encode("utf-8")
    ).hexdigest()

    return {
        "name": song_name,
        "lyrics_length_chars": char_count,
        "lyrics_length_words": word_count,
        "lyrics_length_tokens": token_count,
        "tokens_per_word": tokens_per_word,
        "lyrics_hash": lyrics_hash
    }
