# Architecture & Design Note

## Overview

The Order Supervisor AI is designed to observe an order's lifecycle, evaluate incoming events asynchronously, take required actions, and sleep to conserve compute until necessary.

## Core Architectural Decisions

### 1. Orchestration: Database Polling + LangGraph (Instead of Temporal)

**Why not Temporal?**
Temporal is the gold standard for durable, long-running workflow orchestration. However, setting up a Temporal cluster for a Proof of Concept (POC) adds significant overhead and infrastructure requirements.

**The Alternative Choice:**
We opted for a **Database-Backed State Machine** combined with a **FastAPI Background Poller** and **LangGraph**.
- **LangGraph** naturally handles cyclic agent workflows, memory persistence, and tool execution.
- **FastAPI Background Tasks & APScheduler** act as the workflow runner. When an agent calls `sleep()`, the runtime saves `next_wake_at` to the database and exits. The poller constantly checks the DB for runs that have passed their wake time, and re-triggers them.
- This provides robust long-running capabilities, sleep/wake, and event interruption natively without complex middleware.

### 2. State & Memory Management

- **The Activity Log Ledger:** Instead of maintaining disparate tables for events, actions, and messages, a single append-only `activities` table acts as an immutable ledger for the run.
- **Context Compaction:** Upon waking up, the agent reads the most recent `N` items from the `activities` table. This creates an automatic rolling context window that prevents the LLM context from blowing up over a very long-running order (e.g., spanning months).

### 3. Wake / Sleep Classifier

- For simplicity in the POC, any incoming injected event instantly clears the `next_wake_at` timer and awakens the main agent loop.
- In a production environment, a fast heuristic or lightweight LLM (e.g., GPT-4o-mini) would act as a "Bouncer" or Classifier, evaluating `Event + Current State` to decide: "Does this warrant waking the expensive reasoning agent, or do we ignore it?"

### 4. API Design

The API uses RESTful endpoints that map directly to the Next.js UI capabilities:
- `POST /runs/{id}/events` (Injects an event and wakes agent)
- `POST /runs/{id}/instructions` (Injects human steering and wakes agent)
- `POST /runs/{id}/terminate` (Hard stop of the workflow)

## Tradeoffs

- **Polling vs. Event-Driven Messaging:** Polling the DB every 10 seconds is acceptable for a POC but won't scale elegantly to millions of concurrent runs. A real production system would use AWS SQS / RabbitMQ with Delayed Messages or Temporal.
- **Agent Framework:** Using LangGraph is slightly heavier than a raw OpenAI API loop, but it provides built-in tool bindings and a state graph that makes future expansions (like adding a specialized Researcher sub-agent) trivial.
