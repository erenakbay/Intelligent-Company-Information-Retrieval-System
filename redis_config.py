import redis
import os

REDIS_HOST = os.getenv("REDIS_HOST", "redis")  
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    redis_client.ping()  
    print("! Connected to Redis!")
except redis.ConnectionError:
    print("! Redis connection failed. Ensure Redis is running.")
    redis_client = None  
