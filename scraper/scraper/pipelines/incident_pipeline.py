import json
import redis
from datetime import datetime, timezone

class RedisQueuePipeline:
    def __init__(self):
        self.redis_client = None

    def open_spider(self, spider):
        self.redis_client = redis.Redis(host="localhost", port=6379, db=0)

    def close_spider(self, spider):
        if self.redis_client:
            self.redis_client.close()

    def process_item(self, item, spider):
        article = {
            "source_name": item.get("source_name"),
            "source_url": item.get("source_url"),
            "title": item.get("title"),
            "content": item.get("content"),
            "published_at": item.get("published_at"),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "extra": item.get("extra", {}),
        }
        self.redis_client.rpush("incident:raw", json.dumps(article))
        return item
