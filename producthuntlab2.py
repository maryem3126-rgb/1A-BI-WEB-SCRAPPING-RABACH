
import json
import csv
import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

from selenium.webdriver.chrome.service import Service
import subprocess

BASE_URL   = "https://www.producthunt.com/search?q=mental+health+ai"
JSON_FILE  = "products.json"
CSV_FILE   = "products.csv"
MAX_PAGES  = 3
HEADLESS   = True
try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_MANAGER = True
except ImportError:
    USE_MANAGER = False



from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def build_driver():

    options = Options()

    # TEST SANS HEADLESS
    # options.add_argument("--headless=new")

    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    return driver

def fetch_page_source(url: str, page_num: int) -> str:
    """
    Start the session, navigate to URL, write page source to file, quit driver.
    Returns the raw HTML string.
    """
    driver = build_driver()
    source = ""
    try:
        print(f"  [browser] Opening {url}")
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/posts/']"))
        )

        for _ in range(3):
            driver.execute_script("window.scrollBy(0, window.innerHeight)")
            time.sleep(random.uniform(0.8, 1.2))

        source = driver.page_source

        filename = f"page_source_{page_num}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(source)
        print(f"  [browser] Page source saved → {filename}")

    except Exception as e:
        print(f"  [!] Error fetching {url}: {e}")
    finally:
        driver.quit()   

    return source


# ── 2. Parse page source → JSON ───────────────────────────────────────────────

def parse_products(html: str, id_offset: int = 0) -> list[dict]:
    """
    Extract product cards from HTML using multiple Selenium location strategies:
      - href pattern matching  (link detection)
      - CSS selectors          (tagline, votes)
      - tag name search        (time element)
    Handles missing fields gracefully (exception/None safety).
    """
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a", href=lambda h: h and "/posts/" in h)

    seen, products = set(), []

    for link in links:
        try:
            href = link["href"]
            if not href.startswith("http"):
                href = "https://www.producthunt.com" + href

            name = link.get_text(strip=True)
            if not name or len(name) <= 2 or href in seen:
                continue
            seen.add(href)

            # Tagline: look in nearest parent block for a <p> tag
            tagline = ""
            try:
                parent = link.find_parent("div") or link.find_parent()
                if parent:
                    p = parent.find("p")
                    if p:
                        tagline = p.get_text(strip=True)[:200]
            except Exception:
                pass

            # Votes: find a numeric value in sibling/parent elements
            votes = None
            try:
                container = link.find_parent("div")
                if container:
                    for el in container.find_all(["button", "span"]):
                        raw = el.get_text(strip=True).replace(",", "")
                        digits = "".join(filter(str.isdigit, raw))
                        if digits and int(digits) < 100_000:
                            votes = int(digits)
                            break
            except Exception:
                pass

            products.append({
                "id":           id_offset + len(products) + 1,
                "name":         name,
                "url":          href,
                "tagline":      tagline,
                "votes":        votes,
                "rating":       None,   # from product detail page
                "review_count": None,   # from product detail page
                "topics":       [],     # from product detail page
                "description":  "",     # from product detail page
                "website":      "",     # from product detail page
                "makers":       [],     # from product detail page
                "launch_date":  "",     # from product detail page
            })

        except Exception as e:
            print(f"  [!] Skipping a product due to error: {e}")
            continue

    return products


def append_to_json(new_products: list[dict], path: str):
    """
    Append new products to the JSON file (intermediary storage).
    Deduplicates by URL so re-runs don't create duplicate records.
    """
    existing = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    existing_urls = {p["url"] for p in existing}
    added = 0
    for p in new_products:
        if p["url"] not in existing_urls:
            existing.append(p)
            existing_urls.add(p["url"])
            added += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4, ensure_ascii=False)

    print(f"  [json] +{added} new products → {path} ({len(existing)} total)")


# ── 3. Pagination ─────────────────────────────────────────────────────────────

def scrape_all_pages():
    """
    Iterate through MAX_PAGES search result pages.
    Waiting strategy: re-initialize driver per page, wait for DOM elements.
    Appends results to JSON after each page (safe against crashes mid-run).
    """
    print(f"\n── Scraping {MAX_PAGES} page(s) of search results ──")
    id_offset = 0

    for page_num in range(1, MAX_PAGES + 1):
        url = BASE_URL if page_num == 1 else f"{BASE_URL}&page={page_num}"
        print(f"\n[Page {page_num}] {url}")

        html = fetch_page_source(url, page_num)
        if not html:
            print(f"  [!] No HTML returned for page {page_num}, skipping.")
            continue

        products = parse_products(html, id_offset=id_offset)
        print(f"  [parse] {len(products)} products found on page {page_num}")

        append_to_json(products, JSON_FILE)
        id_offset += len(products)

        time.sleep(random.uniform(2, 4))  # polite delay between pages


# ── 4. JSON → CSV ─────────────────────────────────────────────────────────────

def export_csv():
    """Parse the JSON file and export a structured CSV."""
    if not os.path.exists(JSON_FILE):
        print("[!] No JSON file found. Run scrape_all_pages() first.")
        return

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    fields = ["id", "name", "tagline", "votes", "rating", "review_count",
              "topics", "launch_date", "website", "makers", "url", "description"]

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            row["topics"] = ", ".join(row.get("topics") or [])
            row["makers"] = ", ".join(row.get("makers") or [])
            writer.writerow(row)

    print(f"\n[✓] CSV exported → {CSV_FILE} ({len(data)} rows)")


# ── 5. Product detail pages ───────────────────────────────────────────────────

def scrape_product_detail(driver: webdriver.Chrome, product: dict) -> dict:
    """
    Navigate to a product page and extract detailed metadata.
    Uses multiple CSS selectors with try/except for each field
    (not all fields exist on every product page).
    """
    try:
        driver.get(product["url"])

        # Waiting strategy: wait for <h1> before parsing
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
        except Exception:
            pass

        time.sleep(random.uniform(1, 2))
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Tagline
        try:
            for sel in ["h2", "p[class*='tagline']", "p[class*='subtitle']"]:
                el = soup.select_one(sel)
                if el:
                    text = el.get_text(strip=True)
                    if 10 < len(text) < 200:
                        product["tagline"] = text
                        break
        except Exception:
            pass

        # Description
        try:
            for sel in ["div[class*='description']", "section[class*='about']", "div[class*='body']"]:
                el = soup.select_one(sel)
                if el:
                    text = el.get_text(separator=" ", strip=True)
                    if len(text) > 30:
                        product["description"] = text[:600]
                        break
        except Exception:
            pass

        # Votes
        try:
            for sel in ["button[class*='vote']", "div[class*='voteCount']", "span[class*='vote']"]:
                el = soup.select_one(sel)
                if el:
                    digits = "".join(filter(str.isdigit, el.get_text(strip=True).replace(",", "")))
                    if digits:
                        product["votes"] = int(digits)
                        break
        except Exception:
            pass

        # Rating & review count
        try:
            rating_el = soup.select_one("[class*='rating']")
            if rating_el:
                digits = "".join(c for c in rating_el.get_text(strip=True) if c.isdigit() or c == ".")
                if digits:
                    product["rating"] = float(digits[:3])
        except Exception:
            pass

        try:
            review_el = soup.select_one("[class*='review'][class*='count']")
            if review_el:
                digits = "".join(filter(str.isdigit, review_el.get_text(strip=True)))
                if digits:
                    product["review_count"] = int(digits)
        except Exception:
            pass

        # Topics
        try:
            product["topics"] = list({
                el.get_text(strip=True)
                for el in soup.select("a[href*='/topics/']")
                if el.get_text(strip=True)
            })[:8]
        except Exception:
            pass

        # Launch date
        try:
            time_el = soup.find("time")
            if time_el:
                product["launch_date"] = time_el.get("datetime", time_el.get_text(strip=True))
        except Exception:
            pass

        # External website
        try:
            for link in soup.select("a[href*='://']"):
                href = link.get("href", "")
                if (href.startswith("http")
                        and "producthunt.com" not in href
                        and "twitter.com" not in href):
                    product["website"] = href
                    break
        except Exception:
            pass

        # Makers
        try:
            product["makers"] = list({
                el.get_text(strip=True)
                for el in soup.select("a[href*='/@']")
                if el.get_text(strip=True)
            })[:5]
        except Exception:
            pass

    except Exception as e:
        print(f"  [!] Failed detail scrape for {product['name']}: {e}")

    return product


def enrich_with_details():
    if not os.path.exists(JSON_FILE):
        print("[!] No JSON file found. Run scrape_all_pages() first.")
        return

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)

    os.makedirs("product_details", exist_ok=True)

    print(f"\n── Enriching {len(products)} products with detail pages ──")
    driver = build_driver()

    try:
        for i, product in enumerate(products, 1):
            print(f"[{i}/{len(products)}] {product['name']}")
            products[i - 1] = scrape_product_detail(driver, product)

            # Save individual JSON file per product (best practice)
            safe_name = "".join(c if c.isalnum() else "_" for c in product["name"])[:50]
            detail_path = f"product_details/{safe_name}.json"
            with open(detail_path, "w", encoding="utf-8") as f:
                json.dump(products[i - 1], f, indent=4, ensure_ascii=False)

            time.sleep(random.uniform(1.5, 3))

    finally:
        driver.quit()

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=4, ensure_ascii=False)

    print(f"\n[✓] Enriched data saved → {JSON_FILE} + product_details/")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scrape_all_pages()

    export_csv()

    enrich_with_details()

    export_csv()

    print("\n── Done ──")
    print(f"  {JSON_FILE}          ← full product data (JSON)")
    print(f"  {CSV_FILE}           ← structured dataset (CSV)")
    print(f"  product_details/     ← one JSON file per product")
    print(f"  page_source_N.html   ← raw HTML per search page")