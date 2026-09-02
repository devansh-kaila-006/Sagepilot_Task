# Architecture & Design Note

## Overview

The Order Supervisor AI is designed to oversee a single order from creation until completion. It observes the order's lifecycle, evaluates incoming events asynchronously, executes required business actions, and sleeps to conserve compute until necessary. This architecture is designed to be a scalable, fault-tolerant, and reliable autonomous agent system.

This document outlines the core design decisions, orchestration choices, and tradeoff reasoning in alignment with the project requirements.

---

## 1. Orchestration Choices and Justification

**The Requirement:** The system must support long-running execution, event-driven wake-up, scheduled wake-up, interruption/termination, and reliable state transitions.

**The Choice: Database-Backed State Machine + Cron/Scheduler (APScheduler) + LangGraph**

**Justification & Tradeoff Reasoning:**
While dedicated workflow engines like **Temporal** are the industry gold standard for durable, long-running execution, setting up a cluster for a Proof of Concept adds significant infrastructure overhead. The prompt explicitly allowed *database state plus cron or scheduler* as a valid alternative, which is precisely the orchestration model chosen here.

- **FastAPI Background Tasks & APScheduler:** Act as the workflow runner. When an agent decides to sleep, it calls a tool that saves a 
ext_wake_at timestamp to the database and cleanly exits the process. A background poller constantly sweeps the DB for runs that have passed their wake time, triggering execution.
- **Concurrency & Leasing:** Multi-worker deployments are handled gracefully via a Row-Level database lease (UPDATE ... SET status='processing' WHERE status='sleeping'). This guarantees isolated, mutually-exclusive execution.
- **Crash Recovery:** A stale processing sweep ensures that if a worker node dies mid-execution, the orphaned run is cleanly unlocked (status='processing' for >X minutes) and recovered by the cluster on the next sweep.

*Tradeoff:* Polling a database every 10 seconds is perfectly acceptable and highly resilient for early production, but it incurs a fixed IO cost and won't scale elegantly to tens of millions of concurrent runs. A hyper-scale system would transition this scheduling layer to AWS SQS/RabbitMQ with Delayed Messages or Temporal, but the underlying database schema and agent logic would remain identical.

## 2. Agent Orchestration & Long-Running Run Modeling

**The Choice: LangGraph**

**Justification:**
Instead of a raw while loop calling the OpenAI/Gemini API, **LangGraph** was chosen to model the agent runtime as a cyclic graph. 
- It naturally handles cyclic agent workflows, structured tool bindings (e.g., 	ool_message_fulfillment_team), and memory persistence.
- It makes future expansions (like adding specialized Supervisor sub-agents or human-in-the-loop checkpoints) trivial to implement via graph nodes.

*Tradeoff:* LangGraph introduces a slight learning curve and overhead compared to raw API calls, but the robust structured outputs and state management capabilities far outweigh the complexity for a production-grade agent.

## 3. Event Handling: Two-Tier Wake/Sleep Classifier

To prevent the expensive main reasoning agent from waking up for trivial or duplicate events, a **Two-Tier LLM Architecture** is employed:

- **Classifier Bouncer (gemini-3.1-flash-lite)**: A rapid, cheap model evaluates every incoming event against the run's current context. It acts as a gatekeeper, determining if the event warrants waking the main agent or if it can be safely ignored (returning "SLEEP").
- **Main Agent (gemini-3.6-flash)**: The core reasoning engine. Only powers up when the classifier deems an event important, heavily optimizing API costs and latency.

## 4. State and Memory Design

Maintaining context over a long-running order (which could span weeks) requires careful token management.

- **The Activity Log Ledger:** Instead of maintaining disparate tables for events, actions, and messages, a single append-only ctivities table acts as an immutable ledger for the run.
- **Context Compaction Strategy:** As the activity log grows beyond a set threshold (e.g., 20 events), the system automatically triggers a lightweight LLM task to summarize older events. The compaction state uses absolute database IDs (last_compacted_id) rather than array indices, ensuring perfect resilience against drift or mid-cycle injected events. The agent maintains an infinite-horizon context without blowing out the token limit.

## 5. Security and Access

- **Row Level Security (RLS)**: The database is locked down with explicit Postgres RLS policies, enforcing that frontend clients can read real-time updates via Supabase WebSockets, but all data modifications must travel exclusively through the authenticated FastAPI layer.

## 6. What I'd Build Next (With More Time)

- **True Event-Driven Infrastructure:** Migrate the database polling mechanism (APScheduler) to a dedicated event queue (like RabbitMQ, Apache Kafka, or AWS SQS) or a durable execution framework like Temporal for hyper-scalability.
- **Human-in-the-Loop Checkpoints:** Implement a LangGraph interrupt node that pauses execution and pings a Slack channel or internal dashboard when the agent encounters an edge case it is not confident handling.
- **Comprehensive Analytics:** Emit telemetry for agent reasoning latency, cost per run, and token usage to a centralized dashboard (e.g., Datadog or Grafana) to monitor LLM overhead in production.
- **Agentic Testing Suite:** Build a mock order environment to run automated E2E tests against the agent, ensuring business rules aren't broken when the prompt or underlying LLM model is upgraded.
