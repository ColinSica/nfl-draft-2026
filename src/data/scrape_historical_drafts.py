"""
Scrape historical NFL draft data (2011-2025) from Pro Football Reference.
Uses undetected_chromedriver to bypass Cloudflare protection.
Saves results to data/raw/historical_drafts_2011_2025.csv
"""

import time
import random
from pathlib import Path

import pandas as pd
import undetected_chromedriver as uc
from bs4 import BeautifulSoup, Comment

BASE_URL = "https://www.pro-football-reference.com/years/{year}/draft.htm"
YEARS = range(2011, 2026)
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "historical_drafts_2011_2025.csv"

# Columns we want to extract, keyed by PFR's data-stat attribute
COLUMNS_MAP = {
    "draft_round": "round",
    "draft_pick": "pick",
    "team": "team",
    "player": "player",
    "pos": "position",
    "age": "age",
    "college_id": "college",
    "g": "games_played",
    "all_pros_first_team": "all_pro_1st",
    "pro_bowls": "pro_bowls",
    "years_as_primary_starter": "years_starter",
    "career_av": "career_av",
    "draft_av": "draft_av",
}


def create_driver() -> uc.Chrome:
    """Create an undetected Chrome driver (visible window to pass Cloudflare)."""
    opts = uc.ChromeOptions()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,720")
    return uc.Chrome(options=opts)


def fetch_draft_page(driver: uc.Chrome, year: int) -> str | None:
    """Navigate to a draft year page and return the page source."""
    url = BASE_URL.format(year=year)
    try:
        driver.get(url)
        # Wait for page to fully load / Cloudflare to clear
        time.sleep(5)

        # Verify we got past Cloudflare
        if "Just a moment" in driver.title:
            print("  Waiting for Cloudflare challenge...", end=" ", flush=True)
            time.sleep(10)

        if "Just a moment" in driver.title:
            print("  ERROR: stuck on Cloudflare challenge")
            return None

        return driver.page_source
    except Exception as e:
        print(f"  ERROR fetching {year}: {e}")
        return None


def parse_draft_table(html: str, year: int) -> list[dict]:
    """Parse the draft table from PFR HTML. Handles commented-out tables."""
    soup = BeautifulSoup(html, "lxml")
    rows = []

    # PFR sometimes wraps tables in HTML comments to defer loading.
    # First try finding the table directly, then search inside comments.
    table = soup.find("table", id="drafts")
    if table is None:
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            if 'id="drafts"' in comment:
                comment_soup = BeautifulSoup(comment, "lxml")
                table = comment_soup.find("table", id="drafts")
                if table:
                    break

    if table is None:
        print(f"  WARNING: No draft table found for {year}")
        return rows

    tbody = table.find("tbody")
    if tbody is None:
        return rows

    for tr in tbody.find_all("tr"):
        # Skip header/separator rows
        if tr.get("class") and "thead" in tr["class"]:
            continue

        row = {"year": year}
        for stat_name, col_name in COLUMNS_MAP.items():
            cell = tr.find(["td", "th"], attrs={"data-stat": stat_name})
            if cell is None:
                row[col_name] = None
                continue

            if stat_name in ("player", "team", "college_id"):
                link = cell.find("a")
                row[col_name] = link.get_text(strip=True) if link else cell.get_text(strip=True)
            else:
                text = cell.get_text(strip=True)
                row[col_name] = text if text else None

        # Only include rows that have a player name (skip empty/separator rows)
        if row.get("player"):
            rows.append(row)

    return rows


def main():
    all_rows = []
    errors = []

    print(f"Scraping NFL draft data from {YEARS.start} to {YEARS.stop - 1}...")
    print("Launching Chrome browser...")
    print("-" * 50)

    driver = create_driver()

    # Hit homepage first to establish session / pass initial Cloudflare check
    driver.get("https://www.pro-football-reference.com/")
    time.sleep(8)

    try:
        for year in YEARS:
            print(f"Fetching {year}...", end=" ", flush=True)
            html = fetch_draft_page(driver, year)

            if html is None:
                errors.append(year)
                continue

            rows = parse_draft_table(html, year)
            all_rows.extend(rows)
            print(f"{len(rows)} picks scraped")

            # Polite delay: 1-2 seconds between requests
            delay = 1.0 + random.random()
            time.sleep(delay)
    finally:
        try:
            driver.quit()
        except OSError:
            pass  # Ignore handle errors on cleanup

    print("-" * 50)

    if not all_rows:
        print("No data scraped. Exiting.")
        return

    df = pd.DataFrame(all_rows)

    # Reorder columns
    col_order = ["year", "round", "pick", "team", "player", "position", "age",
                 "college", "games_played", "all_pro_1st",
                 "pro_bowls", "years_starter", "career_av", "draft_av"]
    df = df[[c for c in col_order if c in df.columns]]

    # Convert numeric columns
    numeric_cols = ["round", "pick", "age", "games_played",
                    "all_pro_1st", "pro_bowls", "years_starter", "career_av", "draft_av"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved to {OUTPUT_PATH}")

    # Summary
    print(f"\n{'='*50}")
    print(f"Total rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nFirst 5 rows:")
    print(df.head().to_string(index=False))

    if errors:
        print(f"\nYears with scraping errors: {errors}")
    else:
        print("\nAll years scraped successfully!")

    # Per-year breakdown
    print(f"\nPicks per year:")
    print(df.groupby("year").size().to_string())


if __name__ == "__main__":
    main()
