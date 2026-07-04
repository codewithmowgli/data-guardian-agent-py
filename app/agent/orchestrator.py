import json
import logging
import threading
from kafka import KafkaConsumer

from app.agent.guardian_agent import get_agent
from app.config.settings import settings

logger = logging.getLogger(__name__)


def process_event(event_json: str) -> str:
    logger.info("═══════════════════════════════════════════")
    logger.info("[ORCHESTRATOR] Processing Guardian Event...")

    try:
        event = json.loads(event_json)
        logger.info(
            f"[ORCHESTRATOR] Source: {event.get('source_system')} | "
            f"Entity: {event.get('entity_type')} | "
            f"ID: {event.get('entity_id')} | "
            f"Action: {event.get('action')}"
        )

        agent = get_agent()
        result = agent.invoke({
            "input": f"Process this data event and make a guardian decision: {event_json}"
        })

        output = result.get("output", "No output from agent")
        logger.info(f"[ORCHESTRATOR] ✅ Agent decision complete: {output}")
        logger.info("═══════════════════════════════════════════")
        return output

    except Exception as e:
        logger.error(f"[ORCHESTRATOR] ❌ Failed to process event: {e}", exc_info=True)
        return json.dumps({"error": f"Failed to process event: {str(e)}"})


def start_kafka_consumer():
    def consume():
        logger.info(f"[KAFKA] Starting consumer on topic: {settings.kafka_topic}")
        consumer = KafkaConsumer(
            settings.kafka_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_group_id,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: m.decode("utf-8"),
        )
        for message in consumer:
            logger.info(f"[KAFKA] Received event: {message.value[:100]}...")
            process_event(message.value)

    thread = threading.Thread(target=consume, daemon=True)
    thread.start()
    logger.info("[KAFKA] Consumer thread started.")
