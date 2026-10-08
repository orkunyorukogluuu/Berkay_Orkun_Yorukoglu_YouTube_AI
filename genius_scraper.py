
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv(dotenv_path=".env")

client = ApifyClient(os.getenv("APIFY_API_KEY"))

PAGE_FUNCTION = r"""
async function pageFunction(context) {
    const $ = context.jQuery;

    // Genius'un sarki sozu container'lari
    const containers = $(
        'div[class*="Lyrics__Container"][data-lyrics-container="true"]'
    );

    const lyricsParts = [];

    containers.each(function(index, element) {
        const clone = $(element).clone();

        clone.find('br').replaceWith('\n');
        clone.find('script, style').remove();

        const text = clone.text().trim();

        if (text) {
            lyricsParts.push(text);
        }
    });

    return {
        url: context.request.url,
        lyrics: lyricsParts.join('\n'),
        container_count: containers.length
    };
}
"""


def scrape_genius_lyrics(genius_url):
    run = client.actor("apify/web-scraper").call(
        run_input={
            "startUrls": [{"url": genius_url}],
            "pageFunction": PAGE_FUNCTION,
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

    if not run or not run.get("defaultDatasetId"):
        raise RuntimeError("Apify dataset bulunamadi.")

    items = list(
        client.dataset(
            run["defaultDatasetId"]
        ).iterate_items()
    )

    if not items:
        raise RuntimeError("Genius scraping sonucu bos.")

    lyrics = items[0].get("lyrics") or ""

    if not lyrics.strip():
        raise RuntimeError(
            "Genius sayfasindan sarki sozleri alinamadi."
        )

    return lyrics


if __name__ == "__main__":
    url = "https://genius.com/Madonna-lucky-star-lyrics"

    lyrics = scrape_genius_lyrics(url)

    print("Karakter sayisi:", len(lyrics))
    print("Ilk 100 karakter:", repr(lyrics[:100]))
