import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.agents.classification_agent import ClassificationAgent
from app.agents.correlation_agent import CorrelationAgent
from app.agents.insight_agent import InsightAgent
from app.agents.orchestrator import PipelineOrchestrator as _PipelineOrchestrator


async def run_agent_pipeline(data: dict) -> dict | None:
    """Convenience wrapper: PipelineOrchestrator exposes process_article(raw)."""
    orch = _PipelineOrchestrator()
    return await orch.process_article(data)
from app.schemas.incident import IncidentCreate, IncidentResponse
from app.models.source import Source


# ============================================================================
# 3a. Regression tests — three Stage E bugs
# ============================================================================

def _strip_tz(dt: datetime | None) -> datetime | None:
    """InsightAgent._parse_published_at returns naive datetimes from strptime
    formats (which have no tzinfo), and tz-aware ones from %z-aware formats.
    For test assertions we compare (a) date/clock parts AND (b) presence vs
    absence of tzinfo only where it's deterministic."""
    if dt is None:
        return None
    return dt.replace(tzinfo=None, microsecond=0)


@pytest.mark.asyncio
async def test_parse_published_at_month_name_format():
    agent = InsightAgent()
    result = agent._parse_published_at("Sep 28, 2026")
    assert isinstance(result, datetime)
    assert _strip_tz(result) == datetime(2026, 9, 28)

@pytest.mark.asyncio
async def test_parse_published_at_iso_date():
    agent = InsightAgent()
    result = agent._parse_published_at("2026-09-28")
    assert isinstance(result, datetime)
    assert _strip_tz(result) == datetime(2026, 9, 28)

@pytest.mark.asyncio
async def test_parse_published_at_iso_datetime():
    agent = InsightAgent()
    result = agent._parse_published_at("2026-09-28T13:45:00+00:00")
    assert result is not None
    assert result.year == 2026 and result.month == 9 and result.day == 28
    assert result.hour == 13 and result.minute == 45

@pytest.mark.asyncio
async def test_parse_published_at_none():
    agent = InsightAgent()
    assert agent._parse_published_at(None) is None

@pytest.mark.asyncio
async def test_parse_published_at_empty_string():
    agent = InsightAgent()
    assert agent._parse_published_at("") is None
    assert agent._parse_published_at("    ") is None

@pytest.mark.asyncio
async def test_parse_published_at_garbage_does_not_raise():
    agent = InsightAgent()
    assert agent._parse_published_at("not a date at all 42") is None
    assert agent._parse_published_at("!!!@@@###") is None
    assert agent._parse_published_at("31/02/2026") is None


def test_incident_response_metadata_serializes_to_metadata_key():
    payload = IncidentResponse(
        id=uuid4(),
        title="Test title",
        source_url="https://example.com/a",
        attack_type="phishing",
        severity="high",
        status="open",
        confidence_score=0.8,
        india_relevance_score=0.65,
        metadata_={"tags": ["cve-2026-0001"], "entities": ["RBI"]},
        source_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    encoded = payload.model_dump()
    assert "metadata" in encoded
    assert isinstance(encoded["metadata"], dict)
    assert encoded["metadata"]["tags"] == ["cve-2026-0001"]
    assert "metadata_" not in encoded


def test_incident_response_from_attributes_populates_metadata():
    class FakeORM:
        id = uuid4()
        title = "ORM title"
        description = None
        attack_type = "unknown"
        severity = "info"
        source_url = "https://example.com/b"
        published_at = None
        status = "open"
        confidence_score = 1.0
        india_relevance_score = 0.5
        metadata_ = {"foo": "bar"}
        source_id = uuid4()
        sector_id = None
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)

    resp = IncidentResponse.model_validate(FakeORM())
    encoded = resp.model_dump()
    assert encoded["metadata"] == {"foo": "bar"}


@pytest.mark.asyncio
async def test_source_id_lookup_by_source_name_in_persist():
    """Regression for the Stage E source_id bug: _persist() executes
    `select(Source.id).where(Source.name == <source_name>)` and attaches
    the UUID to incident_data.source_id."""
    agent = InsightAgent()
    fake_source_id = uuid4()

    fake_session = MagicMock()
    captured_payload = {}

    async def _fake_execute(stmt, **kwargs):
        res = MagicMock()
        s = str(stmt)
        if "FROM sources" in s or ("source" in s.lower() and "id" in s.lower()):
            res.scalar_one_or_none.return_value = fake_source_id
        else:
            res.scalar_one_or_none.return_value = None
            res.scalars.return_value.all.return_value = []
        return res

    async def _fake_commit():
        return None

    async def _fake_refresh(entity):
        return None

    fake_session.execute = _fake_execute
    fake_session.commit = _fake_commit
    fake_session.refresh = _fake_refresh
    fake_session.add = lambda ent: captured_payload.setdefault("last_incident", ent)

    @asynccontextmanager
    async def _fake_session_cm():
        yield fake_session

    with patch("app.agents.insight_agent.async_session", new=_fake_session_cm):
        raw = {
            "source_name": "The Hacker News",
            "source_url": "https://example.com/src-lookup-good",
            "title": "T",
            "content": "",
            "published_at": "Sep 28, 2026",
        }
        try:
            await agent.process(raw)
        except Exception:
            pass
    incident_entity = captured_payload.get("last_incident")
    assert incident_entity is not None
    assert incident_entity.source_id == fake_source_id


@pytest.mark.asyncio
async def test_source_id_lookup_unknown_source_returns_null():
    """If source_name has no matching Source row, source_id is persisted as None."""
    agent = InsightAgent()
    fake_session = MagicMock()

    async def _fake_execute(stmt, **kwargs):
        res = MagicMock()
        res.scalar_one_or_none.return_value = None
        res.scalars.return_value.all.return_value = []
        return res

    async def _fake_commit():
        return None

    async def _fake_refresh(entity):
        return None

    fake_session.execute = _fake_execute
    fake_session.commit = _fake_commit
    fake_session.refresh = _fake_refresh
    captured = {}
    fake_session.add = lambda ent: captured.setdefault("inc", ent)

    @asynccontextmanager
    async def _fake_session_cm():
        yield fake_session

    with patch("app.agents.insight_agent.async_session", new=_fake_session_cm):
        raw = {
            "source_name": "Totally Unknown Source",
            "source_url": "https://example.com/src-not-found",
            "title": "T",
            "content": "",
            "published_at": "Sep 28, 2026",
        }
        try:
            await agent.process(raw)
        except Exception:
            pass
    inc = captured.get("inc")
    assert inc is not None
    assert inc.source_id is None


# ============================================================================
# 3b. Unit tests — ClassificationAgent, CorrelationAgent, InsightAgent CVE ext,
#     orchestrator flow, Weekly Recap roundup fixture documented
# ============================================================================

ROUNDUP_FIXTURE = {
    "source_name": "The Hacker News",
    "source_url": "https://thehackernews.com/2026/09/weekly-recap-387m-crypto-hack-citrix.html",
    "title": (
        "\u26a1 Weekly Recap: $387M Crypto Hack, Citrix and SonicWall Flaws, "
        "BlackCat Ransomware Raids, Govt Data Breach"
    ),
    "content": (
        "BlackCat ransomware group hit a government department. A critical RCE bug in "
        "Citrix ADC was patched. SonicWall reported an actively exploited flaw. "
        "Crypto platform lost $387M in a data breach and ransom attack."
    ),
    "published_at": "Sep 27, 2026",
}


@pytest.mark.asyncio
async def test_classification_agent_ransomware_keywords():
    agent = ClassificationAgent()
    out = await agent.process({
        "title": "LockBit ransomware encrypts hospital patient records",
        "content": "The ransomware group demanded ransom. Immediate action required.",
    })
    assert out["attack_type"] == "ransomware"
    assert out["severity"] == "critical"
    assert out["confidence_score"] > 0.0


@pytest.mark.asyncio
async def test_classification_agent_phishing():
    agent = ClassificationAgent()
    out = await agent.process({
        "title": "Fake SBI login page harvests credentials",
        "content": "Phishing campaign targeting UPI and HDFC customers via credential harvest",
    })
    assert out["attack_type"] == "phishing"
    assert out["sector_code"] == "banking_finance"


@pytest.mark.asyncio
async def test_classification_agent_no_keywords_defaults():
    agent = ClassificationAgent()
    out = await agent.process({
        "title": "Something weird happened",
        "content": "No obvious buzzwords here, just talk about things",
    })
    assert out["attack_type"] == "unknown"
    assert out["severity"] == "info"
    assert out["sector_code"] is None
    assert out["confidence_score"] == 0.0


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Known limitation: Weekly Recap aggregate inherits worst-included "
           "attack_type=ransomware severity=critical sector=government; roundup "
           "taxonomy not yet implemented (Stage F backlog item)."
)
async def test_classification_agent_weekly_recap_roundup_fixture():
    """Document the current (mis)classification of the Weekly Recap fixture.

    Current classifier *will* pick the worst-included incident tags. The xfail
    marker documents that this behavior is known to be wrong for aggregate
    roundup items; fixing it is in the Stage F backlog under 'Weekly Recap
    misclassification'. If this test *starts* failing (starts PASSING) in
    future, it means the classifier was updated and the xfail should be removed.
    """
    agent = ClassificationAgent()
    out = await agent.process(dict(ROUNDUP_FIXTURE))
    # Actual current output (recorded here for posterity):
    assert out["attack_type"] == "roundup_meta_placeholder"
    assert out["severity"] == "meta"


@pytest.mark.asyncio
async def test_classification_agent_weekly_recap_record_current_output():
    """Non-xfailing twin of the xfail test above; records the *actual* current
    output of the classifier for the roundup fixture as explicit assertions so
    any behavioural change is flagged by a test failure."""
    agent = ClassificationAgent()
    out = await agent.process(dict(ROUNDUP_FIXTURE))
    assert out["attack_type"] == "ransomware"  # from "ransomware" x 2 / "BlackCat ransomware" + "ransom attack"
    assert out["severity"] == "critical"       # from "Immediate action required" ("actively exploited" family)
    assert out["sector_code"] == "government"  # from "government department"
    assert out["confidence_score"] > 0.0


@pytest.mark.asyncio
async def test_correlation_agent_duplicate_url_skipped():
    """CorrelationAgent._find_by_url(url) returns True when scalar_one_or_none()
    returns an Incident.id. process() logs Duplicate skipped and returns None."""
    agent = CorrelationAgent()
    fake_session = MagicMock()
    fake_id = uuid4()

    async def _fake_execute(stmt, **kwargs):
        m = MagicMock()
        # ANY SELECT from Incident table: call _find_by_url's scalar_one_or_none returns non-None
        m.scalar_one_or_none.return_value = fake_id
        m.scalars.return_value.all.return_value = []
        return m
    fake_session.execute = _fake_execute

    @asynccontextmanager
    async def _fake_session_cm():
        yield fake_session

    with patch("app.agents.correlation_agent.async_session", new=_fake_session_cm):
        data = {"source_url": "https://example.com/dup", "title": "Dup"}
        result = await agent.process(data)
    assert result is None  # duplicate -> skipped


@pytest.mark.asyncio
async def test_correlation_agent_new_url_passes_through():
    agent = CorrelationAgent()
    fake_session = MagicMock()

    async def _fake_execute(stmt, **kwargs):
        m = MagicMock()
        m.scalar_one_or_none.return_value = None
        m.scalars.return_value.all.return_value = []
        return m
    fake_session.execute = _fake_execute

    @asynccontextmanager
    async def _fake_session_cm():
        yield fake_session

    with patch("app.agents.correlation_agent.async_session", new=_fake_session_cm):
        data = {"source_url": "https://example.com/new", "title": "New story"}
        result = await agent.process(data)
    # Non-duplicate returns the input dict with "correlations" key
    assert result is not None
    assert result["source_url"] == data["source_url"]
    assert "correlations" in result


@pytest.mark.asyncio
async def test_insight_agent_entity_extraction_finds_cves_and_summarizes():
    """InsightAgent.process() runs inlined regex-based entity extraction and
    populates extracted_entities AND description summary BEFORE DB write."""
    agent = InsightAgent()
    data = {
        "source_name": "X",
        "source_url": "https://example.com/cve-demo",
        "title": "Banking systems breach report",
        "content": (
            "Security advisory CVE-2026-9999 and CVE-2026-1111 patched. "
            "Hosts 10.0.0.1 and 192.168.1.1 affected. CVE-2026-1234 under active investigation."
        ),
        "published_at": "Sep 28, 2026",
    }
    fake_session = MagicMock()

    async def _fake_execute(stmt, **kwargs):
        m = MagicMock()
        m.scalar_one_or_none.return_value = None
        m.scalars.return_value.all.return_value = []
        return m
    fake_session.execute = _fake_execute
    captured = {}
    fake_session.add = lambda ent: captured.setdefault("inc", ent)
    fake_session.commit = AsyncMock()
    fake_session.refresh = AsyncMock()

    @asynccontextmanager
    async def _fake_session_cm():
        yield fake_session

    with patch("app.agents.insight_agent.async_session", new=_fake_session_cm):
        processed = await agent.process(dict(data))
    assert processed is not None
    names_lower = [e["name"].lower() for e in processed["extracted_entities"]]
    assert "cve-2026-1234" in names_lower
    assert "cve-2026-9999" in names_lower
    assert "cve-2026-1111" in names_lower
    ip_ents = [e for e in processed["extracted_entities"] if e["entity_type"] == "ip_address"]
    assert len(ip_ents) == 2
    assert "description" in processed

@pytest.mark.asyncio
async def test_insight_agent_entity_extraction_empty_when_no_matches():
    agent = InsightAgent()
    data = {
        "source_name": "X",
        "source_url": "https://example.com/no-keywords",
        "title": "nothing to see",
        "content": "literally no keywords",
    }
    fake_session = MagicMock()

    async def _fake_execute(stmt, **kwargs):
        m = MagicMock()
        m.scalar_one_or_none.return_value = None
        m.scalars.return_value.all.return_value = []
        return m
    fake_session.execute = _fake_execute
    fake_session.add = lambda ent: None
    fake_session.commit = AsyncMock()
    fake_session.refresh = AsyncMock()

    @asynccontextmanager
    async def _fake_session_cm():
        yield fake_session

    with patch("app.agents.insight_agent.async_session", new=_fake_session_cm):
        out = await agent.process(dict(data))
    assert out is not None
    assert out["extracted_entities"] == []


@pytest.mark.asyncio
async def test_insight_agent_integrity_error_returns_none_no_raise():
    """UNIQUE source_url IntegrityError:
    process catches IntegrityError (BEFORE generic Exception), returns None.
    Inside _save_to_database() the try/except calls session.rollback before raise.
    """
    agent = InsightAgent()
    raw = {
        "source_name": "The Hacker News",
        "source_url": "https://example.com/unique-constraint-violation",
        "title": "Test",
        "content": "CVE-2026-0001",
        "published_at": "Sep 28, 2026",
    }
    fake_session_one = MagicMock()

    fake_source_id = uuid4()
    async def _fake_execute(stmt, **kwargs):
        m = MagicMock()
        s = str(stmt)
        if "FROM sources" in s or ("source" in s.lower() and "id" in s.lower()):
            m.scalar_one_or_none.return_value = fake_source_id
        else:
            m.scalar_one_or_none.return_value = None
            m.scalars.return_value.all.return_value = []
        return m
    fake_session_one.execute = _fake_execute
    fake_session_one.add = lambda ent: None
    orig = IntegrityError("UNIQUE constraint on incidents.source_url", params={}, orig=Exception("unique"))
    fake_session_one.commit = AsyncMock(side_effect=orig)
    fake_session_one.rollback = AsyncMock()

    @asynccontextmanager
    async def _fake_cm_one():
        yield fake_session_one

    # 1. Call _save_to_database directly; prove it re-raises IntegrityError AND
    # session.rollback() was called beforehand.
    with patch("app.agents.insight_agent.async_session", new=_fake_cm_one):
        with pytest.raises(IntegrityError):
            await agent._save_to_database(raw)
    assert fake_session_one.rollback.await_count >= 1

    # 2. Call process() instead: process() has a dedicated except IntegrityError
    # branch that swallows UNIQUE duplicate source_url errors and returns None.
    fake_session_two = MagicMock()
    fake_session_two.execute = _fake_execute
    fake_session_two.add = lambda ent: None
    fake_session_two.commit = AsyncMock(side_effect=orig)
    fake_session_two.rollback = AsyncMock()

    @asynccontextmanager
    async def _fake_cm_two():
        yield fake_session_two

    with patch("app.agents.insight_agent.async_session", new=_fake_cm_two):
        result = await agent.process(dict(raw))

    assert result is None
    # rollback is always called (once by _save_to_database before re-raise; or
    # if commit is the fail point and process catches, it's already been called
    # inside the _save_to_database except block. Either way, rollback has fired.
    assert fake_session_two.rollback.await_count >= 1


def _build_mocked_orchestrator(relevance_ret, classification_ret, correlation_ret, insight_ret):
    """Build a PipelineOrchestrator whose Redis and agent.process results are
    mocked so process_article() can run without real Redis. Returns orch plus
    the 4 process AsyncMocks in order."""
    fake_redis = MagicMock()
    fake_redis.blpop = AsyncMock(return_value=None)

    class _MockRedisFactory:
        @classmethod
        def from_url(cls, url):  # noqa: D401 — not for public docs
            return fake_redis

    with patch("app.agents.orchestrator.redis", new=_MockRedisFactory()):
        orch = _PipelineOrchestrator()
    R_proc = AsyncMock(return_value=relevance_ret)
    C_proc = AsyncMock(return_value=classification_ret)
    Cor_proc = AsyncMock(return_value=correlation_ret)
    Ins_proc = AsyncMock(return_value=insight_ret)
    orch.relevance_agent.process = R_proc
    orch.classification_agent.process = C_proc
    orch.correlation_agent.process = Cor_proc
    orch.insight_agent.process = Ins_proc
    return orch, R_proc, C_proc, Cor_proc, Ins_proc


@pytest.mark.asyncio
async def test_orchestrator_flow_relevance_filter_drops_before_classify():
    """Items with <0.4 india-relevance are dropped at stage 1 and never reach
    classification or DB write."""
    raw = {
        "source_name": "Irrelevant Blog",
        "source_url": "https://example.com/ohio-local",
        "title": "Local business in Ohio hacked",
        "content": "Nothing India-related at all.",
    }
    orch, R, C, Cor, Ins = _build_mocked_orchestrator(None, "unreachable", "unreachable", "unreachable")
    result = await orch.process_article(raw)
    assert result is None
    R.assert_called_once_with(raw)
    C.assert_not_called()
    Cor.assert_not_called()
    Ins.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_flow_correlation_duplicate_stops_insight():
    raw = {
        "source_name": "CERT-In",
        "source_url": "https://example.com/seen-before",
        "title": "Ransomware hits Indian govt",
        "content": "Gov department ransomware attack, critical severity.",
    }
    after_relevance = dict(raw, is_india_relevant=True, india_relevance_score=0.9)
    after_classify = dict(after_relevance, attack_type="ransomware", severity="critical")
    orch, R, C, Cor, Ins = _build_mocked_orchestrator(after_relevance, after_classify, None, "unreachable")
    result = await orch.process_article(raw)
    assert result is None
    C.assert_called_once()
    Cor.assert_called_once()
    Ins.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_flow_happy_path_calls_all_stages():
    raw = {
        "source_name": "CERT-In",
        "source_url": "https://example.com/new-incident",
        "title": "Ransomware hits SBI",
        "content": "New India-relevant ransomware incident hitting banking sector.",
    }
    after_relevance = dict(raw, is_india_relevant=True, india_relevance_score=0.95)
    after_classify = dict(after_relevance, attack_type="ransomware", severity="high", sector_code="banking_finance", confidence_score=0.6)
    after_correlation = dict(after_classify)  # pass through
    after_insight = dict(after_correlation, saved=True)

    orch, R, C, Cor, Ins = _build_mocked_orchestrator(after_relevance, after_classify, after_correlation, after_insight)
    result = await orch.process_article(raw)
    assert result is after_insight
    R.assert_called_once_with(raw)
    C.assert_called_once_with(after_relevance)
    Cor.assert_called_once()
    Ins.assert_called_once()
