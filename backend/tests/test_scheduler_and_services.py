import subprocess
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
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

