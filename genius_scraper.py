
"""Scrape Genius lyrics with Apify Web Scraper."""

import os
import re
import time

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv(".env")


PAGE_FUNCTION = r"""
async function pageFunction(context) {
    const $ = context.jQuery;

    const containers = $('[data-lyrics-container="true"]');
    const parts = [];

    function textOf(node) {
        if (node.nodeType === 3) {
            return node.nodeValue || '';
        }

        if (node.nodeType !== 1) {
            return '';
        }

        const tag = node.tagName.toUpperCase();

        if (tag === 'BR') {
            return '\n';
        }

        if ([
            'SCRIPT',
            'STYLE',
            'NOSCRIPT',
            'SVG',
            'BUTTON'
        ].includes(tag)) {
            return '';
        }

        if (node.hasAttribute('data-exclude-from-selection')) {
            return '';
        }

        const cls = typeof node.className === 'string'
            ? node.className
            : '';

        if (/LyricsHeader__|SongDescription__|ContributorsCreditSong__|Translations__|LyricsFooter__|SongBio__/.test(cls)) {
            return '';
        }

        if (node.getAttribute('aria-hidden') === 'true') {
            return '';
        }

        if (node.hidden || (
            node.style &&
            node.style.display === 'none'
        )) {
            return '';
        }

        let out = '';

        for (const child of node.childNodes) {
            out += textOf(child);
        }

        return out;
    }

    containers.each(function(_, el) {
        if ($(el).find('[data-lyrics-container="true"]').length) {
            return;
        }

        let text = textOf(el).trim();

        const marker = /\[(?:Intro|Verse(?:\s+\d+)?|Pre-Chorus|Chorus|Post-Chorus|Bridge|Interlude|Outro|Hook|Refrain|Instrumental|Breakdown|Skit|Spoken Word)(?:[^\]]*)\]/i;

        const match = marker.exec(text);

        if (match && match.index > 0) {
            text = text.slice(match.index);
        }

        if (text && marker.test(text)) {
            parts.push(text);
        }
    });

    return {
        url: context.request.url,
        lyrics: parts.join('\n\n'),
        container_count: containers.length
    };
}
"""


def _fix_encoding(text: str) -> str:
    replacements = {
        "\u00e2\u20ac\u2122": "\u2019",
        "\u00e2\u20ac\u0153": "\u201c",
        "\u00e2\u20ac\x9d": "\u201d",
        "\u00e2\u20ac\u00a6": "\u2026",
        "\u00c2\u00a0": " ",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    return text


def _scrape_once(client: ApifyClient, genius_url: str) -> str:
    run = client.actor("apify/web-scraper").call(
        run_input={
            "startUrls": [{"url": genius_url}],
            "pageFunction": PAGE_FUNCTION,
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
            "maxPagesPerCrawl": 1,
            "maxRequestRetries": 3,
            "pageLoadTimeoutSecs": 90,
            "waitUntil": ["domcontentloaded"],
            "downloadMedia": False,
            "downloadCss": False,
            "injectJQuery": True,
        }
    )

    if not run:
        raise RuntimeError("Apify run sonucu bos.")

    if run.get("status") != "SUCCEEDED":
        raise RuntimeError(
            f"Apify run basarisiz: {run.get('status')}"
        )

    dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        raise RuntimeError("Apify dataset ID bulunamadi.")

    items = list(
        client.dataset(dataset_id).iterate_items()
    )

    if not items:
        raise RuntimeError(
            f"Apify dataset bos: {genius_url}"
        )

    record = next(
        (
            item for item in items
            if item.get("lyrics")
        ),
        None
    )

    if record is None:
        raise RuntimeError(
            f"Apify dataset icinde lyrics bulunamadi: {genius_url}"
        )

    lyrics = _fix_encoding(
        record.get("lyrics") or ""
    ).strip()

    if not lyrics:
        raise RuntimeError("Lyrics metni bos.")

    if not re.search(
        r"\[(?:Intro|Verse|Pre-Chorus|Chorus|Bridge|Outro|Hook|Refrain)",
        lyrics,
        re.IGNORECASE,
    ):
        raise RuntimeError(
            "Gecerli lyrics bolumleri bulunamadi."
        )

    if re.search(
        r"Contributors|TranslationsPortugu|LyricsReleased in",
        lyrics,
        re.IGNORECASE,
    ):
        raise RuntimeError(
            "Lyrics metninde Genius metadata bulundu."
        )

    return lyrics


def scrape_genius_lyrics(genius_url: str) -> str:
    api_key = os.getenv("APIFY_API_KEY")

    if not api_key:
        raise ValueError("APIFY_API_KEY eksik.")

    client = ApifyClient(api_key)

    max_attempts = 3
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            print(
                f"Genius scraping attempt {attempt}/{max_attempts}: "
                f"{genius_url}",
                flush=True,
            )

            lyrics = _scrape_once(client, genius_url)

            print(
                f"Genius scraping successful: {len(lyrics)} characters",
                flush=True,
            )

            return lyrics

        except Exception as exc:
            last_error = exc

            print(
                f"Genius scraping failed "
                f"({attempt}/{max_attempts}): {exc}",
                flush=True,
            )

            if attempt < max_attempts:
                time.sleep(5 * attempt)

    raise RuntimeError(
        f"Genius scraping failed after {max_attempts} attempts "
        f"for {genius_url}: {last_error}"
    ) from last_error


if __name__ == "__main__":
    import sys

    url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://genius.com/Madonna-lucky-star-lyrics"
    )

    result = scrape_genius_lyrics(url)

    print("Characters:", len(result))
    print("First 200 chars:", repr(result[:200]))
    print("Last 200 chars:", repr(result[-200:]))
