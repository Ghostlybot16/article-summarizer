import os 
import redis 

def main():
    # Connects to Redis running locally
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    
    # Redis connection object
    r = redis.from_url(redis_url, decode_responses=True)
    
    
    r.set("article_reader:test", "ok", ex=60) # Set a test key in Redis
    
    val = r.get("article_reader:test") # Retrieve key back from Redis
    
    print(f"Redis URL: {redis_url}")
    print(f"Test key value: {repr(val)}") # Show quotes ('') around returned string
    
    if val == "ok":
        print("Redis connection successful")
    else:
        print("Redis connection failed")


if __name__ == "__main__":
    main()