import logging
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings
from app.database import get_sql_echo, engine
from app.agents.relevance_agent import RelevanceAgent

@pytest.mark.asyncio
async def test_relevance_agent_high_score():
    agent = RelevanceAgent()
    data = {
        "title": "CERT-In Advisory on Ransomware",
        "content": "Major ransomware attack hits Indian healthcare system.",
        "source_name": "CERT-In"
    }
    result = await agent.process(data)
    assert result is not None
    assert result["is_india_relevant"] is True
    assert result["india_relevance_score"] >= 0.9

@pytest.mark.asyncio
async def test_relevance_agent_low_score():
    agent = RelevanceAgent()
    data = {
        "title": "Local business in Ohio hacked",
        "content": "No connection to anywhere else.",
        "source_name": "Some Blog"
    }
    result = await agent.process(data)
    assert result is None  # Should be discarded

@pytest.mark.asyncio
async def test_relevance_agent_logs_accept_verdict(caplog):
    agent = RelevanceAgent()
    data = {
        "title": "Indian Bank Cyber Breach",
        "content": "Major security incident reported in Mumbai involving UPI systems.",
        "source_name": "NewsSource",
        "source_url": "https://example.com/bank-breach-india",
    }
    with caplog.at_level(logging.INFO, logger="agent.relevance"):
        result = await agent.process(data)

    assert result is not None
    assert result["is_india_relevant"] is True
    assert result["india_relevance_score"] >= 0.4

    relevance_logs = [r for r in caplog.records if r.name == "agent.relevance"]
    assert len(relevance_logs) == 1
    msg = relevance_logs[0].message
    assert "verdict=ACCEPT" in msg
    assert "url=https://example.com/bank-breach-india" in msg
    assert 'title="Indian Bank Cyber Breach"' in msg

@pytest.mark.asyncio
async def test_relevance_agent_logs_reject_verdict(caplog):
    agent = RelevanceAgent()
    data = {
        "title": "Local business in Ohio hacked",
        "content": "No connection to anywhere else.",
        "source_name": "Some Blog",
        "source_url": "https://example.com/ohio-local-breach",
    }
    with caplog.at_level(logging.INFO, logger="agent.relevance"):
        result = await agent.process(data)

    assert result is None

    relevance_logs = [r for r in caplog.records if r.name == "agent.relevance"]
    assert len(relevance_logs) == 1
    msg = relevance_logs[0].message
    assert "verdict=REJECT" in msg
    assert "url=https://example.com/ohio-local-breach" in msg
    assert 'title="Local business in Ohio hacked"' in msg

def test_sql_echo_configuration(monkeypatch):
    monkeypatch.delenv("SQL_ECHO", raising=False)
    assert get_sql_echo() is False
    assert engine.echo is False

    monkeypatch.setenv("SQL_ECHO", "true")
    assert get_sql_echo() is True
    test_engine = create_async_engine(settings.database_url, echo=get_sql_echo())
    assert test_engine.echo is True
