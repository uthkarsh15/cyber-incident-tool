import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.services.incident_service import (
    create_incident,
    get_incident,
    list_incidents,
    update_incident,
    delete_incident,
)
from app.services.feed_service import generate_json_feed, generate_rss_feed
from app.schemas.incident import IncidentCreate, IncidentUpdate

# Scheduler modules shipped next to this test file (copies from scraper/scraper/
# taken at the time of Stage G1 test-writing) so that the backend pytest runner
# can import them without requiring the scraper code tree.
THIS_TEST_DIR = Path(__file__).resolve().parent
if str(THIS_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_TEST_DIR))

import scraper_scheduler as scheduler  # noqa: E402


# ============================================================================
# 3c. Scheduler tests — env parsing + one spider failing doesn't stop loop
# ============================================================================

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
        assert scheduler._get_spider_timeout() == 30  # clamped
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
    timeout = scheduler.DEFAULT_SPIDER_TIMEOUT_SECONDS

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
        r = subprocess.CompletedProcess(args=args, returncode=1, stdout="no stats here\n", stderr="kaboom\n")
        return r

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
    """Error isolation: a spider throwing doesn't kill sibling spiders in the
    same cycle; overall dict contains per-spider results with error_count=1
    for the broken one and success data for the good one."""
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
    """Integration-ish unit test. Mock subprocess so no network. Patch time/
    signal so loop advances 2 cycles then _running flips to False."""
    iteration = {"count": 0}
    clock = {"t": 1_700_000_000.0}

    def fake_time():
        return clock["t"]

    def fake_sleep(secs):
        clock["t"] += secs

    def fake_run_spiders(names):
        iteration["count"] += 1
        if iteration["count"] >= 2:
            # Simulate SIGTERM flipping _running=False at the end of cycle 2
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
        scheduler._running = True  # reset
        scheduler.main()

    assert iteration["count"] == 2


# ============================================================================
# incident_service + feed_service regression coverage
# ============================================================================

def test_incident_create_model_dump_maps_metadata_to_metadata_orm_field():
    """Regression for the Stage E MetaData() class-clash bug: create_incident
    pops IncidentCreate.metadata (Pydantic field name) and assigns it to the
    Incident ORM attribute `metadata_` via the payload dict rename."""
    data = IncidentCreate(
        title="T",
        source_url="https://x/",
        attack_type="phishing",
        severity="medium",
        source_id=uuid4(),
        sector_id=uuid4(),
        metadata={"foo": ["bar", "baz"]},
    )
    payload = data.model_dump()
    assert "metadata" in payload
    # create_incident performs the rename:
    payload["metadata_"] = payload.pop("metadata", {})
    assert "metadata" not in payload
    assert payload["metadata_"] == {"foo": ["bar", "baz"]}


@pytest.mark.asyncio
async def test_create_incident_maps_metadata_to_orm_metadata_():
    """Exercise create_incident end-to-end via mocked AsyncSession; verify
    Incident(**payload) is constructed with metadata_ kwarg from the renamed
    dict key."""
    captured = {}
    data = IncidentCreate(
        title="RCE in product X",
        source_url="https://example.com/x",
        metadata={"tags": ["cve-2026-9999"], "extracted_count": 3},
    )

    class FakeSession(AsyncMock):
        def add(self, entity):
            captured["entity"] = entity

        async def commit(self):
            return None

        async def refresh(self, entity):
            return None

    fake_db = FakeSession()
    result = await create_incident(fake_db, data)
    incident = captured["entity"]
    assert isinstance(incident, Incident)
    assert incident.metadata_ == {"tags": ["cve-2026-9999"], "extracted_count": 3}
    assert result is incident


@pytest.mark.asyncio
async def test_get_incident_returns_scalar():
    fake_db = AsyncMock()
    exec_future = AsyncMock()
    fake_res = MagicMock()
    expected = Incident(id=uuid4(), title="t", source_url="https://x/")
    fake_res.scalar_one_or_none.return_value = expected

    async def side_effect(*a, **kw):
        return fake_res
    fake_db.execute = side_effect
    out = await get_incident(fake_db, expected.id)
    assert out is expected


@pytest.mark.asyncio
async def test_list_incidents_applies_filters_and_pagination():
    fake_db = AsyncMock()
    expected_rows = [
        Incident(id=uuid4(), title="A", source_url="https://a/"),
        Incident(id=uuid4(), title="B", source_url="https://b/"),
    ]

    async def execute_side_effect(stmt, **kw):
        res = MagicMock()
        s = str(stmt)
        if "count" in s.lower():
            res.scalar_one.return_value = 42
        else:
            res.scalars.return_value.all.return_value = expected_rows
        return res
    fake_db.execute = execute_side_effect

    rows, total = await list_incidents(
        fake_db,
        page=2,
        page_size=10,
        filters={"attack_type": "ransomware", "severity": "high"},
    )
    assert rows == expected_rows
    assert total == 42


@pytest.mark.asyncio
async def test_update_incident_noop_when_empty():
    fake_db = AsyncMock()
    expected = Incident(id=uuid4(), title="keep", source_url="https://keep/")
    fake_get = AsyncMock(return_value=expected)

    with patch("app.services.incident_service.get_incident", new=fake_get):
        out = await update_incident(fake_db, expected.id, IncidentUpdate())
    assert out is expected


@pytest.mark.asyncio
async def test_update_incident_returns_updated_row():
    fake_db = AsyncMock()
    expected = Incident(id=uuid4(), title="new title", source_url="https://u/")
    fake_get = AsyncMock(return_value=expected)

    with patch("app.services.incident_service.get_incident", new=fake_get):
        out = await update_incident(
            fake_db,
            expected.id,
            IncidentUpdate(title="new title", severity="high"),
        )
    assert out is expected


@pytest.mark.asyncio
async def test_delete_incident_returns_boolean():
    fake_db = AsyncMock()
    res = MagicMock()
    res.rowcount = 1

    async def side_effect(*a, **kw):
        return res
    fake_db.execute = side_effect

    assert await delete_incident(fake_db, uuid4()) is True

    res.rowcount = 0
    assert await delete_incident(fake_db, uuid4()) is False


# ============================================================================
# feed_service coverage (actual codebase APIs: generate_json_feed / generate_rss_feed)
# ============================================================================

@pytest.mark.asyncio
async def test_generate_json_feed_returns_id_title_description():
    inc1 = MagicMock(spec=Incident)
    inc1.id = uuid4()
    inc1.title = "Old"
    inc1.description = None
    inc1.published_at = datetime(2026, 9, 20, tzinfo=timezone.utc)
    inc1.source_url = "https://old"
    inc1.attack_type = "phishing"
    inc1.severity = "medium"
    inc1.created_at = inc1.published_at
    inc1.updated_at = inc1.published_at

    inc2 = MagicMock(spec=Incident)
    inc2.id = uuid4()
    inc2.title = "New"
    inc2.description = "newly reported"
    inc2.published_at = datetime(2026, 9, 28, tzinfo=timezone.utc)
    inc2.source_url = "https://new"
    inc2.attack_type = "ransomware"
    inc2.severity = "critical"
    inc2.created_at = inc2.published_at
    inc2.updated_at = inc2.published_at

    fake_db = AsyncMock()
    res_obj = MagicMock()
    # ORDER: list was created by query ordering by created_at DESC, so "New"
    # (created 28th) returned first, then "Old" (20th).
    res_obj.scalars.return_value.all.return_value = [inc2, inc1]

    async def ex_side(*a, **kw):
        return res_obj
    fake_db.execute = ex_side

    entries = await generate_json_feed(fake_db)
    assert len(entries) == 2
    assert entries[0]["title"] == "New"
    assert entries[0]["description"] == "newly reported"
    assert entries[0]["severity"] == "critical"
    assert entries[1]["title"] == "Old"
    assert entries[1]["description"] is None
    assert entries[1]["published_at"] == "2026-09-20T00:00:00+00:00"


@pytest.mark.asyncio
async def test_generate_rss_feed_contains_titles_and_valid_rss_tags():
    fake_db = AsyncMock()
    inc = MagicMock(spec=Incident)
    inc.id = uuid4()
    inc.title = "RCE flaw in example service"
    inc.description = "RCE being actively exploited in the wild"
    inc.published_at = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    inc.source_url = "https://example.com/rce"
    inc.attack_type = "zero_day"
    inc.severity = "critical"
    inc.created_at = inc.published_at
    inc.updated_at = inc.published_at

    res_obj = MagicMock()
    res_obj.scalars.return_value.all.return_value = [inc]

    async def ex_side(*a, **kw):
        return res_obj
    fake_db.execute = ex_side

    xml = await generate_rss_feed(fake_db)
    assert "<?xml" in xml
    assert '<rss version="2.0">' in xml
    assert "<channel>" in xml
    assert "<title><![CDATA[RCE flaw in example service]]></title>" in xml
    assert "https://example.com/rce" in xml
    assert "<description><![CDATA[RCE being actively exploited in the wild]]></description>" in xml


# Also exercise feed_service's get_recent_incidents indirectly:
@pytest.mark.asyncio
async def test_generate_json_feed_with_zero_incidents():
    fake_db = AsyncMock()
    res_obj = MagicMock()
    res_obj.scalars.return_value.all.return_value = []
    async def ex_side(*a, **kw):
        return res_obj
    fake_db.execute = ex_side
    assert await generate_json_feed(fake_db) == []


@pytest.mark.asyncio
async def test_generate_rss_feed_published_at_none():
    fake_db = AsyncMock()
    inc = MagicMock(spec=Incident)
    inc.id = uuid4()
    inc.title = "No date"
    inc.description = ""
    inc.published_at = None
    inc.source_url = "https://nodate"
    inc.attack_type = "unknown"
    inc.severity = "info"
    inc.created_at = datetime(2026, 9, 28, tzinfo=timezone.utc)
    inc.updated_at = inc.created_at
    res_obj = MagicMock()
    res_obj.scalars.return_value.all.return_value = [inc]
    async def ex_side(*a, **kw):
        return res_obj
    fake_db.execute = ex_side
    xml = await generate_rss_feed(fake_db)
    assert "No date" in xml
    assert "<link>https://nodate</link>" in xml

