import json
import logging
import os
import signal
import subprocess
import sys
import time
from typing import Any, Iterable


DEFAULT_INTERVAL_MINUTES: int = 30  # per PROJECT_RULES.md §5.1 Required Environment Variables
DEFAULT_SPIDERS: str = "news"  # Only news_spider scheduled by default; certin broken, github missing
DEFAULT_SPIDER_TIMEOUT_SECONDS: int = 900  # 15 minutes per spider (safe: each yields after (news_scraper 2-min scrapy_crawl 15m default
STATS_PREFIX = "SCHEDULER_SPIDER_STATS"
LOG_FORMAT: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"

logger = logging.getLogger("scraper_scheduler")


def _configure_logging() -> None:
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
    level_name = os.getenv("SCRAPER_LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))


def _get_spider_list() -> list[str]:
    raw = os.getenv("SCRAPER_SPIDERS", DEFAULT_SPIDERS) or DEFAULT_SPIDERS
    return [n.strip() for n in raw.split(",") if n.strip()]


def _get_interval_minutes() -> int:
    try:
        value = int(os.getenv("SCRAPER_INTERVAL_MINUTES", str(DEFAULT_INTERVAL_MINUTES)))
    except (TypeError, ValueError):
        logger.warning(
            "Invalid SCRAPER_INTERVAL_MINUTES=%r, falling back to %d min",
            os.getenv("SCRAPER_INTERVAL_MINUTES"),
            DEFAULT_INTERVAL_MINUTES,
        )
        value = DEFAULT_INTERVAL_MINUTES
    return max(1, value)


def _get_spider_timeout() -> int:
    try:
        value = int(os.getenv("SCRAPER_SPIDER_TIMEOUT_SECONDS", str(DEFAULT_SPIDER_TIMEOUT_SECONDS)))
    except (TypeError, ValueError):
        value = DEFAULT_SPIDER_TIMEOUT_SECONDS
    return max(30, value)


def _parse_stats(line: str) -> dict[str, Any] | None:
    if STATS_PREFIX not in line:
        return None
    try:
        return json.loads(line.split(STATS_PREFIX, 1)[1].strip())
    except Exception:
        return None


def _run_one_spider(name: str) -> dict[str, Any]:
    wrapper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_one_spider.py")
    env = os.environ.copy()
    env.setdefault("STATS_PREFIX", STATS_PREFIX)
    if not env.get("PYTHONUNBUFFERED"):
        env["PYTHONUNBUFFERED"] = "1"
    timeout = _get_spider_timeout()
    try:
        proc = subprocess.run(
            [sys.executable, wrapper, name],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
    except subprocess.TimeoutExpired:
        return {
            "spider": name,
            "items_scraped": 0,
            "finish_reason": "timeout",
            "response_count": 0,
            "error_count": 1,
            "exit_code": -1,
            "error": f"timeout after {timeout}s",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "spider": name,
            "items_scraped": 0,
            "finish_reason": "launch_error",
            "response_count": 0,
            "error_count": 1,
            "exit_code": -1,
            "error": repr(exc),
        }

    # emit Scrapy logs to stdout via our wrapper emits everything under sun to stdout → re-route all combined. Print through logger by dumping relevant bits to stdout since subprocess captured them. Print the combined stdout to stderr so logs go to our own docker logs too.
    combined = (proc.stdout or "") + ("\n" if (proc.stdout or "").endswith("\n") else "") + (proc.stderr or "")
    # Emit combined output lines as debug; they are already timestamped, but docker will show via stream. Print combined (Scrapy scrapy log)
    for line in combined.splitlines():
        if not line.strip():
            continue
        if STATS_PREFIX in line:
            continue  # stats handled below
        # always print via stdout (captured stdout so docker logs it)
        print(line, flush=True)

    stats: dict[str, Any] | None = None
    for line in (proc.stdout or "").splitlines() + (proc.stderr or "").splitlines():
        stats = _parse_stats(line)
        if stats is not None:
            break

    if stats is None:
        # Wrapper crashed (python-level crash) → no stats output → infer from exit_code
        stats = {
            "spider": name,
            "items_scraped": 0,
            "finish_reason": "crashed",
            "response_count": 0,
            "error_count": 1,
            "exit_code": proc.returncode,
        }
    else:
        stats.setdefault("exit_code", proc.returncode)
    stats["spider"] = name
    stats.setdefault("items_scraped", 0)
    stats.setdefault("finish_reason", "unknown")
    stats.setdefault("response_count", 0)
    stats.setdefault("error_count", 0)
    return stats


def run_spiders(spider_names: Iterable[str]) -> dict[str, dict[str, Any]]:
    per_spider: dict[str, dict[str, Any]] = {}
    for name in spider_names:
        logger.info("spider=%s action=launch", name)
        try:
            result = _run_one_spider(name)
        except Exception as exc:  # noqa: BLE001
            result = {
                "spider": name,
                "items_scraped": 0,
                "finish_reason": "setup_error",
                "response_count": 0,
                "error_count": 1,
                "error": repr(exc),
            }
        per_spider[name] = result
    return per_spider


_running = True


def _shutdown_handler(signum, frame):  # noqa: ARG001
    global _running
    logger.info("Received signal=%d, shutting scheduler down after current cycle", signum)
    _running = False


def main() -> None:
    _configure_logging()
    signal.signal(signal.SIGTERM, _shutdown_handler)
    if os.name != "nt":
        signal.signal(signal.SIGINT, _shutdown_handler)

    spider_names = _get_spider_list()
    interval_min = _get_interval_minutes()

    logger.info(
        "scheduler_started spiders=%s interval_min=%d download_delay=settings_default_2s robots_obey=settings_default_true",
        ",".join(spider_names),
        interval_min,
    )

    while _running:
        run_started = time.time()
        run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(run_started))
        logger.info("run=%s action=start spiders=%s", run_id, ",".join(spider_names))

        total_items = 0
        failed_spiders: list[str] = []

        try:
            per_spider = run_spiders(spider_names)
        except Exception as exc:  # noqa: BLE001
            logger.error("run=%s action=crashed error=%r (continuing next cycle)", run_id, exc)
            per_spider = {}

        for spider_name, stats in per_spider.items():
            scraped = int(stats.get("items_scraped") or 0)
            reason = stats.get("finish_reason")
            errors = int(stats.get("error_count") or 0)
            exit_code = stats.get("exit_code")
            total_items += scraped
            if reason not in ("finished", "closespider_itemcount", "closespider_timeout"):
                failed_spiders.append(f"{spider_name}:{reason}")
            logger.info(
                "run=%s spider=%s items_scraped=%d finish_reason=%s errors=%d exit_code=%s",
                run_id,
                spider_name,
                scraped,
                reason,
                errors,
                exit_code,
            )

        duration = max(time.time() - run_started, 0.0)
        logger.info(
            "run=%s action=end total_items=%d duration_sec=%.1f failed=%s",
            run_id,
            total_items,
            duration,
            failed_spiders if failed_spiders else "none",
        )
        if not _running:
            break

        sleep_seconds = max(float(interval_min * 60) - duration, 1.0)
        logger.info("run=%s next_run_in=%.0fs (%.1f min)", run_id, sleep_seconds, sleep_seconds / 60)
        # Sleep in 0.5s ticks to remain responsive to SIGTERM
        end = time.time() + sleep_seconds
        while _running and time.time() < end:
            time.sleep(0.5)

    logger.info("scheduler_stopped run_cycle_ended=true")


if __name__ == "__main__":
    main()
