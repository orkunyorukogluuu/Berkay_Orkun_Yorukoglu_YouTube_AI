
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    raise ValueError("OPENROUTER_API_KEY bulunamadi!")

artist = "Madonna"

prompt = f"""
Find the first officially released studio album
by the artist {artist}.

Return every song in its ORIGINAL release order.
Exclude bonus tracks, deluxe editions and reissues.

Return ONLY a valid JSON object:
{{
    "artist": "{artist}",
    "album_name": "Album name",
    "songs": ["Song 1", "Song 2"]
}}
"""

payload = {
    "model": "openai/gpt-5.2",
    "messages": [
        {
            "role": "user",
            "content": prompt
        }
    ],
    "temperature": 0
}

try:
    print("GPT-5.2'ye istek gonderiliyor...")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=180
    )

    response.raise_for_status()
    result = response.json()

    content = result["choices"][0]["message"]["content"]
    album = json.loads(content)

    print("\n=== ALBUM BILGILERI ===")
    print("Sanatci:", album["artist"])
    print("Album:", album["album_name"])

    for i, song in enumerate(album["songs"], start=1):
        print(f"{i}. {song}")

    print("\n=== TOKEN KULLANIMI ===")

    usage = result.get("usage", {})

    print("Input tokens:", usage.get("prompt_tokens"))
    print("Output tokens:", usage.get("completion_tokens"))
    print("Total tokens:", usage.get("total_tokens"))

    cost = usage.get("cost")

    if cost is not None:
        print(f"API maliyeti: ${float(cost):.6f}")
    else:
        print("API maliyeti yanitta bildirilmedi.")

except requests.exceptions.HTTPError as e:
    print("HTTP Hatasi:", e)
    print("API cevabi:", response.text[:1000])

except (KeyError, TypeError, json.JSONDecodeError) as e:
    print("JSON isleme hatasi:", e)

except Exception as e:
    print("Hata:", str(e))
