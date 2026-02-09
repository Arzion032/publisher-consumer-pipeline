import time
import requests
import trafilatura
from trafilatura import extract
from trafilatura.settings import use_config


config = use_config()
config.set("DEFAULT", "USER_AGENT", 
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")

def scrape_article(url, retries=2, timeout=30):

    for attempt in range(1, retries + 1):
        try:
            print(f"[SCRAPER] Attempt {attempt} for URL: {url}")

            response = requests.get(
                url, 
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'
                }
            )
            response.raise_for_status()
            downloaded = response.text
            
            if not downloaded:
                raise Exception("Failed to fetch URL")

            content = extract(
                downloaded, 
                include_comments=False, 
                include_tables=False,
                config=config
            )

            if not content or len(content.split()) < 150:
                print(f"[SCRAPER] Article too short or empty: {url}")
                return None

            # Try to get title from metadata, fall back to first headline-like line
            title = None
            try:
                meta = trafilatura.extract_metadata(downloaded)
                title = meta.title if meta and getattr(meta, 'title', None) else None
            except Exception:
                title = None

            if not title:
                # get first non-empty line
                lines = [l.strip() for l in content.splitlines() if l.strip()]
                title = lines[0] if lines else ""

            word_count = len(content.split())

            print(f"[SCRAPER] Success: {word_count} words scraped from {url}")

            return {
                "title": title.strip(),
                "content": content.strip(),
                "word_count": word_count,
            }

        except requests.Timeout:
            print(f"[SCRAPER] Timeout error after {timeout}s for {url}")
            sleep_time = 2 ** attempt
            if attempt < retries:
                print(f"[SCRAPER] Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
                
        except requests.RequestException as e:
            print(f"[SCRAPER] Request error scraping {url}: {e}")
            sleep_time = 2 ** attempt
            if attempt < retries:
                print(f"[SCRAPER] Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
                
        except Exception as e:
            print(f"[SCRAPER] Error scraping {url}: {e}")
            sleep_time = 2 ** attempt
            if attempt < retries:
                print(f"[SCRAPER] Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)

    print(f"[SCRAPER] Failed after {retries} attempts: {url}")
    return None