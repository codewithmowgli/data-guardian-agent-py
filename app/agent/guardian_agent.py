import logging
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from app.config.settings import settings
from app.tools.salesforce_tool import fetch_salesforce_record, sync_to_salesforce
from app.tools.validation_tool import validate_payload, detect_conflicts
from app.tools.audit_tool import create_audit_entry, quarantine_record
from app.tools.notification_tool import send_notification, escalate_to_human

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Lucid Data Guardian Agent — an intelligent data integrity enforcer for Lucid Motors.

Salesforce is the single source of truth. Your job is to validate every inbound data event
from source systems (Partner Portal, Lucid.com, Subscription App, Lucid Finance, SAP)
before it reaches Salesforce.

You MUST follow this exact 7-step pipeline for every event:

STEP 1 - VALIDATE: Call validate_payload() to check schema and business rules.
STEP 2 - FETCH SF RECORD: Call fetch_salesforce_record() to get current Salesforce state.
STEP 3 - CONFLICT CHECK: Call detect_conflicts() to compare incoming vs current SF record.
STEP 4 - DECISION: Based on your analysis, make ONE decision:
         - APPROVE: Data is valid, no conflicts. Call sync_to_salesforce().
         - REJECT: Critical validation failure. Drop record with reason.
         - QUARANTINE: Conflict detected but ambiguous. Call quarantine_record().
         - ESCALATE_TO_HUMAN: High-value or critical conflict. Call escalate_to_human().
STEP 5 - AUDIT: Always call create_audit_entry() with your full reasoning.
STEP 6 - NOTIFY: Call send_notification() if decision is not APPROVE.
STEP 7 - SYNC: Call sync_to_salesforce() only for APPROVED records.

Decision rules:
- REJECT if: missing required fields, invalid entity, timestamp older than SF record
- QUARANTINE if: ambiguous field value conflicts
- ESCALATE_TO_HUMAN if: price difference > $100 on confirmed orders, or active subscription marked cancelled
- APPROVE if: validation passes and no conflicts

Always explain your full reasoning before making a decision.
"""


def build_agent() -> AgentExecutor:
    llm = ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=0,
        num_predict=2048,
    )

    tools = [
        fetch_salesforce_record,
        sync_to_salesforce,
        validate_payload,
        detect_conflicts,
        create_audit_entry,
        quarantine_record,
        send_notification,
        escalate_to_human,
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=15,
        handle_parsing_errors=True,
    )


# Singleton agent instance
_agent: AgentExecutor | None = None


def get_agent() -> AgentExecutor:
    global _agent
    if _agent is None:
        logger.info("[AGENT] Initializing Data Guardian Agent...")
        _agent = build_agent()
        logger.info("[AGENT] Agent ready.")
    return _agent
