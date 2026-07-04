# Data Guardian Agent (Python)

Python implementation of the Lucid Data Guardian Agent using **FastAPI + LangChain + Ollama**.

> Java version: [lucid-data-guardian-agent](https://github.com/codewithmowgli/lucid-data-guardian-agent)

## Stack
- Python 3.12
- FastAPI + Uvicorn
- LangChain + langchain-ollama
- Apache Kafka (kafka-python)
- PostgreSQL + SQLAlchemy
- Pytest

## Pipeline
```
INGEST → VALIDATE → CONFLICT_CHECK → DECISION (AI) → AUDIT → NOTIFY → SYNC
```

## Run Locally

### Prerequisites
- Python 3.12
- Docker Desktop
- Ollama: `ollama pull llama3.1`

### Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Start infrastructure
```bash
docker-compose up -d
```

### Start the agent
```bash
uvicorn app.main:app --reload
```

### API Docs
http://localhost:8000/docs

### Run tests
```bash
pytest tests/ -v
```

### Test with a sample event
```bash
curl -X POST http://localhost:8000/api/v1/guardian/process \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "EVT-001",
    "source_system": "PARTNER_PORTAL",
    "entity_type": "LEAD",
    "entity_id": "LEAD-NEW-001",
    "action": "UPSERT",
    "payload_json": "{\"entityId\":\"LEAD-NEW-001\",\"email\":\"john@example.com\",\"firstName\":\"John\",\"lastName\":\"Smith\",\"vehicleInterest\":\"Lucid Air Grand Touring\",\"timestamp\":\"2025-06-01T10:00:00Z\"}"
  }'
```

## Author
Dilip Agnihotri — github.com/codewithmowgli

