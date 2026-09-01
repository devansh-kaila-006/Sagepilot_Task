import httpx
import asyncio

BASE_URL = "http://127.0.0.1:8000/api"

async def wait_for_agent(client, run_id, min_activities, timeout=60):
    print(f"Waiting for agent on run {run_id}...")
    for _ in range(int(timeout / 3)):
        await asyncio.sleep(3)
        res = await client.get(f"{BASE_URL}/runs/{run_id}/activities")
        activities = res.json()["data"]
        
        if len(activities) > min_activities:
            print("Found new activities:")
            for act in activities[min_activities:]:
                print(f"  [{act['created_at']}] {act['type'].upper()}: {act['payload']}")
            return len(activities)
    print("Timed out.")
    return min_activities

async def inject_event(client, run_id, event_type, payload):
    print(f"\n--- Injecting: {event_type} ---")
    await client.post(f"{BASE_URL}/runs/{run_id}/events", json={
        "type": "event",
        "payload": payload
    })

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create Supervisor
        res = await client.post(f"{BASE_URL}/supervisors/", json={
            "name": "Full Event Tester",
            "base_instruction": "Handle standard events normally. If a payment fails after shipment, alert payments and fulfillment. If instructed by a human to override, follow their instructions.",
            "config": {}
        })
        sup_id = res.json()["data"]["id"]
        
        # Create Run
        res = await client.post(f"{BASE_URL}/runs/", json={"order_id": "ORD-TEST-ALL", "supervisor_id": sup_id})
        run_id = res.json()["data"]["id"]
        print(f"Run ID: {run_id}")
        
        act_count = await wait_for_agent(client, run_id, 1)

        events_to_test = [
            ("order_shipped", {"event": "order_shipped", "carrier": "FedEx"}),
            ("delivery_delayed", {"event": "delivery_delayed", "reason": "weather"}),
            ("payment_failed", {"event": "payment_failed", "reason": "chargeback"})
        ]

        for e_name, e_payload in events_to_test:
            await inject_event(client, run_id, e_name, e_payload)
            act_count = await wait_for_agent(client, run_id, act_count + 1)
        
        print(f"\n--- Injecting Instruction ---")
        await client.post(f"{BASE_URL}/runs/{run_id}/instructions", json={
            "type": "instruction",
            "payload": {"instruction": "Ignore payment failure, do not recall package."}
        })
        act_count = await wait_for_agent(client, run_id, act_count + 1)
        
        res = await client.get(f"{BASE_URL}/runs/{run_id}")
        run_data = res.json()["data"]
        print(f"\nFinal Run Status: {run_data['status']}")

if __name__ == "__main__":
    asyncio.run(main())
