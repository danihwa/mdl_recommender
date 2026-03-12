import requests
from bs4 import BeautifulSoup
import time
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_page(url: str) -> BeautifulSoup:
    """Fetch a page and return a BeautifulSoup object."""
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def scrape_drama_page(url: str) -> dict:
    """Scrape a single drama page and return a dictionary of fields."""
    soup = get_page(url)

    mdl_id = int(url.split("/")[-1].split("-")[0])

    # --- Core info ---
    title = soup.find("h1", class_="film-title")
    title = title.get_text(strip=True) if title else None

    native_title = soup.find("b", string="Native Title:")
    if native_title:
        a_tag = native_title.find_next_sibling("a")
        native_title = a_tag.get_text(strip=True) if a_tag else None
    else:
        native_title = None

    also_known_as = soup.find("b", string="Also Known As:")
    if also_known_as:
        span = also_known_as.find_next_sibling("span", class_="mdl-aka-titles")
        also_known_as = span.get_text(strip=True) if span else None
    else:
        also_known_as = None

    # --- Synopsis ---
    synopsis_div = soup.find("div", class_="show-synopsis")
    synopsis = None
    if synopsis_div:
        # Get only the span with the actual text, not the translation links
        synopsis_span = synopsis_div.find("span", itemprop="description")
        synopsis = (
            synopsis_span.get_text(strip=True)
            if synopsis_span
            else synopsis_div.get_text(strip=True)
        )

    # --- Details sidebar ---
    country = soup.find("b", string="Country:")
    country = country.find_next_sibling(string=True).strip() if country else None

    episodes = soup.find("b", string="Episodes:")
    episodes = episodes.find_next_sibling(string=True).strip() if episodes else None
    episodes = int(episodes) if episodes and episodes.isdigit() else None

    duration = soup.find("b", string="Duration:")
    duration = duration.find_next_sibling(string=True).strip() if duration else None
    # Extract just the number from "35 min."
    duration_min = (
        int(duration.split()[0]) if duration and duration.split()[0].isdigit() else None
    )

    content_rating = soup.find("b", string="Content Rating:")
    content_rating = (
        content_rating.find_next_sibling(string=True).strip()
        if content_rating
        else None
    )

    network = soup.find("b", string="Original Network:")
    network = network.find_next_sibling() if network else None
    network = network.get_text(strip=True) if network else None

    # --- Year from Aired field ---
    year = None
    aired = soup.find("b", string="Aired:")
    if aired:
        aired_text = aired.next_sibling
        if aired_text:
            aired_text = aired_text.strip()
            try:
                year = int(aired_text.split()[-1][:4])
            except (ValueError, IndexError):
                years = re.findall(r"\d{4}", aired_text)
                year = int(years[0]) if years else None

    # --- Genres & Tags ---
    genres_section = soup.find("b", string="Genres:")
    genres = []
    if genres_section:
        for a in genres_section.find_next_siblings("a"):
            genres.append(a.get_text(strip=True))

    tags = []
    tags_li = soup.find("li", class_="show-tags")
    if tags_li:
        for span in tags_li.find_all("span"):
            a = span.find("a", class_="text-primary")
            if a:
                tags.append(a.get_text(strip=True))

    # --- Score ---
    score = None
    hfs_div = soup.find("div", class_="hfs")
    if hfs_div:
        score_b = hfs_div.find("b")
        if score_b:
            try:
                score = float(score_b.get_text(strip=True))
            except ValueError:
                score = None
    # --- Watchers ---
    watchers = None
    for hfs in soup.find_all("div", class_="hfs"):
        text = hfs.get_text()
        if "Watchers" in text:
            b_tag = hfs.find("b")
            if b_tag:
                try:
                    watchers = int(b_tag.get_text(strip=True).replace(",", ""))
                except ValueError:
                    watchers = None
            break

    return {
        "mdl_id": mdl_id,
        "mdl_url": url,
        "title": title,
        "native_title": native_title,
        "also_known_as": also_known_as,
        "synopsis": synopsis,
        "country": country,
        "episodes": episodes,
        "duration_min": duration_min,
        "content_rating": content_rating,
        "network": network,
        "year": year,
        "genres": genres,
        "tags": tags,
        "mdl_score": score,
        "watchers": watchers,
    }


if __name__ == "__main__":
    url = "https://mydramalist.com/9025-nirvana-in-fire"
    print(f"Scraping: {url}\n")
    drama = scrape_drama_page(url)
    for key, value in drama.items():
        print(f"{key}: {value}")
