import os
import json
import time
import redis
import logging
from datetime import datetime
from pymongo import MongoClient, errors
from scraper import scrape_article
from ai_analyzer import analyze_article

# Logging configuration
logging.basicConfig(level=logging.INFO, format="[CONSUMER] %(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Redis and MongoDB configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
MONGO_DB = os.getenv("MONGO_DB", "articles_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "articles")

PRIORITY_LEVELS = [1, 2, 3, 4, 5]

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
        collection.create_index("id", unique=True)
        break
    except errors.ConnectionFailure as e:
        logger.warning(f"MongoDB not available yet: {e}. Retrying in 5s...")
        time.sleep(5)

logger.info("Consumer service started and waiting for messages...\n")

# Function to clean LLM response and extract JSON
def clean_llm_json(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    # remove ```json ... ```
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    return text

# Process article function
def process_article(article):
    url = article.get("url")
    if not url:
        return None

    scraped = scrape_article(url)
    if not scraped:
        return None
    
    analysis_data = {
    "summary": None,
    "sentiment": None,
    "keywords": []
}

    try:
        analysis = analyze_article(scraped["title"], scraped["content"])
        cleaned = clean_llm_json(analysis)
        analysis_data = json.loads(cleaned)
    except Exception as e:
        logger.warning(f"AI parsing failed: {e}")

    now = datetime.now()
    return {
        "id": article["id"],
        "url": url,
        "source": article["source"],
        "category": article["category"],
        "title": scraped["title"],
        "content": scraped["content"],
        "summary": analysis_data["summary"],
        "sentiment": analysis_data["sentiment"],
        "keywords": analysis_data["keywords"],
        "word_count": scraped["word_count"],
        "priority": article["priority"],
        "created_at": now,
    }



priority_keys = [f"articles:priority:{p}" for p in PRIORITY_LEVELS]

# Main loop
while True:
    try:
        item = r.brpop(priority_keys, timeout=0)
        if not item:
            continue

        _, message = item

        try:
            article = json.loads(message)
        except json.JSONDecodeError:
            r.lpush("articles:failed", message)
            logger.warning("Invalid JSON, moved to failed list")
            continue

        logger.info(f"Processing job ID: {article.get('id')} | URL: {article.get('url')}")

        document = process_article(article)
        if not document:
            r.lpush("articles:failed", message)
            logger.warning("Scrape failed, moved to failed list")
            continue

        collection.insert_one(document)
        logger.info(f"✅ Job {article.get('id')} completed and stored in database")

    except redis.exceptions.ConnectionError:
        logger.error("Lost Redis connection, retrying in 5s...")
        time.sleep(5)
    except errors.PyMongoError as e:
        logger.error(f"MongoDB error: {e}, retrying in 5s...")
        time.sleep(5)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
