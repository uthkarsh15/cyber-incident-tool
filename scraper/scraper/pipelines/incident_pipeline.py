import json
import os
import redis
from datetime import datetime, timezone
from urllib.parse import urlparse


class RedisQueuePipeline:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    @classmethod
    def from_crawler(cls, crawler):
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        parsed = urlparse(redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        db = int(parsed.path.lstrip("/") or "0")
        client = redis.Redis(host=host, port=port, db=db)
        return cls(redis_client=client)

    def open_spider(self, spider):
        pass

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
