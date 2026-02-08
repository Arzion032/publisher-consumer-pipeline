import time
import redis
import json
import os

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

print("Publisher service started")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

with open('articles.json', 'r') as file:
    data = json.load(file)
    
    for article in data:
        try:
            r.rpush('articles', json.dumps(article))
            print(f"Published {article['url']}")
            time.sleep(1)
        except redis.exceptions.ConnectionError:
            print("Failed to connect to Redis, retrying in 5s...")
            time.sleep(5)
        
    print('Successfully published all articles')
