import json
import logging
import time
from datetime import datetime
import redis
from pymongo import errors
from common.connections import create_mongo_collection, create_redis_client
from common.validation import validate_article_payload
from scraper import scrape_article
from ai_analyzer import analyze_article

# Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("CONSUMER")
#
# Priority levels
PRIORITY_LEVELS = [1, 2, 3, 4, 5]

# Function to clean LLM response and extract JSON
def clean_llm_json(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    # remove ```json ``` from the llm response
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
        # Analyze the article
        analysis = analyze_article(scraped["title"], scraped["content"])
        # Clean the LLM response
        cleaned = clean_llm_json(analysis)
        # Load the JSON
        analysis_data = json.loads(cleaned)
    except Exception as e:
        logger.warning(f"AI parsing failed: {e}")

    now = datetime.now()
    # Return the document
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

def save_document(collection, document, message: str, redis_client):
    try:
        # Save the document to the database
        collection.insert_one(document)
        logger.info(f"Job {document.get('id')} stored in database")
    except errors.DuplicateKeyError:
        logger.info(f"Duplicate id={document.get('id')} detected; treating as already processed")
    except errors.PyMongoError as e:
        logger.error(f"MongoDB error while saving id={document.get('id')}: {e}")
        redis_client.lpush("articles:failed", message)

def run_worker(r: redis.Redis, collection):
    logger.info("Consumer service started and waiting for messages...\n")
    priority_keys = [f"articles:priority:{p}" for p in PRIORITY_LEVELS]

    # Main loop
    while True:
        try:
            # Block until a job arrives, always checking priority-1 first (1 = highest), 
            # process items FIFO within each individual priority list
            item = r.blpop(priority_keys, timeout=0)
            if not item:
                continue

            # Get the key and message
            key, message = item
            # Load the JSON
            try:
                article = json.loads(message)
            except json.JSONDecodeError:
                # Move the message to the failed list
                r.lpush("articles:failed", message)
                logger.warning("Invalid JSON, moved to failed list")
                continue

            # Validate the payload coming from Redis before processing
            is_valid, err = validate_article_payload(article)
            if not is_valid:
                # Move the message to the failed list
                r.lpush("articles:failed", message)
                logger.warning(f"Invalid article payload, moved to failed list: {err}")
                continue

            # Process the article
            logger.info(f"Processing job ID: {article.get('id')} | URL: {article.get('url')}")
            document = process_article(article)

            # If the document is not valid, move the message to the failed list
            if not document:
                r.lpush("articles:failed", message)
                logger.warning("Scrape failed, moved to failed list")
                continue

            # Save the document to the database
            save_document(collection, document, message, r)

        except redis.exceptions.ConnectionError:
            logger.error("Lost Redis connection, retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

def main():
    r = create_redis_client()
    collection = create_mongo_collection()
    run_worker(r, collection)

if __name__ == "__main__":
    main()
