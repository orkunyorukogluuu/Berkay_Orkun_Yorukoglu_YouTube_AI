
import hashlib
import json
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer


MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"


def load_album_result(file_path="album_result.json"):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Album JSON dosyasi bulunamadi: {file_path}"
        )

    raw = path.read_bytes()

    # Windows PowerShell 5.1 UTF-16 cikti olusturabilir.
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8-sig")

    data = json.loads(text)

    if not data.get("songs"):
        raise ValueError("Albumde sarki bulunamadi.")

    return data


def build_token_string(album_data):
    token_counts = []

    for song in album_data["songs"]:
        count = song["lyrics_length_tokens"]

        if type(count) is not int or count < 0:
            raise ValueError(
                f"Gecersiz token sayisi: {song['name']}"
            )

        token_counts.append(str(count))

    return ",".join(token_counts)


def generate_hash(album_data):
    token_string = build_token_string(album_data)

    print(
        f"Token dizisi: {token_string}",
        file=sys.stderr
    )

    print(
        f"Model yukleniyor: {MODEL_NAME}",
        file=sys.stderr
    )

    model = SentenceTransformer(
        MODEL_NAME,
        trust_remote_code=True
    )

    # Nomic embedding modelleri arama dokumani
    # icin search_document on ekini kullanir.
    embedding = model.encode(
    token_string,
    convert_to_numpy=True,
    normalize_embeddings=False

    )

    if len(embedding) != 768:
        raise ValueError(
            f"Beklenen 768 boyut, gelen: {len(embedding)}"
        )

    embedding_string = ",".join(
        f"{float(value):.10f}"
        for value in embedding
    )

    return hashlib.md5(
        embedding_string.encode("utf-8")
    ).hexdigest()


if __name__ == "__main__":
    try:
        album_data = load_album_result()
        result = generate_hash(album_data)

        # stdout: yalnizca hash
        print(result)

    except Exception as error:
        print(
            f"HATA: {error}",
            file=sys.stderr
        )
        sys.exit(1)
