# YouTube AI Scraping Agent

**An AI-powered music analysis pipeline built with Python, Apify, OpenRouter GPT-5.2, and Nomic AI.**

## About This Project

This project was developed as part of the technical assessment process for **AI Multiple**.

The objective was to build an end-to-end AI-powered application that takes a YouTube music video URL, identifies the artist and their debut studio album, retrieves the album's lyrics, and performs text analysis to generate structured JSON data or an embedding-based MD5 hash.

Beyond fulfilling the technical requirements, I approached this project as an opportunity to explore how different AI models, web scraping tools, and data processing techniques can work together in a practical application.

I would also like to sincerely thank the **AI Multiple team** for giving me this opportunity. Working on this challenge has been both an enjoyable and valuable learning experience. It has allowed me to strengthen my understanding of AI integrations, automation workflows, and Python development while tackling real engineering challenges.

I genuinely appreciate the time and consideration invested in reviewing my work, and I am grateful for the opportunity to demonstrate my skills.

---

## Project Overview

The YouTube AI Scraping Agent is a Python command-line application that automates the analysis of an artist's first officially released studio album.

Given a YouTube music video URL, the application:

1. Extracts video metadata using Apify.
2. Identifies the artist and queries GPT-5.2 to determine their debut studio album.
3. Retrieves the album's original track listing in release order.
4. Finds and extracts lyrics from Genius using Apify.
5. Calculates text statistics and cryptographic hashes for each track.
6. Produces either structured JSON or an embedding-based MD5 hash.

The application is designed with a modular architecture, separating scraping, AI inference, text processing, and output generation.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.10 | Core application and CLI |
| Apify | YouTube metadata extraction and Genius scraping |
| OpenRouter | Access to OpenAI GPT-5.2 |
| GPT-5.2 | Debut album identification and track listing |
| Genius | Lyrics source |
| Tiktoken | Token counting using `cl100k_base` |
| Nomic Embed Text v1.5 | Local text embedding generation |
| Sentence Transformers | Loading and running the embedding model |
| Hashlib | MD5 hash generation |
| Python dotenv | Environment variable management |

## Architecture

The application follows this processing pipeline:

```text
YouTube Music Video URL
          |
          v
Apify YouTube Scraper
          |
          v
Artist Identification
          |
          v
OpenRouter GPT-5.2
          |
          v
Debut Studio Album + Track Listing
          |
          v
Apify + Genius
          |
          v
Lyrics Extraction and Caching
          |
          v
Lyrics Cleaning and Text Analysis
          |
          +----------------------+
          |                      |
          v                      v
      JSON Mode              Hash Mode
          |                      |
          v                      v
  Structured Metrics       Token Counts
                                 |
                                 v
                        Nomic Embedding
                         (768 dimensions)
                                 |
                                 v
                           MD5 Hash
```

## Features

**YouTube metadata extraction**

Uses the Apify `streamers/youtube-scraper` actor to retrieve information about a YouTube video and identify its channel.

**AI-powered album identification**

Uses `openai/gpt-5.2` through OpenRouter to identify the artist's first officially released studio album and determine its original track order, excluding bonus tracks and deluxe editions.

**Automated lyrics retrieval**

Locates Genius lyrics pages using Apify-powered search and retrieves lyrics through an Apify web scraper.

**Lyrics analysis**

Calculates the following metrics for each song:

- Character count
- Word count
- Token count using `cl100k_base`
- Tokens-per-word ratio
- MD5 hash of the processed lyrics

**Embedding-based hash generation**

Combines song token counts in album order, generates a 768-dimensional embedding using `nomic-ai/nomic-embed-text-v1.5`, formats the embedding values to ten decimal places, and calculates a final MD5 hash.

**Local caching**

Stores successfully retrieved lyrics locally to reduce repeated scraping requests, improve development efficiency, and avoid unnecessary API usage.

## Project Structure

```text
YouTube_AI_Agent/
|
|-- main.py
|-- album_processor.py
|-- genius_finder.py
|-- genius_scraper.py
|-- lyrics_processor.py
|-- hash_generator.py
|
|-- requirements.txt
|-- README.md
|-- .env.example
|-- .gitignore
|
|-- test_*.py
|
|-- .env                 # Local only
|-- .venv/               # Local only
|-- lyrics_cache/        # Local only
```

### Main Components

| File | Responsibility |
|---|---|
| `main.py` | Command-line interface and pipeline orchestration |
| `album_processor.py` | Track processing, caching, and album-level statistics |
| `genius_finder.py` | Finding relevant Genius lyrics URLs |
| `genius_scraper.py` | Extracting lyrics from Genius pages |
| `lyrics_processor.py` | Lyrics cleaning, tokenization, and metrics |
| `hash_generator.py` | Nomic embeddings and final hash calculation |

## Installation

### Prerequisites

- Python 3.10
- Git
- Internet connection
- Apify API key
- OpenRouter API key

### 1. Clone the repository

```bash
git clone <YOUR_PRIVATE_REPOSITORY_URL>
cd YouTube_AI_Agent
```

Replace the placeholder URL with the actual GitHub repository URL.

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The Nomic embedding model will be downloaded automatically on first use. This may take additional time depending on the internet connection.

### 4. Configure API credentials

Create a `.env` file in the project root using `.env.example` as a template:

```dotenv
APIFY_API_KEY=your_apify_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

API credentials are intentionally excluded from the repository and will be provided separately to authorized reviewers.

## Usage

The application supports two output modes: `json` and `hash`.

### JSON Mode

Run:

```bash
python main.py "https://www.youtube.com/watch?v=rSaC-YbSDpo" json
```

This mode returns a JSON object containing:

- Artist name
- Debut studio album name
- Song-level lyrics metrics
- Total token count across the album
- Average token count per song

Example response structure:

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

The example above is abbreviated for readability. The actual result includes all tracks returned for the album.

### Hash Mode

Run:

```bash
python main.py "https://www.youtube.com/watch?v=rSaC-YbSDpo" hash
```

The application:

1. Processes the album in its original track order.
2. Extracts each song's token count.
3. Joins the counts into a comma-separated string.
4. Generates a 768-dimensional Nomic embedding.
5. Formats each embedding value to ten decimal places.
6. Concatenates the formatted values using commas.
7. Computes the MD5 hash of the resulting UTF-8 string.

Example token sequence:

```text
618,587,633,458,567,613,549,888
```

Verified hash from the local Madonna test:

```text
2e5a2b9787d9516816da5c74162ad8f4
```

## Testing and Validation

The application has been tested end-to-end using a Madonna music video.

The test successfully completed the following stages:

| Test | Result |
|---|---|
| YouTube metadata extraction | Passed |
| Artist identification | Passed |
| GPT-5.2 album identification | Passed |
| Original track listing retrieval | Passed |
| Lyrics processing for eight tracks | Passed |
| Token calculations | Passed |
| JSON output generation | Passed |
| Nomic embedding generation | Passed |
| Final MD5 hash generation | Passed |
| Repeated execution using cached lyrics | Passed |

### Validated Album

**Artist:** Madonna

**Album:** Madonna (debut studio album)

**Tracks processed:** 8

**Total tokens:** 4,913

**Average tokens per song:** 614.125

Both JSON and hash modes were executed successfully through the CLI.

These results demonstrate a working end-to-end implementation for the tested example. Broader testing across additional artists, operating systems, and clean Python environments remains an area for further validation.

## Design Decisions

### Modular Architecture

The project separates individual responsibilities into dedicated Python modules to make the implementation easier to understand, test, maintain, and extend.

### GPT-5.2 for Album Identification

Rather than relying on manually maintained album data, the application uses GPT-5.2 to identify the debut album and its original track listing dynamically.

### Local Embedding Generation

The Nomic embedding model runs locally, avoiding the need for an additional paid embedding API.

### Caching Strategy

Lyrics are cached after successful retrieval, reducing repeated requests during development and testing.

### Structured CLI Output

The application separates processing diagnostics from its final result, making JSON and hash outputs suitable for command-line workflows.

## Known Limitations

- YouTube channel names do not always match the actual performing artist.
- GPT-5.2 responses may require additional validation for unusual discographies or alternate album editions.
- Genius lyrics URLs may vary from expected naming conventions.
- Lyrics availability depends on external websites and Apify actors.
- The first embedding run requires a model download.
- API requests may incur usage costs.
- Results for additional artists and fresh installations have not yet been fully validated.

## Security and API Credentials

API keys are loaded through environment variables using `python-dotenv`.

The `.env` file is excluded from version control through `.gitignore`.

For security reasons, API keys should never be committed to GitHub, even in private repositories. Credentials for evaluation can be shared separately through a secure channel.

## Future Improvements

Potential improvements include:

- More robust artist identification using additional video metadata
- Stronger validation of AI-generated album information
- Improved Genius URL matching and fallback strategies
- Automated tests with mocked API responses
- Broader cross-platform testing
- More comprehensive exception handling
- Optional local caching of YouTube and album metadata

---

## Acknowledgements

I would like to express my appreciation to the **AI Multiple team** for the opportunity to work on this technical assessment.

This project gave me the chance to connect several technologies into a complete workflow, overcome real implementation challenges, and learn through hands-on experimentation.

Thank you for considering my application and taking the time to review my work. Regardless of the outcome, I genuinely value the experience and the opportunity to grow through this challenge.

**Thank you, AI Multiple!**

---

*Developed as part of the AI Multiple technical assessment.*