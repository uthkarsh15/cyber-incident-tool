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
    assert "keywords=" in msg

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
    assert "keywords=" in msg

@pytest.mark.asyncio
async def test_relevance_agent_whole_word_matching(caplog):
    agent = RelevanceAgent()

    # 1. "arbitrary" contains 'rbi', "occupied" contains 'upi' as substrings -> must NOT match -> REJECT
    substring_only_data = {
        "title": "Arbitrary code execution flaw in occupied building systems",
        "content": "Just arbitrary and occupied memory locations tested.",
        "source_name": "TechBlog",
        "source_url": "https://example.com/arbitrary-occupied",
    }
    with caplog.at_level(logging.INFO, logger="agent.relevance"):
        result = await agent.process(substring_only_data)

    assert result is None
    relevance_logs = [r for r in caplog.records if r.name == "agent.relevance"]
    assert len(relevance_logs) == 1
    assert "verdict=REJECT" in relevance_logs[0].message
    assert "keywords=[]" in relevance_logs[0].message

    caplog.clear()

    # 2. "India's" and "Indian" match
    indias_data = {
        "title": "Attack on India's infrastructure",
        "content": "Security alert affecting Indian networks.",
        "source_name": "TechBlog",
        "source_url": "https://example.com/indias-infra",
    }
    with caplog.at_level(logging.INFO, logger="agent.relevance"):
        result = await agent.process(indias_data)

    assert result is not None
    assert "india" in result["india_keywords_found"]
    assert "indian" in result["india_keywords_found"]
    relevance_logs = [r for r in caplog.records if r.name == "agent.relevance"]
    assert len(relevance_logs) == 1
    assert "verdict=ACCEPT" in relevance_logs[0].message
    assert "keywords=" in relevance_logs[0].message

    caplog.clear()

    # 3. "CERT-In" matches
    certin_data = {
        "title": "CERT-In issued new cybersecurity advisory in Delhi",
        "content": "Critical patch updates released.",
        "source_name": "AdvisoryFeed",
        "source_url": "https://example.com/certin-advisory-match",
    }
    with caplog.at_level(logging.INFO, logger="agent.relevance"):
        result = await agent.process(certin_data)

    assert result is not None
    assert "cert-in" in result["india_keywords_found"]
    assert "verdict=ACCEPT" in caplog.records[-1].message

    caplog.clear()

    # 4. ".in " keyword case: domain ending with .in followed by space matches; word ending in "in" does not
    dot_in_data = {
        "title": "Breach reported at portal.in domain for Delhi office",
        "content": "Hackers targeted domain.in servers.",
        "source_name": "SecurityFeed",
        "source_url": "https://example.com/dot-in-match",
    }
    with caplog.at_level(logging.INFO, logger="agent.relevance"):
        result = await agent.process(dot_in_data)

    assert result is not None
    assert ".in " in result["india_keywords_found"]

def test_sql_echo_configuration(monkeypatch):
    monkeypatch.delenv("SQL_ECHO", raising=False)
    assert get_sql_echo() is False
    assert engine.echo is False

    monkeypatch.setenv("SQL_ECHO", "true")
    assert get_sql_echo() is True
    test_engine = create_async_engine(settings.database_url, echo=get_sql_echo())
    assert test_engine.echo is True
