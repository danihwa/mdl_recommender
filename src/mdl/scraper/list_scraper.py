import requests
from bs4 import BeautifulSoup
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

BASE_URL = "https://mydramalist.com/search?adv=titles&ty=68&co=2&rt=7.5,10&st=3&so=top&page={page}"

def get_drama_urls_from_page(page: int) -> list[str]:
    """Scrape one search results page and return a list of drama URLs."""
    url = BASE_URL.format(page=page)
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    urls = []
    for a in soup.select("h6.title a"):
        href = a.get("href")
        if href:
            urls.append(f"https://mydramalist.com{href}")
    return urls

def get_all_drama_urls(max_pages: int = 135) -> list[str]:
    """Scrape all search pages and return all drama URLs."""
    all_urls = []
    for page in range(1, max_pages + 1):
        print(f"Scraping page {page}/{max_pages}...")
        urls = get_drama_urls_from_page(page)
        if not urls:
            print(f"No URLs found on page {page}, stopping.")
            break
        all_urls.extend(urls)
        time.sleep(1)  # be polite to MDL 🙏
    return all_urls

if __name__ == "__main__":
    urls = get_all_drama_urls(max_pages=135)
    print(f"\nTotal drama URLs found: {len(urls)}")