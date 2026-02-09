import time
import redis
import json
import os
import logging
from pymongo import MongoClient, errors

# Logging configuration
logging.basicConfig(level=logging.INFO, format="[PUBLISHER] %(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Redis and MongoDB configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
MONGO_DB = os.getenv("MONGO_DB", "articles_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "articles")

# Reddit and MongoDB connections
while True:
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        # test connection
        r.ping()
        logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        break
    except redis.exceptions.ConnectionError as e:
        logger.warning(f"Redis not available yet: {e}. Retrying in 5s...")
        time.sleep(5)

while True:
    try:
        mongo_client = MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")
        collection = mongo_client[MONGO_DB][MONGO_COLLECTION]
        logger.info("Connected to MongoDB successfully")
        break
    except errors.ConnectionFailure as e:
        logger.warning(f"MongoDB not available yet: {e}. Retrying in 5s...")
        time.sleep(5)

# Enqueue article function
def enqueue_article(article, max_retries=3):
    payload = json.dumps(article)
    priority = article.get("priority", 3)
    list_name = f"articles:priority:{priority}"
    delay = 1

    for attempt in range(1, max_retries + 1):
        try:
            r.rpush(list_name, payload)
            logger.info(f"Published {article['url']} (id={article['id']}) to {list_name}")
            return True
        except redis.exceptions.ConnectionError as e:
            logger.warning(f"Redis connection error on attempt {attempt}: {e}")
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

    with open("articles.json", "r") as file:
        data = json.load(file)

    published_count = 0
    skipped_count = 0

    for article in data:
        article_id = article.get("id")
        
        
        if collection is not None and collection.find_one({"id": article_id}):
            logger.info(f"⏭️  Skipping article id={article_id} (already in database)")
            skipped_count += 1
            continue

        if enqueue_article(article):
            published_count += 1

        time.sleep(1)

    logger.info(f"Finished publishing articles: {published_count} published, {skipped_count} skipped")

if __name__ == "__main__":
    main()
