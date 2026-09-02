# Design Note: What I'd Build Next (With More Time)

- **True Event-Driven Infrastructure:** Migrate the database polling mechanism (APScheduler) to a dedicated event queue (like RabbitMQ, Apache Kafka, or AWS SQS) or a durable execution framework like Temporal for hyper-scalability.
- **Human-in-the-Loop Checkpoints:** Implement a LangGraph interrupt node that pauses execution and pings a Slack channel or internal dashboard when the agent encounters an edge case it is not confident handling.
- **Comprehensive Analytics:** Emit telemetry for agent reasoning latency, cost per run, and token usage to a centralized dashboard (e.g., Datadog or Grafana) to monitor LLM overhead in production.
- **Agentic Testing Suite:** Build a mock order environment to run automated E2E tests against the agent, ensuring business rules aren't broken when the prompt or underlying LLM model is upgraded.
