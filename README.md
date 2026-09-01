# Order Supervisor AI (Production-Ready)

An autonomous AI agent designed to oversee the lifecycle of e-commerce orders. Built with FastAPI (backend), Next.js (frontend), Supabase (PostgreSQL DB), and LangGraph (agent orchestration).

## Architecture

This project utilizes a two-tier LLM architecture powered by Google Gemini:
1. **Classifier Model (`gemini-3.1-flash-lite`)**: A fast, low-cost model used to route incoming events. It decides if an event is trivial ("SLEEP") or requires business logic ("WAKE"), preserving the main agent's quota.
2. **Main Agent (`gemini-3.6-flash`)**: The core reasoning engine. Wakes up when necessary to assess context, invoke tools (messaging teams, logging notes), and decide when to sleep or complete the run.

### Reliability & Concurrency
- **Per-Run DB Leasing**: Multi-worker deployments are supported out-of-the-box via Row Level database leases.
- **Context Compaction**: As the event log grows, older events are dynamically summarized to prevent LLM context bloat and hallucination on long-running orders. This compaction tracking uses absolute IDs to perfectly handle race conditions and injections.
- **Fault Tolerance**: A background poller actively recovers any orphaned processes, ensuring maximum uptime.

### Security
- **Strict JWT Verification**: All backend routes and WebSocket streams explicitly demand cryptographically signed JWT tokens.
- **Row Level Security**: The database tables are locked down to `authenticated` and `service_role` traffic exclusively.

## Quick Start (Local Development)

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
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_supabase_key

GEMINI_API_KEY=your_gemini_api_key

# Optional overrides
# AGENT_MODEL=gemini-3.6-flash
# CLASSIFIER_MODEL=gemini-3.1-flash-lite
```

### 3. Run the Stack
**Backend**:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
**Frontend**:
```bash
cd frontend
npm install
npm run dev
```

Navigate to `http://localhost:3000` to interact with the dashboard.

## Cloud Deployment

### Backend (Render)
This repository includes a `render.yaml` Blueprint file and a `Dockerfile`.
1. Commit your code and connect your GitHub repository to [Render](https://render.com).
2. Create a new **Blueprint**. Render will automatically detect the Web Service and configure it for the free tier.
3. Supply your Environment Variables in the Render Dashboard when prompted.

### Frontend (Vercel)
1. Go to [Vercel](https://vercel.com) and import your GitHub repository.
2. Set the Root Directory to `frontend`.
3. Add your `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and set `NEXT_PUBLIC_API_URL` to your live Render backend URL.
4. Deploy!
