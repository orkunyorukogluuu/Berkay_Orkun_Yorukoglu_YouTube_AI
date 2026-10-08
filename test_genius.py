
import os
import json
from dotenv import load_dotenv
from apify_client import ApifyClient

# .env dosyasindaki API anahtarlarini yukle
load_dotenv()

APIFY_API_KEY = os.getenv("APIFY_API_KEY")

if not APIFY_API_KEY:
    raise ValueError(
        "APIFY_API_KEY bulunamadi. .env dosyasini kontrol et."
    )

client = ApifyClient(APIFY_API_KEY)

# Test edecegimiz Genius sayfasi
genius_url = "https://genius.com/Madonna-lucky-star-lyrics"

# Apify Web Scraper icinde calisacak JavaScript
page_function = r"""
async function pageFunction(context) {
    const $ = context.jQuery;

    const containers = $('[data-lyrics-container="true"]');

    const details = [];
    const lyricsParts = [];

    containers.each(function(index, element) {
        const container = $(element);
        const clone = container.clone();

        // Satir sonlarini koru
        clone.find('br').replaceWith('\n');

        // Gereksiz HTML elemanlarini kaldir
        clone.find('script, style').remove();

        const text = clone.text().trim();

        details.push({
            index: index,
            tag: element.tagName,
            className: container.attr('class') || '',
            childCount: container.children().length,
            textStart: container.text().slice(0, 150),
            htmlStart: (container.html() || '').slice(0, 500)
        });

        if (text.length > 0) {
            lyricsParts.push(text);
        }
    });

    return {
        url: context.request.url,
        lyrics: lyricsParts.join('\n'),
        container_count: containers.length,
        container_details: details
    };
}
"""

print("Genius scraping testi basliyor...")
print("URL:", genius_url)
print("Apify'a gonderilen JS uzunlugu:", len(page_function))

try:
    # Apify Web Scraper'i calistir
    run = client.actor("apify/web-scraper").call(
        run_input={
            "startUrls": [
                {"url": genius_url}
            ],
            "pageFunction": page_function,
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            },
            "maxPagesPerCrawl": 1,
            "maxRequestRetries": 1,
            "pageLoadTimeoutSecs": 30,
            "waitUntil": ["domcontentloaded"],
            "downloadMedia": False,
            "downloadCss": False,
            "injectJQuery": True
        }
    )

    if not run:
        raise RuntimeError("Apify run sonucu bos geldi.")

    print("\nApify run status:", run.get("status"))

    dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        raise RuntimeError("Apify dataset ID bulunamadi.")

    items = list(
        client.dataset(dataset_id).iterate_items()
    )

    if not items:
        raise RuntimeError(
            "Apify dataset bos. Sayfa veya pageFunction kontrol edilmeli."
        )

    
    result = items[0]

    print("\n=== APIFY DATASET ALANLARI ===")
    print("Alanlar:", list(result.keys()))
    print("Lyrics tipi:", type(result.get("lyrics")).__name__)
    print("Lyrics uzunlugu:", len(result.get("lyrics") or ""))
    print("Dataset kayit sayisi:", len(items))

    for index, item in enumerate(items):
        print(
            "Kayit:", index,
            "| Alanlar:", list(item.keys()),
            "| Lyrics uzunlugu:", len(item.get("lyrics") or "")
        )

    print("\n=== GENIUS SCRAPING SONUCU ===")

    lyrics = result.get("lyrics") or ""

    print("Karakter sayisi:", len(lyrics))
    print("Container sayisi:", result.get("container_count", 0))

    print("\n=== CONTAINER DETAYLARI ===")
    print(
        json.dumps(
            result.get("container_details", []),
            ensure_ascii=False,
            indent=2
        )
    )

    print("\n=== GENIUS SCRAPING SONUCU ===")

    print(
        "Lyrics container sayisi:",
        result.get("container_count", 0)
    )

    lyrics = result.get("lyrics") or ""

    print("Karakter sayisi:", len(lyrics))

    print("\n=== CONTAINER DETAYLARI ===")

    print(
        json.dumps(
            result.get("container_details", []),
            ensure_ascii=False,
            indent=2
        )
    )

    print("\n=== ILK 200 KARAKTER ===")
    print(repr(lyrics[:200]))

    print("\n=== SON 300 KARAKTER ===")
    print(repr(lyrics[-300:]))

    if not lyrics.strip():
        print(
            "\nUYARI: Sarki sozleri bos geldi. "
            "Container detaylarini incele."
        )
    else:
        print("\nGenius scraping testi tamamlandi!")

except Exception as error:
    print("\nHATA:", str(error))
