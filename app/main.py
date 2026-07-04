import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.guardian_router import router
from app.models.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Lucid Data Guardian Agent (Python)")
    init_db()
    logger.info("✅ Database initialized")

    # Start Kafka consumer in background (comment out if Kafka not running)
    # from app.agent.orchestrator import start_kafka_consumer
    # start_kafka_consumer()

    yield
    logger.info("🛑 Shutting down Data Guardian Agent")


app = FastAPI(
    title="Lucid Data Guardian Agent",
    description="Agentic AI system for Salesforce data integrity across Lucid Motors' multi-system ecosystem",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/", tags=["Health"])
def root():
    return {
        "name": "Lucid Data Guardian Agent",
        "version": "1.0.0",
        "status": "running",
        "stack": "Python · FastAPI · LangChain · Ollama · PostgreSQL · Kafka"
    }
