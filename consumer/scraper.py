import time
import requests
import trafilatura
from trafilatura import extract
from trafilatura.settings import use_config
from urllib.parse import urlparse
import logging

# Logger configuration
logger = logging.getLogger("SCRAPER")

# Trafilatura configuration
config = use_config()
config.set(
    "DEFAULT", "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
)

# Minimum seconds between requests to the same host
RATE_LIMIT_DELAY = 2.0

# Dictionary to store the last request time for each domain
last_request_by_domain = {}

# Get the domain from the URL
def get_domain(url):

    try:
        parsed = urlparse(url)
        # netloc is the hostname (and optional port), e.g. "example.com:443"
        return parsed.netloc or ""
    except Exception:
        return ""

# Wait for the rate limit
def wait_for_rate_limit(domain):

    if not domain:
        return

    last_request_time = last_request_by_domain.get(domain)
    now = time.time()

    # If we've hit this domain before, ensure we wait at least RATE_LIMIT_DELAY.
    if last_request_time is not None:
        elapsed = now - last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)

    # Record this request time so the next request to this domain will wait for RATE_LIMIT_DELAY seconds
    last_request_by_domain[domain] = time.time()

# Scrape article function 
def scrape_article(url, retries=2, timeout=30):

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Attempt {attempt} for URL: {url}")

            # wait if we recently requested this host (per-domain rate limit).
            domain = get_domain(url)
            wait_for_rate_limit(domain)

            # Get the response
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'
                }
            )
            # Raise an exception if the response is not successful
            response.raise_for_status()
            # Get the downloaded text
            downloaded = response.text

            # If the downloaded text is empty, raise an exception
            if not downloaded:
                # Log the failure
                raise Exception("Failed to fetch URL")

            # Extract the content
            content = extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                config=config
            )

            # If the content is empty or less than 150 words, log the failure
            if not content or len(content.split()) < 150:
                logger.warning(f"Article too short or empty: {url}")
                return None

            # Attempt to extract title from metadata
            # If the title is not found, fallback to the first non-empty line
            title = None
            try:
                meta = trafilatura.extract_metadata(downloaded)
                title = meta.title if meta and getattr(meta, 'title', None) else None
            except Exception:
                title = None

            if not title:
                # Get the first non-empty line
                lines = [l.strip() for l in content.splitlines() if l.strip()]
                title = lines[0] if lines else ""

            # Get the word count
            word_count = len(content.split())
            # Log the success
            logger.info(f"Success: {word_count} words scraped from {url}")

            # Return the scraped data
            return {
                "title": title.strip(),
                "content": content.strip(),
                "word_count": word_count,
            }

        except requests.Timeout:
            logger.warning(f"Timeout after {timeout}s for {url}")
            # Calculate the sleep time
            sleep_time = 2 ** attempt
            # If the attempt is less than the retries, sleep for the sleep time
            if attempt < retries:
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)

        except requests.RequestException as e:
            logger.error(f"Request error scraping {url}: {e}")
            # Calculate the sleep time
            sleep_time = 2 ** attempt
            # If the attempt is less than the retries, sleep for the sleep time
            if attempt < retries:
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            # Calculate the sleep time
            sleep_time = 2 ** attempt
            # If the attempt is less than the retries, sleep for the sleep time
            if attempt < retries:
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)

    # Log the failure
    logger.error(f"Failed after {retries} attempts: {url}")
    return None
