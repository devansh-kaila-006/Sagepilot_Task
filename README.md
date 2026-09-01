# Order Supervisor AI (POC)

A long-running AI supervisor that manages the lifecycle of orders. 
Built with FastAPI, LangGraph, PostgreSQL, and Next.js.

## Prerequisites

- Python 3.10+
- Node.js 18+
- Docker (optional, but no longer required as we use Supabase)
- OpenAI API Key

### 1. Database (Supabase)

Since this POC uses Supabase:
1. Create a project at [Supabase](https://supabase.com/).
2. Copy the **Transaction Connection String** from your Database settings.
3. Copy the **Project URL** and **Anon Key** from your API settings (if you want real-time UI updates).

### 2. Backend (FastAPI + LangGraph)

Create a `.env` file in the `backend/` directory:
```
OPENAI_API_KEY=your-api-key-here
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-region.pooler.supabase.com:6543/postgres
```

Install dependencies and run:
```bash
cd backend
python -m venv venv
# Windows
.\venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt # (or manually install the packages listed in the code)
uvicorn app.main:app --reload
```

### 3. Frontend (Next.js)

Create a `.env.local` file in the `frontend/` directory for real-time UI:
```
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

Install dependencies and run:
```bash
cd frontend
npm install
npm run dev
```

The UI will be available at [http://localhost:3000](http://localhost:3000).

## Usage Guide (Walkthrough)

1. Open the UI at `http://localhost:3000`.
2. Click **"+ Create Demo"** to create a supervisor template.
3. Click **"Start New Run"** on the supervisor card.
4. The run will appear in the "Active Runs" column. Click it to enter the Run Details page.
5. In the Run Details view, you will see a `run_started` event and the Agent's response.
6. Use the **Inject Event** dropdown to simulate system events (e.g. `payment_failed`).
7. Watch the Activity Log populate as the Agent wakes up, reasons, executes tools (like `message_customer`), and goes back to sleep.
8. Use the **Add Instruction** box to steer the agent mid-flight (e.g., "Do not message the customer for the next 24 hours").
9. Click the **Terminate** button in the top right to end the run gracefully.

## Architecture

See `architecture_note.md` for detailed design decisions.
