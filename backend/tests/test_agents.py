import pytest
from backend.app.agents.relevance_agent import RelevanceAgent

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
