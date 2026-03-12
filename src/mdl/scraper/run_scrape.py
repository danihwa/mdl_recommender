"""
run_scrape.py

Orchestrates the full scraping pipeline:
  1. Scrape all drama URLs from MDL search pages
  2. For each URL, scrape the drama detail page
  3. Append each result to dramas.json as we go (resumable)
  4. Log any failed URLs to failed_urls.txt

Usage:
    uv run src/scraper/run_scrape.py
"""

import json
import time
import os
from src.scraper.list_scraper import get_all_drama_urls
from src.scraper.drama_scraper import scrape_drama_page

# --- Config ---
OUTPUT_FILE = "data/dramas.json"
FAILED_FILE = "data/failed_urls.txt"
DELAY_SECONDS = 1.5  # polite delay between requests


def load_already_scraped(output_file: str) -> set[str]:
    """
    Read the existing JSON file and return a set of URLs already scraped.
    This is what makes the scraper resumable — if we restart, we skip
    anything that's already in the file.
    """
    if not os.path.exists(output_file):
        return set()

    already_scraped = set()
    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                drama = json.loads(line)
                if drama.get("mdl_url"):
                    already_scraped.add(drama["mdl_url"])
            except json.JSONDecodeError:
                pass  # skip malformed lines

    print(f"Found {len(already_scraped)} already scraped dramas in {output_file}")
    return already_scraped


def append_drama(output_file: str, drama: dict) -> None:
    """
    Append one drama dict as a single JSON line to the output file.

    We use newline-delimited JSON (NDJSON) format here — one JSON object
    per line. This lets us append safely without rewriting the whole file,
    which is important for a long-running scrape.
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(drama, ensure_ascii=False) + "\n")


def log_failed(failed_file: str, url: str, reason: str) -> None:
    """Append a failed URL and reason to the failed log."""
    os.makedirs(os.path.dirname(failed_file), exist_ok=True)
    with open(failed_file, "a", encoding="utf-8") as f:
        f.write(f"{url}\t{reason}\n")


def run():
    """Main function to run the scraping pipeline."""
    # Step 1: Get all drama URLs from search pages
    print("Step 1: Collecting drama URLs from search pages...")
    all_urls = get_all_drama_urls(max_pages=135)
    print(f"Found {len(all_urls)} drama URLs total\n")

    # Step 2: Check which URLs we've already scraped (resume support)
    already_scraped = load_already_scraped(OUTPUT_FILE)
    urls_to_scrape = [url for url in all_urls if url not in already_scraped]
    print(f"Skipping {len(already_scraped)} already scraped")
    print(f"Scraping {len(urls_to_scrape)} remaining dramas\n")

    # Step 3: Scrape each drama page
    success_count = 0
    fail_count = 0

    for i, url in enumerate(urls_to_scrape, start=1):
        print(f"[{i}/{len(urls_to_scrape)}] Scraping: {url}", end=" ... ")

        try:
            drama = scrape_drama_page(url)
            append_drama(OUTPUT_FILE, drama)
            success_count += 1
            print(f"{drama.get('title', '???')}")

        except Exception as e:
            fail_count += 1
            reason = str(e)
            log_failed(FAILED_FILE, url, reason)
            print(f"FAILED — {reason}")

        time.sleep(DELAY_SECONDS)

    # Step 4: Summary
    print(f"\n{'='*50}")
    print(f"Scraped successfully : {success_count}")
    print(f"Failed (logged)      : {fail_count}")
    print(f"Output file         : {OUTPUT_FILE}")
    if fail_count > 0:
        print(f"Failed URLs logged  : {FAILED_FILE}")
    print(f"{'='*50}")


if __name__ == "__main__":
    run()
