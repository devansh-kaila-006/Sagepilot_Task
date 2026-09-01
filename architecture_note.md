# Architecture & Design Note

## Overview

The Order Supervisor AI is designed to observe an order's lifecycle, evaluate incoming events asynchronously, take required actions, and sleep to conserve compute until necessary. It is designed as a scalable, fault-tolerant, and secure autonomous agent system.

## Core Architectural Decisions

### 1. Orchestration: Database Polling + LangGraph

**Why not Temporal?**
Temporal is the gold standard for durable, long-running workflow orchestration. However, setting up a Temporal cluster for a Proof of Concept (POC) adds significant overhead and infrastructure requirements.

**The Alternative Choice:**
We opted for a **Database-Backed State Machine** combined with a **FastAPI Background Poller** and **LangGraph**.
- **LangGraph** naturally handles cyclic agent workflows, memory persistence, and tool execution.
- **FastAPI Background Tasks & APScheduler** act as the workflow runner. When an agent calls `sleep()`, the runtime saves `next_wake_at` to the database and exits. The poller constantly checks the DB for runs that have passed their wake time, and re-triggers them.
- **Concurrency & Leasing:** Multi-worker deployments (e.g. Render, AWS) are handled gracefully via a Row-Level DB lease (`UPDATE ... SET status='processing'`). This guarantees isolated execution.
- **Fault-Tolerance:** A stale processing sweep ensures that if a worker dies mid-execution, the orphaned run is cleanly unlocked and recovered by the cluster.

### 2. State & Memory Management

- **The Activity Log Ledger:** Instead of maintaining disparate tables for events, actions, and messages, a single append-only `activities` table acts as an immutable ledger for the run.
- **Context Compaction:** As the log grows beyond 20 events, the system automatically uses a lightweight LLM to summarize older events. The compaction state uses absolute IDs (`last_compacted_id`) rather than array indices, ensuring perfect resilience against drift or mid-cycle injected events. The agent maintains infinite-horizon context without blowing out the token limit.

### 3. Wake / Sleep Classifier (Two-Tier LLM Architecture)

- **Classifier Bouncer (`gemini-3.1-flash-lite`)**: A rapid, cheap model evaluates every incoming event against the run's current context. It acts as a gatekeeper, determining if the event warrants waking the expensive reasoning agent or if it can be safely ignored ("SLEEP").
- **Main Agent (`gemini-3.6-flash`)**: The core reasoning engine. Only powers up when business logic dictates action is required, heavily optimizing API costs and latency.

### 4. API & Security Design

- **REST & WebSockets**: The API uses RESTful endpoints mapped directly to Next.js capabilities, alongside a live WebSocket stream for realtime terminal output.
- **Strict Authentication**: All backend routes and WebSocket connections are protected by Supabase JWT validation. 
- **Row Level Security (RLS)**: The database itself is locked down against malicious anonymous access via explicit `Deny` policies, enforcing that all data modifications travel exclusively through the authenticated FastAPI layer.

## Tradeoffs

- **Polling vs. Event-Driven Messaging:** Polling the DB every 10 seconds is acceptable for early production but won't scale elegantly to millions of concurrent runs. A real hyper-scale system would use AWS SQS / RabbitMQ with Delayed Messages or Temporal.
- **Agent Framework:** Using LangGraph is slightly heavier than a raw OpenAI/Gemini API loop, but it provides built-in tool bindings and a state graph that makes future expansions (like adding a specialized Researcher sub-agent) trivial.
