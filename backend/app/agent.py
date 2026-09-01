import os
import json
import time
import logging
import asyncio
from typing import TypedDict, Annotated, Sequence, Any, Dict, List
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from .core.database import async_session
from .models import domain as models

logger = logging.getLogger(__name__)

# Classifier uses the lite model (trivial WAKE/SLEEP task, separate quota bucket);
# agent keeps the flagship flash model for reliable tool-calling. Override via .env.
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-3.6-flash")
CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "gemini-3.1-flash-lite")

run_locks = {}

def get_run_lock(run_id: str):
    if run_id not in run_locks:
        run_locks[run_id] = asyncio.Lock()
    return run_locks[run_id]

# --- State Definition ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    run_id: str
    order_id: str
    supervisor_instruction: str
    recent_activities: str
    next_wake_at: str | None
    completed: bool
    wake_decision: str | None

# --- Tools Definition (Simulated actions) ---
# We simulate these by returning a string that the agent will see, 
# but the real effect is creating an Activity in the DB.
async def _record_action(run_id: str, action_name: str, payload: dict):
    async with async_session() as db:
        result = await db.execute(select(models.Run).where(models.Run.id == run_id))
        run = result.scalars().first()
        if run and run.status in ["completed", "terminated"]:
            logger.warning(f"Run {run_id} is already {run.status}. Aborting action {action_name}.")
            return False
            
        activity = models.Activity(
            run_id=run_id,
            type="action",
            payload={"action": action_name, **payload}
        )
        db.add(activity)
        await db.commit()
        return True

async def message_fulfillment_team(run_id: str, message: str):
    if not await _record_action(run_id, "message_fulfillment_team", {"message": message}):
        return "Run is completed/terminated. Action aborted."
    return f"Sent to fulfillment: {message}"

async def message_payments_team(run_id: str, message: str):
    if not await _record_action(run_id, "message_payments_team", {"message": message}):
        return "Run is completed/terminated. Action aborted."
    return f"Sent to payments: {message}"

async def message_logistics_team(run_id: str, message: str):
    if not await _record_action(run_id, "message_logistics_team", {"message": message}):
        return "Run is completed/terminated. Action aborted."
    return f"Sent to logistics: {message}"

async def message_customer(run_id: str, message: str):
    if not await _record_action(run_id, "message_customer", {"message": message}):
        return "Run is completed/terminated. Action aborted."
    return f"Sent to customer: {message}"

async def create_internal_note(run_id: str, note: str):
    if not await _record_action(run_id, "create_internal_note", {"note": note}):
        return "Run is completed/terminated. Action aborted."
    return f"Created note: {note}"

async def sleep_until(run_id: str, hours: float):
    try:
        hours = max(0.01, min(720.0, float(hours)))
    except (ValueError, TypeError):
        hours = 24.0
    wake_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=hours)
    async with async_session() as db:
        result = await db.execute(select(models.Run).where(models.Run.id == run_id))
        run = result.scalars().first()
        
        if run and run.status in ["completed", "terminated"]:
            logger.warning(f"Run {run_id} is already {run.status}. Aborting sleep_until.")
            return f"Run is already {run.status}, cannot sleep."

        if run:
            run.next_wake_at = wake_time
            run.status = "sleeping"
            await db.commit()
            
        activity = models.Activity(
            run_id=run_id,
            type="sleep",
            payload={"duration_hours": hours, "wake_time": wake_time.isoformat()}
        )
        db.add(activity)
        await db.commit()
    return f"Sleeping for {hours} hours (until {wake_time.isoformat()})."

# LangChain Tool Wrappers
from langchain_core.tools import tool

@tool
def tool_message_fulfillment_team(message: str) -> str:
    """Send a message to the fulfillment team regarding the order."""
    # Note: State injection or context is tricky in pure @tool, so we will handle the DB write 
    # in a wrapper node or by passing run_id via context. 
    # For simplicity in this POC, we'll let the node executing the tool handle the DB write.
    return f"Fulfillment team messaged: {message}"

@tool
def tool_message_payments_team(message: str) -> str:
    """Send a message to the payments team regarding the order."""
    return f"Payments team messaged: {message}"

@tool
def tool_message_logistics_team(message: str) -> str:
    """Send a message to the logistics team regarding the order."""
    return f"Logistics team messaged: {message}"

@tool
def tool_message_customer(message: str) -> str:
    """Send a message to the customer regarding the order."""
    return f"Customer messaged: {message}"

@tool
def tool_create_internal_note(note: str) -> str:
    """Create an internal note for the order."""
    return f"Internal note created: {note}"

@tool
def tool_sleep(hours: float) -> str:
    """Go to sleep for a given number of hours. Use this when waiting for an update."""
    return f"Sleeping for {hours} hours"

@tool
def tool_complete_run(summary: str) -> str:
    """Mark the order run as completed and provide a final summary."""
    return f"Run completed: {summary}"

tools = [
    tool_message_fulfillment_team,
    tool_message_payments_team,
    tool_message_logistics_team,
    tool_message_customer,
    tool_create_internal_note,
    tool_sleep,
    tool_complete_run
]

# --- Nodes ---
async def classifier_node(state: AgentState):
    """Lightweight step to decide if the event is important enough to wake the main agent."""
    recent_activities_list = state['recent_activities'].strip().split("\n")
    if recent_activities_list and "INSTRUCTION:" in recent_activities_list[-1]:
        return {"wake_decision": "WAKE"}

    llm = ChatGoogleGenerativeAI(model=CLASSIFIER_MODEL, temperature=0)
    _t0 = time.perf_counter()
    sys_msg = SystemMessage(content=f"""
You are an event router for an Order Supervisor.
Recent Activities:
{state['recent_activities']}

Look at the last event. If it is trivial and requires no action, output "SLEEP".
If it might require business logic, communication, or state updates, output "WAKE".
Only output "WAKE" or "SLEEP".
""")
    response = await llm.ainvoke([sys_msg] + state["messages"])
    logger.info(f"[timing] classifier ({CLASSIFIER_MODEL}) call took {time.perf_counter() - _t0:.2f}s")
    content = response.content
    if isinstance(content, list):
        content = " ".join([b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"])
    decision = content.strip().upper()
    return {"wake_decision": decision}

async def agent_node(state: AgentState):
    llm = ChatGoogleGenerativeAI(model=AGENT_MODEL, temperature=0)
    llm_with_tools = llm.bind_tools(tools)
    
    sys_msg = SystemMessage(content=f"""
You are an Order Supervisor AI. Your job is to oversee a single order lifecycle.
Order ID: {state['order_id']}

Supervisor Instructions:
{state['supervisor_instruction']}

Recent Activities (Context):
{state['recent_activities']}

Analyze the recent activities. Decide if you need to take action.
If action is needed, use the available tools to message teams, create notes, or communicate with the customer.
Once you have handled the current situation, you MUST either:
1. Call `tool_sleep(hours)` to wait for the next update.
2. Call `tool_complete_run(summary)` if the order has reached a terminal state (e.g. delivered, refunded) and no further action will ever be needed.
Do NOT just return text without calling sleep or complete when you are done with the current batch of events.
""")
    
    messages = [sys_msg] + state["messages"]
    _t0 = time.perf_counter()
    response = await llm_with_tools.ainvoke(messages)
    usage = getattr(response, "usage_metadata", None)
    logger.info(f"[timing] agent ({AGENT_MODEL}) call took {time.perf_counter() - _t0:.2f}s"
                + (f" (in={usage['input_tokens']} out={usage['output_tokens']} tokens)" if usage else ""))
    return {"messages": [response]}

async def tool_executor_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    next_wake_at = state.get("next_wake_at")
    completed = state.get("completed", False)
    
    tool_msgs = []
    
    for tool_call in last_message.tool_calls:
        action_name = tool_call["name"]
        args = tool_call["args"]
        call_id = tool_call["id"]
        
        # Execute side effects
        if action_name == "tool_sleep":
            hours = args.get("hours", 24)
            msg = await sleep_until(state["run_id"], hours)
            next_wake_at = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=hours)).isoformat()
        elif action_name == "tool_complete_run":
            summary = args.get("summary", "")
            async with async_session() as db:
                result = await db.execute(select(models.Run).where(models.Run.id == state["run_id"]))
                run = result.scalars().first()
                if run and run.status in ["completed", "terminated"]:
                    logger.warning(f"Run {state['run_id']} is already {run.status}. Ignoring redundant complete.")
                elif run:
                    run.status = "completed"
                    run.next_wake_at = None
                    await db.commit()
                    
                activity = models.Activity(run_id=state["run_id"], type="complete", payload={"summary": summary})
                db.add(activity)
                await db.commit()
            msg = f"Run marked as completed. Summary: {summary}"
            completed = True
        else:
            # Dispatch to our internal handlers to record to DB
            if action_name == "tool_message_fulfillment_team":
                msg = await message_fulfillment_team(state["run_id"], args.get("message", ""))
            elif action_name == "tool_message_payments_team":
                msg = await message_payments_team(state["run_id"], args.get("message", ""))
            elif action_name == "tool_message_logistics_team":
                msg = await message_logistics_team(state["run_id"], args.get("message", ""))
            elif action_name == "tool_message_customer":
                msg = await message_customer(state["run_id"], args.get("message", ""))
            elif action_name == "tool_create_internal_note":
                msg = await create_internal_note(state["run_id"], args.get("note", ""))
            else:
                msg = f"Unknown tool: {action_name}"

        tool_msgs.append({
            "role": "tool",
            "name": action_name,
            "tool_call_id": call_id,
            "content": msg
        })
        
    return {
        "messages": tool_msgs,
        "next_wake_at": next_wake_at,
        "completed": completed
    }

def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return "end"
        
    # If the last tool was sleep or complete, we stop the graph loop
    for tc in last_message.tool_calls:
        if tc["name"] in ["tool_sleep", "tool_complete_run"]:
            return "execute_tools_and_end"
            
    return "execute_tools"

# --- Graph Setup ---
workflow = StateGraph(AgentState)

workflow.add_node("classifier", classifier_node)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_executor_node)

workflow.set_entry_point("classifier")

def route_from_classifier(state: AgentState):
    if state.get("wake_decision") == "SLEEP":
        return END
    return "agent"

workflow.add_conditional_edges("classifier", route_from_classifier)

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "execute_tools": "tools",
        "execute_tools_and_end": "tools", # Will route to END after
        "end": END
    }
)

# If it executes normal tools, it goes back to agent to think again
def route_after_tools(state: AgentState):
    if state.get("completed") or state.get("next_wake_at"):
        return END
    return "agent"

workflow.add_conditional_edges("tools", route_after_tools)

graph = workflow.compile()

# --- Main Trigger Entrypoint ---
async def trigger_agent(run_id: str):
    """
    Called by the FastAPI endpoints or the background poller.
    It reads DB state, formats it, runs the LangGraph, and updates DB state.
    """
    lock = get_run_lock(run_id)
        
    async with lock:
        print(f"\n\n==== HELLO FROM TRIGGER AGENT: {run_id} ====\n\n")
        logger.info(f"Triggering agent for run {run_id}")
        
        async with async_session() as db:
            result = await db.execute(select(models.Run).where(models.Run.id == run_id))
            run = result.scalars().first()
            if not run or run.status not in ["active", "sleeping"]:
                logger.info("Run not found or not active.")
                return
            
            sup_result = await db.execute(select(models.Supervisor).where(models.Supervisor.id == run.supervisor_id))
            supervisor = sup_result.scalars().first()
        
            act_result = await db.execute(select(models.Activity).where(models.Activity.run_id == run_id).order_by(models.Activity.created_at.desc()).limit(100))
            all_activities = act_result.scalars().all()
            all_activities.reverse() # chronological order
        
            # Context Compaction: If we have > 20 activities, we summarize the older ones
            # to prevent the LLM context from growing indefinitely.
            if len(all_activities) > 20:
                logger.info("Compacting context...")
                older_activities = all_activities[:-15] # keep last 15 intact
                recent_activities = all_activities[-15:]
            
                # (In a real implementation, we would use an LLM here to summarize `older_activities` into a single text block and store it in run.state)
                # For this POC, we'll simulate the compaction:
                compacted_summary = f"[COMPACTED SUMMARY] {len(older_activities)} older events occurred, including order creation and initial steps."
            
                activity_strings = [compacted_summary]
                activity_strings.extend([f"[{a.created_at.isoformat()}] {a.type.upper()}: {json.dumps(a.payload)}" for a in recent_activities])
                activity_str = "\n".join(activity_strings)
            else:
                activity_str = "\n".join([f"[{a.created_at.isoformat()}] {a.type.upper()}: {json.dumps(a.payload)}" for a in all_activities])
        
            run.status = "active"
            run.next_wake_at = None
            await db.commit()
        
            # In a real app we'd load `run.state["messages"]` here, but for this POC we can just 
            # let the agent read the recent activity log on every wake. 
            # This acts as a compacted context mechanism automatically.
        
            initial_state = {
                "messages": [HumanMessage(content="A new event has arrived or a timer has popped. Review the context and decide your actions.")],
                "run_id": run_id,
                "order_id": run.order_id,
                "supervisor_instruction": supervisor.base_instruction if supervisor else "",
                "recent_activities": activity_str,
                "next_wake_at": None,
                "completed": False
            }
        
        try:
            final_state = await graph.ainvoke(initial_state)
            logger.info(f"Agent finished graph execution for {run_id}.")
            # Note: Sleep/Complete tool handles DB updates.
        except Exception as e:
            logger.error(f"Error executing agent: {e}")
        finally:
            # Fallback: if run is still active (orphaned), force sleep
            async with async_session() as db2:
                result = await db2.execute(select(models.Run).where(models.Run.id == run_id))
                run_check = result.scalars().first()
                if run_check and run_check.status == "active":
                    logger.warning(f"Run {run_id} left active without sleep/complete. Forcing fallback sleep.")
                    await sleep_until(run_id, 1.0)

