"""
Load the PFR 2020 draft page and print every <thead> cell's data-stat +
visible label so we can correct COLUMNS_MAP in scrape_historical_drafts.py.
Does not extract row data.
"""

import time

import undetected_chromedriver as uc
from bs4 import BeautifulSoup, Comment

URL = "https://www.pro-football-reference.com/years/2020/draft.htm"


def main():
    opts = uc.ChromeOptions()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,720")
    driver = uc.Chrome(options=opts)
    try:
        driver.get("https://www.pro-football-reference.com/")
        time.sleep(8)
        driver.get(URL)
        time.sleep(6)
        if "Just a moment" in driver.title:
            time.sleep(10)
        html = driver.page_source
    finally:
        try:
            driver.quit()
        except OSError:
            pass

    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="drafts")
    if table is None:
        for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
            if 'id="drafts"' in c:
                table = BeautifulSoup(c, "lxml").find("table", id="drafts")
                if table:
                    break
    if table is None:
        print("No #drafts table found")
        return

    thead = table.find("thead")
    if thead is None:
        print("No <thead> in #drafts")
        return

    print(f"{'data-stat':<40} label")
    print("-" * 70)
    for th in thead.find_all("th"):
        stat = th.get("data-stat", "")
        label = th.get_text(strip=True)
        if stat:
            print(f"{stat:<40} {label}")


if __name__ == "__main__":
    main()
