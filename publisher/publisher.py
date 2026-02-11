import json
import logging
import time

import redis

from common.connections import create_mongo_collection, create_redis_client
from common.validation import validate_article_payload

# Logging configuration
logging.basicConfig(level=logging.INFO, format="[PUBLISHER] %(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Enqueue article function
def enqueue_article(r: redis.Redis, article: dict, max_retries: int = 3):
    payload = json.dumps(article)
    priority = article.get("priority", 3)
    list_name = f"articles:priority:{priority}"
    delay = 1

    # Try to enqueue the article
    for attempt in range(1, max_retries + 1):
        try:
            # Enqueue the article
            r.rpush(list_name, payload)
            logger.info(f"Published {article['url']} (id={article['id']}) to {list_name}")
            return True
        except redis.exceptions.ConnectionError as e:
            logger.warning(f"Redis connection error on attempt {attempt}: {e}")
            # If the attempt is the maximum retries, log the failure and return False
            if attempt == max_retries:
                logger.error(f"Max retries reached for article id={article.get('id')}. Skipping.")
                return False
            time.sleep(delay)
            delay *= 2
        except Exception as e:
            logger.error(f"Unexpected error publishing article id={article.get('id')}: {e}")
            return False

# Main loop
def main():
    logger.info("Publisher service started")

    r = create_redis_client()
    collection = create_mongo_collection()

    # Load the articles from the JSON file
    with open("articles.json", "r") as file:
        # Load the data from the JSON file
        data = json.load(file)

    # Initialize the published and skipped counts
    published_count = 0
    skipped_count = 0

    for article in data:
        # Get the article ID
        article_id = article.get("id")
        
        # If the article is already in the database, skip it
        if collection is not None and collection.find_one({"id": article_id}):
            # Log the skipped article
            logger.info(f"Skipping article id={article_id} (already in database)")
            skipped_count += 1
            continue

        # Validate payload before enqueueing. Invalid articles are sent to articles:failed list
        is_valid, error = validate_article_payload(article)
        if not is_valid:
            # Log the invalid article
            logger.warning(f"Invalid article payload id={article_id}: {error}")
            try:
                # Push the invalid article to the failed list       
                r.lpush("articles:failed", json.dumps(article))
            except Exception as e:
                logger.error(
                    f"Failed to push invalid article id={article_id} to 'articles:failed': {e}"
                )
            continue

        # Enqueue the article
        if enqueue_article(r, article):
            # Increment the published count
            published_count += 1

        time.sleep(1)

    logger.info(f"Finished publishing articles: {published_count} published, {skipped_count} skipped")

if __name__ == "__main__":
    main()
