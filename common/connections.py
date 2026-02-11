import logging
import os
import time
import redis
from pymongo import MongoClient, errors

logger = logging.getLogger("CONNECTIONS")

# environment variables for Redis and MongoDB
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
MONGO_DB = os.getenv("MONGO_DB", "articles_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "articles")

# Create a Redis client
def create_redis_client(decode_responses: bool = True) -> redis.Redis:
    while True:
        try:
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=decode_responses,
            )
            client.ping()
            logger.info("Connected to Redis at %s:%s", REDIS_HOST, REDIS_PORT)
            return client
        except redis.exceptions.ConnectionError as exc:
            logger.warning("Redis not available yet: %s. Retrying in 5s...", exc)
            time.sleep(5)

# Create a MongoDB collection
def create_mongo_collection():
    while True:
        try:
            mongo_client = MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")
            collection = mongo_client[MONGO_DB][MONGO_COLLECTION]
            # Create a unique index on the id field
            collection.create_index("id", unique=True)
            logger.info("Connected to MongoDB successfully")
            return collection
        except errors.ConnectionFailure as exc:
            logger.warning("MongoDB not available yet: %s. Retrying in 5s...", exc)
            time.sleep(5)

