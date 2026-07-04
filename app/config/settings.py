from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    database_url: str = "postgresql://postgres:postgres@localhost:5432/guardian_db"

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "sf.inbound.events"
    kafka_group_id: str = "guardian-agent-py-group"

    salesforce_mock_mode: bool = True
    slack_enabled: bool = False

    price_conflict_threshold: float = 100.0
    duplicate_window_minutes: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
