import httpx
import asyncio
import time

BASE_URL = "http://127.0.0.1:8000/api"

async def wait_for_agent_activity(client, run_id, min_activities, timeout=45):
    print(f"Waiting for agent activities on run {run_id}...")
    for _ in range(int(timeout / 3)):
        await asyncio.sleep(3)
        res = await client.get(f"{BASE_URL}/runs/{run_id}/activities")
        activities = res.json()["data"]
        
        if len(activities) > min_activities:
            print("Found new activities:")
            for act in activities[min_activities:]:
                print(f"  [{act['created_at']}] {act['type'].upper()}: {act['payload']}")
            return len(activities)
    
    print("Timed out waiting for expected activities!")
    return min_activities

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health check
        print("1. Health Check")
        res = await client.get("http://127.0.0.1:8000/health")
        print("  ", res.json())
        
        # 2. Create Supervisor
        print("\n2. Create Supervisor")
        res = await client.post(f"{BASE_URL}/supervisors/", json={
            "name": "E2E Test Supervisor",
            "base_instruction": "You are a highly efficient e2e test agent. Handle routine tasks with notes, but for cancellations or severe issues, always alert the payments team and mark complete.",
            "config": {}
        })
        supervisor_id = res.json()["data"]["id"]
        print(f"   Created Supervisor ID: {supervisor_id}")
        
        # 3. Create Run
        print("\n3. Create Run")
        res = await client.post(f"{BASE_URL}/runs/", json={
            "order_id": "ORD-E2E-999",
            "supervisor_id": supervisor_id
        })
        run_id = res.json()["data"]["id"]
        print(f"   Created Run ID: {run_id}")
        
        # The run creation triggers the agent (start event). Wait for it to sleep.
        act_count = await wait_for_agent_activity(client, run_id, 1) # wait for sleep/action beyond the initial "run_started"
        
        # 4. Inject Event (Routine)
        print("\n4. Inject Routine Event")
        res = await client.post(f"{BASE_URL}/runs/{run_id}/events", json={
            "type": "event",
            "payload": {"event": "payment_processed"}
        })
        act_count = await wait_for_agent_activity(client, run_id, act_count + 1)
        
        # 5. Inject Instruction (Conflicting / Steering)
        print("\n5. Inject Instruction")
        res = await client.post(f"{BASE_URL}/runs/{run_id}/instructions", json={
            "type": "instruction",
            "payload": {"instruction": "Customer requested immediate cancellation. Refund and cancel order."}
        })
        act_count = await wait_for_agent_activity(client, run_id, act_count + 1)
        
        # 6. Check final status
        res = await client.get(f"{BASE_URL}/runs/{run_id}")
        run_data = res.json()["data"]
        print(f"\n6. Final Run Status: {run_data['status']} | Next Wake: {run_data['next_wake_at']}")

if __name__ == "__main__":
    asyncio.run(main())
