# Order Supervisor AI (POC)

An autonomous AI agent designed to oversee the lifecycle of e-commerce orders. Built with FastAPI (backend), Next.js (frontend), Supabase (PostgreSQL DB), and LangGraph (agent orchestration).

## Architecture

This project utilizes a two-tier LLM architecture powered by Google Gemini:
1. **Classifier Model (`gemini-3.1-flash-lite`)**: A fast, low-cost model used to route incoming events. It decides if an event is trivial ("SLEEP") or requires business logic ("WAKE"), preserving the main agent's quota.
2. **Main Agent (`gemini-3.6-flash`)**: The core reasoning engine. Wakes up when necessary to assess context, invoke tools (messaging teams, logging notes), and decide when to sleep or complete the run.

### Concurrency & State Management
- **Per-Run Isolation**: Each order lifecycle (Run) operates completely independently with an isolated `run_id` lock to prevent state bleed during event bursts.
- **Terminate/Fallback Design**: Mid-cycle completions correctly abort trailing actions via database-level termination guards. A fallback cron job (Poller) ensures sleeping runs wake up safely.
- **Context Compaction**: As the event log grows, older events are dynamically summarized and stored in `run.state["compacted_summary"]` to prevent LLM context bloat and hallucination on long-running orders.

## Setup Instructions

### 1. Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate # Mac/Linux
pip install -r requirements.txt
```

### 2. Environment Variables
Copy `.env.example` to `.env` in the `backend/` directory:
```
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres
GEMINI_API_KEY=your_gemini_api_key
AGENT_MODEL=gemini-3.6-flash
CLASSIFIER_MODEL=gemini-3.1-flash-lite
```

### 3. Run the Backend
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Run the Frontend
```bash
cd frontend
npm install
npm run dev
```

Navigate to `http://localhost:3000` to interact with the dashboard.
