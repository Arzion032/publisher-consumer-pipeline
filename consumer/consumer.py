from pymongo import MongoClient, errors
from datetime import datetime
import time
import redis
import os 
import json

print("Consumer service started")

# Redis config
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Mongo config
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")

# Reddis connection
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# Connect to MongoDB
try:
    mongo_client = MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")
    db = mongo_client[MONGO_DB]
    collection = db[MONGO_COLLECTION]

    # Create unique index for idempotency
    collection.create_index("id", unique=True)
    print(f"Connected to MongoDB, using DB: {MONGO_DB}, collection: {MONGO_COLLECTION}")
except errors.ConnectionFailure as e:
    print("Could not connect to MongoDB:", e)
    exit(1)

print("Waiting for messages on 'articles' queue...\n")

while True:
    try:
        _, message = r.brpop('articles')
        article = json.loads(message)
        
        now = datetime.now()

        # if article is already in the database, update it. 
        # otherwise, insert a new document
        update_fields = {
            "url": article["url"],
            "source": article["source"],
            "category": article["category"],
            "priority": article["priority"],
            "updated_at": now
        }

        result = collection.update_one(
            {"id": article["id"]},
            {
                "$set": update_fields,
                "$setOnInsert": {
                    "created_at": now
                }
            },
            upsert=True
        )
            
        print("-"*40)
        
    except json.JSONDecodeError:
        print("Failed to decode message:", message)
    except redis.exceptions.ConnectionError:
        print("Lost Redis connection, retrying in 5s...")
        time.sleep(5)
    except errors.PyMongoError as e:
        print("MongoDB error:", e)
        time.sleep(5)