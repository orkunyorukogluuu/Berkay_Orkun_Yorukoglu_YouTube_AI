
import hashlib
import unittest
from unittest.mock import patch

import numpy as np

from hash_generator import build_token_string, generate_hash


class FakeModel:
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, text, **kwargs):
        self.last_text = text

        # 768 boyutlu, deterministik test vektörü
        return np.array(
            [i / 1000 for i in range(768)],
            dtype=np.float32,
        )


class TestEmbeddingHash(unittest.TestCase):

    def setUp(self):
        self.album = {
            "songs": [
                {"name": "Song A", "lyrics_length_tokens": 100},
                {"name": "Song B", "lyrics_length_tokens": 200},
            ]
        }

    def test_token_string(self):
        self.assertEqual(
            build_token_string(self.album),
            "100,200",
        )

    def test_invalid_token_count(self):
        self.album["songs"][0]["lyrics_length_tokens"] = -1

        with self.assertRaises(ValueError):
            build_token_string(self.album)

    @patch("hash_generator.SentenceTransformer", FakeModel)
    def test_hash_deterministic(self):
        first = generate_hash(self.album)
        second = generate_hash(self.album)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 32)

    @patch("hash_generator.SentenceTransformer", FakeModel)
    def test_hash_matches_expected_md5(self):
        values = np.array(
            [i / 1000 for i in range(768)],
            dtype=np.float32,
        )

        embedding_string = ",".join(
            f"{float(value):.10f}"
            for value in values
        )

        expected = hashlib.md5(
            embedding_string.encode("utf-8")
        ).hexdigest()

        actual = generate_hash(self.album)

        self.assertEqual(actual, expected)

    @patch("hash_generator.SentenceTransformer", FakeModel)
    def test_hash_format(self):
        result = generate_hash(self.album)

        self.assertRegex(result, r"^[0-9a-f]{32}$")


if __name__ == "__main__":
    unittest.main(verbosity=2)
