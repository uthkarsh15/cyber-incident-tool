import json
import os
import sys
from typing import Any

from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


STATS_PREFIX = os.environ.get("STATS_PREFIX", "SCHEDULER_SPIDER_STATS")


def _print_stats(spider_name: str, stats: dict[str, Any], finish_reason: str) -> None:
    emit = {
        "spider": spider_name,
        "finish_reason": finish_reason,
        "items_scraped": int(stats.get("item_scraped_count", 0) or 0),
        "response_count": int(stats.get("response_received_count", 0) or 0),
        "error_count": int(stats.get("log_count/ERROR", 0) or 0),
    }
    sys.stdout.write("\n")
    sys.stdout.write(STATS_PREFIX)
    sys.stdout.write(" ")
    sys.stdout.write(json.dumps(emit))
    sys.stdout.write("\n")
    sys.stdout.flush()


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: run_one_spider.py <spider_name>", file=sys.stderr)
        return 2

    spider_name = sys.argv[1]
    settings = get_project_settings()
    env_redis = os.environ.get("REDIS_URL")
    if env_redis:
        settings.set("REDIS_URL", env_redis, priority="cmdline")

    process = CrawlerProcess(settings, install_root_handler=False)
    crawler = process.create_crawler(spider_name)

    capture: dict[str, Any] = {}

    def _on_closed(reason: str):  # type: ignore[no-untyped-def]
        capture["finish_reason"] = reason
        try:
            capture["stats"] = crawler.stats.get_stats()
        except Exception:
            capture["stats"] = {}

    crawler.signals.connect(_on_closed, signals.spider_closed)
    process.crawl(crawler)
    try:
        process.start(stop_after_crawl=True)
    except Exception as exc:  # noqa: BLE001
        print(f"CrawlerProcess crashed: {exc!r}", file=sys.stderr)
        stats = capture.get("stats", {})
        _print_stats(spider_name, stats, capture.get("finish_reason", "crashed"))
        return 1

    stats = capture.get("stats", {})
    _print_stats(spider_name, stats, capture.get("finish_reason", "unknown"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
