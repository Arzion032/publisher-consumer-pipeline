import time
import trafilatura
from trafilatura import extract, fetch_url


def scrape_article(url, retries=2):
    for attempt in range(1, retries + 1):
        try:
            print(f"[SCRAPER] Attempt {attempt} for URL: {url}")

            downloaded = fetch_url(url)
            if not downloaded:
                raise Exception("Failed to fetch URL")

            content = extract(downloaded, include_comments=False, include_tables=False)

            if not content or len(content.split()) < 150:
                print(f"[SCRAPER] Article too short or empty: {url}")
                return None

            # Try to get title from metadata; fall back to first headline-like line
            title = None
            try:
                meta = trafilatura.extract_metadata(downloaded)
                title = meta.title if meta and getattr(meta, 'title', None) else None
            except Exception:
                title = None

            if not title:
                # crude fallback: first non-empty line
                lines = [l.strip() for l in content.splitlines() if l.strip()]
                title = lines[0] if lines else ""

            word_count = len(content.split())

            print(f"[SCRAPER] Success: {word_count} words scraped from {url}")

            return {
                "title": title.strip(),
                "content": content.strip(),
                "word_count": word_count,
            }

        except Exception as e:
            print(f"[SCRAPER] Error scraping {url}: {e}")
            sleep_time = 2 ** attempt
            print(f"[SCRAPER] Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)

    print(f"[SCRAPER] Failed after {retries} attempts: {url}")
    return None
