import json
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

HERE = Path(__file__).resolve().parent
SCRAPER_PKG_DIR = HERE.parent / "scraper"
if str(SCRAPER_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(SCRAPER_PKG_DIR))

import scheduler  # noqa: E402  (real scraper/scraper/scheduler.py)


def test_get_spider_list_default_single():
    with patch.dict(os.environ, {}, clear=True):
        assert scheduler._get_spider_list() == ["news"]


def test_get_spider_list_env_csv_strips_and_ignores_blank():
    with patch.dict(os.environ, {"SCRAPER_SPIDERS": " news , certin, , github "}):
        assert scheduler._get_spider_list() == ["news", "certin", "github"]


def test_get_interval_minutes_default():
    with patch.dict(os.environ, {}, clear=True):
        assert scheduler._get_interval_minutes() == 30


def test_get_interval_minutes_env_integer():
    with patch.dict(os.environ, {"SCRAPER_INTERVAL_MINUTES": "15"}):
        assert scheduler._get_interval_minutes() == 15


def test_get_interval_minutes_invalid_falls_back_to_default():
    with patch.dict(os.environ, {"SCRAPER_INTERVAL_MINUTES": "not_a_number"}):
        assert scheduler._get_interval_minutes() == 30


def test_get_interval_minutes_zero_or_negative_clamped_to_one():
    with patch.dict(os.environ, {"SCRAPER_INTERVAL_MINUTES": "0"}):
        assert scheduler._get_interval_minutes() == 1
    with patch.dict(os.environ, {"SCRAPER_INTERVAL_MINUTES": "-10"}):
        assert scheduler._get_interval_minutes() == 1


def test_get_spider_timeout_default_and_clamp_and_invalid():
    with patch.dict(os.environ, {}, clear=True):
        assert scheduler._get_spider_timeout() == 900
    with patch.dict(os.environ, {"SCRAPER_SPIDER_TIMEOUT_SECONDS": "5"}):
        assert scheduler._get_spider_timeout() == 30
    with patch.dict(os.environ, {"SCRAPER_SPIDER_TIMEOUT_SECONDS": "abc"}):
        assert scheduler._get_spider_timeout() == 900


def test_parse_stats_parses_prefix_and_json():
    line = (
        "2026-09-30 prefix "
        "SCHEDULER_SPIDER_STATS "
        '{"spider":"news","items_scraped":16,"finish_reason":"finished",'
        '"response_count":20,"error_count":0}'
    )
    stats = scheduler._parse_stats(line)
    assert stats is not None
    assert stats["spider"] == "news"
    assert stats["items_scraped"] == 16
    assert stats["finish_reason"] == "finished"


def test_parse_stats_no_prefix_returns_none():
    assert scheduler._parse_stats("2026-09-30 just a regular log line") is None


def test_parse_stats_bad_json_returns_none():
    assert scheduler._parse_stats("SCHEDULER_SPIDER_STATS {not-json") is None


def test_run_one_spider_subprocess_timeout_isolated():
    name = "slow_spider"

    def fake_run(*args, timeout, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=timeout)

    with patch.object(subprocess, "run", side_effect=fake_run):
        stats = scheduler._run_one_spider(name)
    assert stats["spider"] == name
    assert stats["items_scraped"] == 0
    assert stats["finish_reason"] == "timeout"
    assert stats["error_count"] == 1


def test_run_one_spider_subprocess_launch_error_isolated():
    def fake_run(*args, **kwargs):
        raise OSError("python binary missing")

    with patch.object(subprocess, "run", side_effect=fake_run):
        stats = scheduler._run_one_spider("broken_launcher")
    assert stats["finish_reason"] == "launch_error"
    assert stats["error_count"] == 1


def test_run_one_spider_wrapper_crash_no_stats_output():
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="no stats here\n", stderr="kaboom\n"
        )

    with patch.object(subprocess, "run", side_effect=fake_run):
        stats = scheduler._run_one_spider("crasher")
    assert stats["finish_reason"] == "crashed"
    assert stats["error_count"] == 1
    assert stats["exit_code"] == 1
    assert stats["items_scraped"] == 0


def test_run_one_spider_happy_path_extracts_stats():
    fake_stdout_lines = [
        "2026-09-30 scrapy log 1",
        "2026-09-30 scrapy log 2",
        'SCHEDULER_SPIDER_STATS {"spider":"news","items_scraped":16,"finish_reason":"finished","response_count":20,"error_count":0}',
    ]

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="\n".join(fake_stdout_lines) + "\n", stderr=""
        )

    with patch.object(subprocess, "run", side_effect=fake_run):
        stats = scheduler._run_one_spider("news")
    assert stats["spider"] == "news"
    assert stats["items_scraped"] == 16
    assert stats["finish_reason"] == "finished"
    assert stats["error_count"] == 0
    assert stats["exit_code"] == 0
    assert stats["response_count"] == 20


def test_run_spiders_one_spider_fails_does_not_affect_siblings():
    call_log = []

    def fake_run_one_spider(name: str):
        call_log.append(name)
        if name == "broken":
            raise RuntimeError("spider imploded")
        return {
            "spider": name, "items_scraped": 5, "finish_reason": "finished",
            "response_count": 10, "error_count": 0, "exit_code": 0,
        }

    with patch.object(scheduler, "_run_one_spider", side_effect=fake_run_one_spider):
        per_spider = scheduler.run_spiders(["good1", "broken", "good2"])

    assert "good1" in call_log and "broken" in call_log and "good2" in call_log
    assert per_spider["good1"]["items_scraped"] == 5 and per_spider["good1"]["error_count"] == 0
    assert per_spider["broken"]["error_count"] == 1
    assert per_spider["broken"]["finish_reason"] == "setup_error"
    assert per_spider["good2"]["items_scraped"] == 5 and per_spider["good2"]["error_count"] == 0


def test_main_loop_runs_two_cycles_then_sigterm_exits():
    iteration = {"count": 0}
    clock = {"t": 1_700_000_000.0}

    def fake_time():
        return clock["t"]

    def fake_sleep(secs):
        clock["t"] += secs

    def fake_run_spiders(names):
        iteration["count"] += 1
        if iteration["count"] >= 2:
            scheduler._running = False
        return {
            "news": {
                "spider": "news", "items_scraped": 2, "finish_reason": "finished",
                "response_count": 5, "error_count": 0, "exit_code": 0,
            }
        }

    with patch.object(scheduler, "_get_interval_minutes", return_value=1), \
         patch.object(scheduler, "_get_spider_list", return_value=["news"]), \
         patch.object(scheduler, "run_spiders", side_effect=fake_run_spiders), \
         patch.object(scheduler.signal, "signal"), \
         patch.object(scheduler.time, "time", side_effect=fake_time), \
         patch.object(scheduler.time, "sleep", side_effect=fake_sleep):
        scheduler._running = True
        scheduler.main()

    assert iteration["count"] == 2
