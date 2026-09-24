# AGENT_DESIGN.md — Agent Pipeline Specifications
<!-- STATUS: ACTIVE | LAST_UPDATED: 2026-09-24 | VERSION: 1.0 -->

> **Purpose**: Detailed specification for every autonomous agent in the system. Read `PROJECT_RULES.md` and `ARCHITECTURE.md` first.

---

## 1. Agent Architecture Overview

All agents follow a **pipeline pattern** — data flows through agents sequentially:

```
Scraper → Redis Queue → Relevance Agent → Classification Agent → Correlation Agent → Insight Agent → Database
```

### 1.1 Base Agent Contract

Every agent inherits from `BaseAgent` and implements the same interface:

```python
# backend/app/agents/base_agent.py

import logging
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Base class for all processing agents."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    async def process(self, data: dict) -> dict | None:
        """
        Process a single data item.
        
        Args:
            data: Input dictionary from previous pipeline stage.
            
        Returns:
            Enriched dictionary to pass to next stage, 
            or None to discard the item.
        """
        pass

    async def run_batch(self, items: list[dict]) -> list[dict]:
        """Process a batch of items, filtering out None results."""
        results = []
        for item in items:
            try:
                result = await self.process(item)
                if result is not None:
                    results.append(result)
            except Exception as e:
                self.logger.error(f"Error processing item: {e}", exc_info=True)
        return results
```

### 1.2 Pipeline Orchestrator

```python
# backend/app/agents/orchestrator.py

class PipelineOrchestrator:
    """Coordinates the sequential agent pipeline."""
    
    def __init__(self):
        self.relevance_agent = RelevanceAgent()
        self.classification_agent = ClassificationAgent()
        self.correlation_agent = CorrelationAgent()
        self.insight_agent = InsightAgent()
        self.pipeline = [
            self.relevance_agent,
            self.classification_agent,
            self.correlation_agent,
            self.insight_agent,
        ]

    async def process_article(self, raw_article: dict) -> dict | None:
        """Run a single article through the entire agent pipeline."""
        data = raw_article
        for agent in self.pipeline:
            data = await agent.process(data)
            if data is None:
                return None  # Article was filtered out
        return data
```

---

## 2. Scraper Agent

> **Location**: `scraper/spiders/` (Scrapy) + `backend/app/agents/scraper_agent.py` (coordinator)

### 2.1 Responsibility
- Crawl configured data sources on a schedule
- Extract article title, content, URL, publish date
- Push raw articles to Redis queue
- Respect rate limits and robots.txt

### 2.2 Implementation Strategy

**Scrapy spiders** handle the actual crawling. The `scraper_agent.py` in backend is a **coordinator** that:
1. Reads active sources from the database
2. Triggers Scrapy spiders via subprocess or Scrapy API
3. Monitors scrape completion
4. Updates `sources.last_scraped_at`

### 2.3 Spider Template

```python
# scraper/spiders/certin_spider.py

import scrapy
from scraper.items import RawArticleItem


class CertInSpider(scrapy.Spider):
    name = "certin"
    allowed_domains = ["cert-in.org.in"]
    start_urls = ["https://www.cert-in.org.in/s2cMainServlet?pageid=PUBVLNOTES01"]

    custom_settings = {
        "DOWNLOAD_DELAY": 2,                # 2 seconds between requests
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": "CyberIncidentBot/1.0 (+https://github.com/your-repo)",
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    }

    def parse(self, response):
        # Extract advisory links from listing page
        for link in response.css("a.advisory-link::attr(href)").getall():
            yield response.follow(link, self.parse_advisory)

    def parse_advisory(self, response):
        yield RawArticleItem(
            source_name="CERT-In",
            source_url=response.url,
            title=response.css("h1::text").get("").strip(),
            content=response.css(".advisory-content").get(""),
            published_at=None,  # Extract from page if available
        )
```

### 2.4 Scrapy Item

```python
# scraper/items.py

import scrapy

class RawArticleItem(scrapy.Item):
    source_name = scrapy.Field()
    source_url = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    published_at = scrapy.Field()
    extra = scrapy.Field()
```

### 2.5 Scrapy Pipeline (pushes to Redis)

```python
# scraper/pipelines/incident_pipeline.py

import json
import redis
from datetime import datetime, timezone


class RedisQueuePipeline:
    def __init__(self):
        self.redis_client = None

    def open_spider(self, spider):
        self.redis_client = redis.Redis(host="localhost", port=6379, db=0)

    def close_spider(self, spider):
        if self.redis_client:
            self.redis_client.close()

    def process_item(self, item, spider):
        article = {
            "source_name": item["source_name"],
            "source_url": item["source_url"],
            "title": item["title"],
            "content": item["content"],
            "published_at": item.get("published_at"),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "extra": item.get("extra", {}),
        }
        self.redis_client.rpush("incident:raw", json.dumps(article))
        return item
```

### 2.6 Scrape Rules

| Rule | Value |
|---|---|
| **Rate limit** | Minimum 2 seconds between requests per domain |
| **Robots.txt** | Must obey (Scrapy `ROBOTSTXT_OBEY = True`) |
| **User-Agent** | Must identify as `CyberIncidentBot/1.0` |
| **Concurrent domains** | Max 3 at a time |
| **Concurrent per domain** | Max 1 request at a time |
| **Retry** | 3 retries with exponential backoff |
| **Timeout** | 30 seconds per request |
| **Deduplication** | Check `source_url` against DB before queuing |

---

## 3. Relevance Agent

> **Location**: `backend/app/agents/relevance_agent.py`

### 3.1 Responsibility
- Determine if a scraped article is relevant to **Indian cyberspace**
- Assign an `india_relevance_score` (0.0–1.0)
- **Discard** articles with score below threshold

### 3.2 Algorithm (Rule-Based MVP)

```python
# India-relevance determination logic

INDIA_KEYWORDS = {
    # Direct India mentions (high weight)
    "high": [
        "india", "indian", "bharat", "cert-in", "nciipc", "nic.in",
        "gov.in", "uidai", "aadhaar", "upi", "npci", "rbi",
        "aiims", "isro", "drdo", "bsnl", "irctc", "sbi",
        "hdfc", "icici", "infosys", "tcs", "wipro", "hcl",
        "reliance", "tata", "airtel", "jio", "paytm",
        "delhi", "mumbai", "bangalore", "bengaluru", "hyderabad",
        "chennai", "kolkata", "pune", "noida", "gurgaon",
        "meity", "niti aayog",
    ],
    # Indirect indicators (medium weight)
    "medium": [
        ".in ", "south asia", "asia pacific", "subcontinent",
    ],
}

INDIA_KEYWORD_WEIGHTS = {"high": 0.3, "medium": 0.1}
RELEVANCE_THRESHOLD = 0.4  # Minimum score to pass through
```

### 3.3 Scoring Logic

```python
async def process(self, data: dict) -> dict | None:
    text = f"{data.get('title', '')} {data.get('content', '')}".lower()
    score = 0.0
    keywords_found = []

    for weight_class, keywords in INDIA_KEYWORDS.items():
        weight = INDIA_KEYWORD_WEIGHTS[weight_class]
        for keyword in keywords:
            if keyword in text:
                score += weight
                keywords_found.append(keyword)

    # Cap at 1.0
    score = min(score, 1.0)

    # Known India source gets automatic pass
    if data.get("source_name") in ["CERT-In", "NCIIPC"]:
        score = max(score, 0.9)

    if score < RELEVANCE_THRESHOLD:
        self.logger.debug(f"Discarded (score={score:.2f}): {data.get('title', '')[:80]}")
        return None

    data["is_india_relevant"] = True
    data["india_relevance_score"] = score
    data["india_keywords_found"] = keywords_found
    return data
```

### 3.4 Future Enhancement
- Replace keyword matching with a trained text classifier
- Add geolocation NLP using spaCy NER for location extraction
- Support Hindi-language content analysis

---

## 4. Classification Agent

> **Location**: `backend/app/agents/classification_agent.py`

### 4.1 Responsibility
- Classify each incident by **attack type**, **severity**, and **sector**
- Assign a `confidence_score` for the classification
- Uses rule-based approach for MVP, upgrades to DistilBERT in Phase 4

### 4.2 MVP: Rule-Based Classifier

```python
ATTACK_TYPE_KEYWORDS = {
    "ransomware": ["ransomware", "ransom", "encrypt files", "lockbit", "conti", "ryuk"],
    "phishing": ["phishing", "spear phishing", "credential harvest", "fake login"],
    "ddos": ["ddos", "denial of service", "traffic flood", "botnet attack"],
    "data_breach": ["data breach", "data leak", "records exposed", "personal data"],
    "apt_campaign": ["apt", "advanced persistent", "nation state", "espionage"],
    "defacement": ["defacement", "defaced", "website hacked"],
    "malware": ["malware", "trojan", "worm", "spyware", "backdoor", "rootkit"],
    "sql_injection": ["sql injection", "sqli"],
    "xss": ["cross-site scripting", "xss"],
    "supply_chain": ["supply chain", "solarwinds", "dependency confusion"],
    "zero_day": ["zero-day", "zero day", "0-day", "0day"],
}

SEVERITY_INDICATORS = {
    "critical": ["critical", "emergency", "immediate action", "actively exploited", "rce"],
    "high": ["high severity", "high risk", "significant", "major"],
    "medium": ["moderate", "medium", "potential risk"],
    "low": ["low risk", "minor", "informational"],
}

SECTOR_KEYWORDS = {
    "banking_finance": ["bank", "banking", "financial", "rbi", "upi", "npci", "sbi", "hdfc"],
    "healthcare": ["hospital", "healthcare", "aiims", "medical", "health"],
    "government": ["government", "gov.in", "nic", "ministry", "department"],
    "energy_power": ["power grid", "energy", "electricity", "oil", "gas"],
    "telecom": ["telecom", "bsnl", "airtel", "jio", "5g", "mobile network"],
    "defence": ["defence", "defense", "military", "army", "navy", "drdo"],
    "education": ["university", "college", "education", "school", "academic"],
    "it_ites": ["it company", "infosys", "tcs", "wipro", "software"],
}
```

### 4.3 Classification Logic

```python
async def process(self, data: dict) -> dict | None:
    text = f"{data.get('title', '')} {data.get('content', '')}".lower()

    # Classify attack type
    attack_type, attack_confidence = self._match_keywords(text, ATTACK_TYPE_KEYWORDS)
    data["attack_type"] = attack_type or "unknown"

    # Classify severity
    severity, _ = self._match_keywords(text, SEVERITY_INDICATORS)
    data["severity"] = severity or "info"

    # Classify sector
    sector, _ = self._match_keywords(text, SECTOR_KEYWORDS)
    data["sector_code"] = sector  # None if not matched

    data["confidence_score"] = attack_confidence
    return data

def _match_keywords(self, text: str, keyword_map: dict) -> tuple[str | None, float]:
    best_match = None
    best_score = 0.0
    for category, keywords in keyword_map.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits > 0:
            score = hits / len(keywords)
            if score > best_score:
                best_score = score
                best_match = category
    return best_match, min(best_score * 2, 1.0)  # Scale up for confidence
```

### 4.4 Phase 4: DistilBERT Upgrade

When Phase 4 (ML training) is completed:
1. Load fine-tuned model from `ml/models/`
2. Use HuggingFace `pipeline()` for inference
3. Replace `_match_keywords` with model prediction
4. Keep keyword-based as fallback when model confidence < 0.5

```python
# Future Phase 4 implementation
from transformers import pipeline

class MLClassificationAgent(ClassificationAgent):
    def __init__(self):
        super().__init__("ml_classification")
        self.classifier = pipeline(
            "text-classification",
            model="./ml/models/incident_classifier",
            top_k=3,
        )
```

---

## 5. Correlation Agent

> **Location**: `backend/app/agents/correlation_agent.py`

### 5.1 Responsibility
- Find **related incidents** already in the database
- Link incidents that describe the same event from different sources
- Identify campaign-level connections (same actor, same CVE)

### 5.2 Correlation Strategies

| Strategy | How it Works | Correlation Type |
|---|---|---|
| **URL Dedup** | Same `source_url` → skip (already exists) | — (prevent duplicates) |
| **Title Similarity** | Jaccard similarity on title tokens > 0.6 | `same_event` |
| **Entity Match** | Shared CVE IDs, threat actor names, or org names | `same_cve`, `same_actor` |
| **Time Window** | Incidents within 48 hours with same attack type + sector | `related_campaign` |

### 5.3 Algorithm

```python
async def process(self, data: dict) -> dict | None:
    # Step 1: Check deduplication (exact URL match)
    existing = await self._find_by_url(data["source_url"])
    if existing:
        self.logger.info(f"Duplicate skipped: {data['source_url']}")
        return None

    # Step 2: Find similar incidents in last 7 days
    recent_incidents = await self._get_recent_incidents(days=7)
    correlations = []

    for incident in recent_incidents:
        # Title similarity
        sim = self._jaccard_similarity(data["title"], incident.title)
        if sim > 0.6:
            correlations.append({
                "incident_id": str(incident.id),
                "similarity_score": sim,
                "correlation_type": "same_event",
            })
            continue

        # Entity match (CVEs, actors)
        shared_entities = self._find_shared_entities(data, incident)
        if shared_entities:
            correlations.append({
                "incident_id": str(incident.id),
                "similarity_score": 0.7,
                "correlation_type": shared_entities["type"],
            })

    data["correlations"] = correlations
    return data
```

### 5.4 Jaccard Similarity

```python
def _jaccard_similarity(self, text_a: str, text_b: str) -> float:
    """Compute Jaccard similarity between two text strings."""
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(intersection) / len(union)
```

---

## 6. Insight Agent

> **Location**: `backend/app/agents/insight_agent.py`

### 6.1 Responsibility
- Final stage before database insertion
- Extract named entities (NER) from the text
- Generate a processed summary/description
- **Persist** the incident and its entities to the database

### 6.2 NER Extraction (spaCy)

```python
import spacy

class InsightAgent(BaseAgent):
    def __init__(self):
        super().__init__("insight")
        self.nlp = spacy.load("en_core_web_sm")

    async def process(self, data: dict) -> dict | None:
        text = data.get("content", "")

        # Extract entities using spaCy
        doc = self.nlp(text[:10000])  # Limit text length for performance
        entities = []
        for ent in doc.ents:
            if ent.label_ in ("ORG", "GPE", "PERSON", "PRODUCT"):
                entities.append({
                    "name": ent.text,
                    "entity_type": self._map_spacy_label(ent.label_),
                })

        # Extract CVE IDs via regex
        import re
        cves = re.findall(r"CVE-\d{4}-\d{4,}", text)
        for cve in cves:
            entities.append({"name": cve, "entity_type": "cve_id"})

        # Extract IP addresses via regex
        ips = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text)
        for ip in ips:
            entities.append({"name": ip, "entity_type": "ip_address"})

        data["extracted_entities"] = entities

        # Generate summary (truncate content for description)
        data["description"] = self._generate_summary(data)

        # Persist to database
        await self._save_to_database(data)
        return data

    def _map_spacy_label(self, label: str) -> str:
        mapping = {
            "ORG": "organization",
            "GPE": "country",
            "PERSON": "threat_actor",
            "PRODUCT": "software",
        }
        return mapping.get(label, "other")

    def _generate_summary(self, data: dict) -> str:
        content = data.get("content", "")
        # Simple: first 500 chars as summary
        # Future: Use extractive summarization
        return content[:500].strip() + "..." if len(content) > 500 else content
```

### 6.3 Database Persistence

```python
async def _save_to_database(self, data: dict) -> None:
    """Save the fully processed incident to PostgreSQL."""
    # 1. Create Incident record
    # 2. Create/find Entity records
    # 3. Create IncidentEntity junction records
    # 4. Create Correlation records if any
    # (Implementation uses SQLAlchemy async session)
```

---

## 7. Agent Configuration Summary

| Agent | Input | Output | Can Discard? | DB Access |
|---|---|---|---|---|
| **Scraper** | Web pages | Raw articles → Redis | No | Read (sources) |
| **Relevance** | Raw article | Filtered + scored article | **Yes** (below threshold) | No |
| **Classification** | Filtered article | Classified article | No | No |
| **Correlation** | Classified article | Correlated article | **Yes** (duplicate) | Read (recent incidents) |
| **Insight** | Correlated article | Final incident record | No | **Write** (insert) |

---

## 8. Agent Scheduling

| Trigger | Frequency | What Runs |
|---|---|---|
| **Scraper cron** | Every 30 minutes | All active Scrapy spiders |
| **Queue consumer** | Continuous (event loop) | Orchestrator pipeline (polls Redis) |
| **Trend update** | Every 6 hours | Insight Agent batch recalculation |

### 8.1 Queue Consumer Pattern

```python
# backend/app/agents/orchestrator.py — consumer loop

async def consume_queue(self):
    """Continuously consume from Redis queue and process articles."""
    while True:
        raw = await self.redis.blpop("incident:raw", timeout=30)
        if raw:
            article = json.loads(raw[1])
            await self.process_article(article)
        # If no message, blpop will wait up to timeout then loop
```

---

## 9. Error Handling & Resilience

| Scenario | Handling |
|---|---|
| Spider HTTP error (4xx/5xx) | Scrapy auto-retries (3 times), then logs and skips |
| Redis connection failure | Agent retries with exponential backoff, alerts after 5 failures |
| NLP model load failure | Agent starts without NER, logs warning, classifies without entities |
| Database insert failure | Logs full error, pushes article back to Redis for retry |
| Duplicate article | Correlation Agent detects and discards (not an error) |
| Unexpected exception in any agent | Caught by `BaseAgent.run_batch()`, logged, item skipped |
