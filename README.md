# Indian Cyber Incident Intelligence Platform

An end-to-end automated platform that scrapes, processes, correlates, and visualizes cybersecurity incidents with a specific focus on the Indian cyberspace.

## Features
- **Automated Scraping:** Crawls CERT-In and The Hacker News.
- **Intelligent Pipeline:** Four custom agents that filter relevance, classify attacks, correlate duplicates, and extract entities (CVEs, IPs).
- **FastAPI Backend:** Fully async RESTful API serving incident data and RSS/JSON feeds.
- **Streamlit Dashboard:** Real-time visualization and filtering of incidents.
- **Docker Ready:** Spin up the entire stack with a single command.

## Tech Stack
- **Database:** PostgreSQL (with psycopg)
- **Queue/Cache:** Redis
- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic
- **Scraper:** Scrapy
- **Frontend:** Streamlit + Plotly
- **ML/NLP:** spaCy, HuggingFace Transformers (scaffolding)

## Getting Started

### Using Docker
1. Clone the repository.
2. Ensure you have Docker and Docker Compose installed.
3. Run `docker-compose up --build`.
4. Access the dashboard at `http://localhost:8501`.
5. Access the API docs at `http://localhost:8000/docs`.

### Running Locally (Without Docker)
1. Install PostgreSQL and Redis locally.
2. Create a virtual environment and install dependencies.
3. Set up `.env` based on `.env.example`.
4. Run migrations: `cd backend && alembic upgrade head`.
5. Start FastAPI: `cd backend && uvicorn app.main:app --reload`.
6. Start Orchestrator: `cd backend && python -c "import asyncio; from app.agents.orchestrator import PipelineOrchestrator; asyncio.run(PipelineOrchestrator().consume_queue())"`.
7. Start Streamlit: `cd dashboard && streamlit run app.py`.
