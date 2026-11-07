# YouTube AI Scraping Agent

**Python CLI | Apify | OpenRouter GPT-5.2 | Genius | tiktoken | Nomic Embed Text v1.5**

A modular command-line application that takes a YouTube music-video URL, identifies the artist, determines the artist's debut studio album and original track order, retrieves lyrics through Apify, and returns either album-level JSON metrics or an embedding-based MD5 hash.


## What it does

1. **Identify the artist:** call Apify's `streamers/youtube-scraper` and read video channel metadata.
2. **Find the debut album:** ask `openai/gpt-5.2` through OpenRouter for the first officially released studio album and its original track listing, excluding deluxe and bonus tracks.
3. **Locate and scrape lyrics:** find relevant Genius URLs and retrieve page content using Apify actors.
4. **Process lyrics:** normalize formatting and common encoding artifacts; compute character, word and `cl100k_base` token counts, tokens per word and lyrics MD5.
5. **Return a result:** output JSON in `json` mode, or embed the ordered token counts with `nomic-ai/nomic-embed-text-v1.5` and MD5-hash the formatted embedding in `hash` mode.

The pipeline also supports **local lyrics caching, per-track checkpoints and resume behavior** to reduce unnecessary repeated requests after interruptions.

## Repository layout

```text
YouTube_AI_Agent/
├── main.py                  # CLI entry point and orchestration
├── album_processor.py       # Track processing, caching, checkpoints
├── genius_finder.py         # Genius URL discovery and title variants
├── genius_scraper.py        # Apify-based lyrics extraction
├── lyrics_processor.py      # Cleaning, tokenization and metrics
├── hash_generator.py        # Nomic embedding and MD5
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example             # Example configuration, if present
├── madonna_result.json      # Example album result
└── britney_result.json      # Example album result
```

This is intentionally a **multi-module Python project**. The executable entry point is `main.py`; the supporting `.py` modules must remain alongside it. Development tests were used locally but are **not part of the current repository submission**. Generated lyrics, checkpoints and local caches are not required to be committed.

## Requirements

- Python **3.10** (development environment)
- An **Apify API key** and an **OpenRouter API key**
- Internet access for YouTube metadata, model inference and Genius scraping
- Sufficient disk space and time for the Nomic model download on first hash run

## Setup

```bash
git clone https://github.com/orkunyorukogluuu/YouTube_AI_Agent.git
cd YouTube_AI_Agent
python -m venv .venv
```

Install dependencies without activating the environment if Windows PowerShell blocks `Activate.ps1`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

On macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root:

```dotenv
APIFY_API_KEY=your_apify_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

**Never commit `.env` or API credentials**, including to a private repository.

## Usage

### JSON mode

```powershell
.\.venv\Scripts\python.exe main.py "https://www.youtube.com/watch?v=ThHz9wlBeLU" json
```

### Hash mode

```powershell
.\.venv\Scripts\python.exe main.py "https://www.youtube.com/watch?v=ThHz9wlBeLU" hash
```

On systems with the environment activated, replace `.\.venv\Scripts\python.exe` with `python`.

### Optional flags

```text
--checkpoint PATH    Checkpoint file (default: album_checkpoint.json)
--lyrics-dir PATH    Output directory for retrieved lyrics (default: lyrics_output)
```

For example:

```powershell
.\.venv\Scripts\python.exe main.py "https://www.youtube.com/watch?v=ThHz9wlBeLU" json --checkpoint madonna_checkpoint.json
```

Processing messages and errors are directed to **stderr**, while the final JSON/hash is printed to **stdout**.

## Output

A representative JSON result contains the following metrics:

```json
{
  "artist": "Madonna",
  "album_name": "Madonna",
  "songs": [
    {
      "name": "Lucky Star",
      "lyrics_length_chars": 2306,
      "lyrics_length_words": 410,
      "lyrics_length_tokens": 618,
      "tokens_per_word": 1.5073170731707317,
      "lyrics_hash": "3a78a48b7258905f36512afe522b5d9a"
    }
  ],
  "total_tokens_all_songs": 4913,
  "avg_tokens_per_song": 614.125
}
```

*Illustrative, abbreviated example: the album-wide totals refer to all eight Madonna tracks, not only the one shown above.*

**Implementation note:** The current `lyrics_processor.py` also produces internal diagnostic fields (`tokenizer`, `token_ids`, `token_roundtrip_valid`), so the actual JSON may contain additional song fields beyond the assessment's minimal schema. The `lyrics_hash` is currently calculated from **cleaned lyrics**, rather than the raw text; this differs from a strict raw-lyrics MD5 requirement. These are known specification differences, not claimed as resolved.

### Hash algorithm

For the eight-track Madonna example, the ordered token counts were:

```text
618,587,633,458,567,613,549,888
```

The application encodes that comma-separated string with `nomic-ai/nomic-embed-text-v1.5` (768 dimensions), formats each embedding value to ten decimal places, joins them with commas, and calculates the UTF-8 MD5.

A hash recorded in local validation was:

```text
2e5a2b9787d9516816da5c74162ad8f4
```

Embedding outputs can be sensitive to model and dependency versions, so the above value is a recorded run, not a cross-environment guarantee.

## Validation performed during development

- **Madonna:** debut album *Madonna* (1983), 8 tracks, **4,913 tokens** and **614.125 average tokens per track** in the saved result. Both JSON and hash workflows were exercised during development.
- **Britney Spears:** debut album *...Baby One More Time*, 11 tracks and **6,249 tokens** in the recorded development run; example result is included.
- Mocked pipeline and regression tests were run during development; those development test scripts were deliberately excluded from the final GitHub repository.

These observations are **not a claim that every artist, clean installation or external API condition has been verified**.

## Reliability and limitations

- **Artist identity:** YouTube's channel name can differ from the performing artist.
- **Album accuracy:** GPT-5.2's discography and track-order output may need verification for ambiguous releases.
- **Genius availability:** External scraping can encounter HTTP 403 responses, missing lyrics or page changes.
- **Title variants:** Featuring credits and alternative track naming can complicate Genius URL matching; the finder tries normalized variants.
- **Resuming:** Checkpoints and cached lyrics help avoid repeating successfully processed tracks, but do not guarantee recovery from every corrupted state.
- **Text fidelity:** Cleaning and Unicode repair can change the source text, which affects hashes and token counts.
- **Output contract:** The present modular CLI and its extra diagnostic fields differ from a strict single-file/minimal-JSON assessment interpretation.
- **Cost:** Apify and OpenRouter requests may incur charges.

## Security

Only the `APIFY_API_KEY` and `OPENROUTER_API_KEY` environment variables are required for the integrations described above. `.env`, virtual environments, caches and generated working data should remain outside version control. Share reviewer access to the private repository and distribute credentials only through an approved secure channel.

