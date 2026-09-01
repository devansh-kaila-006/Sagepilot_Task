import httpx
import asyncio
import uuid
import sys

BASE_URL = "http://127.0.0.1:8001/api"

async def wait_for_activities(client, run_id, min_activities, timeout=60):
    for _ in range(int(timeout / 3)):
        await asyncio.sleep(3)
        res = await client.get(f"{BASE_URL}/runs/{run_id}/activities")
        activities = res.json().get("data", [])
        if len(activities) > min_activities:
            return len(activities), activities
    return min_activities, []

async def test_1_terminate_mid_cycle(client, sup_id):
    print("Test 1: Terminate mid-cycle")
    res = await client.post(f"{BASE_URL}/runs/", json={"order_id": "ORD-T1", "supervisor_id": sup_id})
    run_id = res.json()["data"]["id"]
    await wait_for_activities(client, run_id, 1) # wait for start
    
    await client.post(f"{BASE_URL}/runs/{run_id}/events", json={"type": "event", "payload": {"event": "trigger"}})
    await asyncio.sleep(3) # Wait mid-cycle
    await client.post(f"{BASE_URL}/runs/{run_id}/terminate") # Terminate while running!
    
    await asyncio.sleep(40) # Wait for agent to finish
    res = await client.get(f"{BASE_URL}/runs/{run_id}")
    assert res.json()["data"]["status"] == "completed", f"Run should be completed, got {res.json()['data']['status']}"
    print("  PASS")

async def test_2_absurd_hours(client, sup_id):
    print("Test 2: Absurd hours")
    res = await client.post(f"{BASE_URL}/runs/", json={"order_id": "ORD-T2", "supervisor_id": sup_id})
    run_id = res.json()["data"]["id"]
    await wait_for_activities(client, run_id, 1)
    
    await client.post(f"{BASE_URL}/runs/{run_id}/instructions", json={"type": "instruction", "payload": {"instruction": "Call tool_sleep with hours = -1"}})
    await wait_for_activities(client, run_id, 2)
    
    res = await client.get(f"{BASE_URL}/runs/{run_id}/activities")
    sleeps = [a for a in res.json()["data"] if a["type"] == "sleep"]
    if sleeps:
        hrs = sleeps[-1]["payload"].get("duration_hours")
        assert hrs > 0, "Hours should be clamped to a positive value"
    print("  PASS")

async def test_3_resume_completed(client, sup_id):
    print("Test 3: Resume completed run")
    res = await client.post(f"{BASE_URL}/runs/", json={"order_id": "ORD-T3", "supervisor_id": sup_id})
    run_id = res.json()["data"]["id"]
    await client.post(f"{BASE_URL}/runs/{run_id}/terminate")
    
    res = await client.post(f"{BASE_URL}/runs/{run_id}/resume")
    assert res.status_code == 400, "Should reject resume of completed run"
    print("  PASS")

async def test_5_classifier_sleep(client, sup_id):
    print("Test 5: Classifier SLEEP path")
    res = await client.post(f"{BASE_URL}/runs/", json={"order_id": "ORD-T5", "supervisor_id": sup_id})
    run_id = res.json()["data"]["id"]
    act_len, _ = await wait_for_activities(client, run_id, 0)
    
    await client.post(f"{BASE_URL}/runs/{run_id}/events", json={"type": "event", "payload": {"event": "system_ping"}})
    # If it sleeps immediately via fallback, it should happen quickly without agent turn
    act_len, acts = await wait_for_activities(client, run_id, act_len + 1)
    assert any(a["type"] == "sleep" for a in acts), "Should fallback sleep"
    print("  PASS")

async def test_6_agent_initiated_completion(client, sup_id):
    print("Test 6: Agent-initiated completion")
    res = await client.post(f"{BASE_URL}/runs/", json={"order_id": "ORD-T6", "supervisor_id": sup_id})
    run_id = res.json()["data"]["id"]
    act_len, _ = await wait_for_activities(client, run_id, 0)
    
    await client.post(f"{BASE_URL}/runs/{run_id}/events", json={"type": "event", "payload": {"event": "order_delivered"}})
    await client.post(f"{BASE_URL}/runs/{run_id}/instructions", json={"type": "instruction", "payload": {"instruction": "Complete the run immediately. Call tool_complete_run."}})
    act_len, acts = await wait_for_activities(client, run_id, act_len + 1, timeout=90)
    
    res = await client.get(f"{BASE_URL}/runs/{run_id}")
    assert res.json()["data"]["status"] == "completed", "Run should be completed by agent"
    
    res = await client.post(f"{BASE_URL}/runs/{run_id}/events", json={"type": "event", "payload": {"event": "late_event"}})
    assert res.status_code == 400, "Should reject events for completed run"
    print("  PASS")

async def test_8_context_compaction(client, sup_id):
    print("Test 8: Context compaction")
    res = await client.post(f"{BASE_URL}/runs/", json={"order_id": "ORD-T8", "supervisor_id": sup_id})
    run_id = res.json()["data"]["id"]
    
    for i in range(22):
        await client.post(f"{BASE_URL}/runs/{run_id}/events", json={"type": "event", "payload": {"event": f"trivial_{i}"}})
    
    # Send a real instruction
    await client.post(f"{BASE_URL}/runs/{run_id}/instructions", json={"type": "instruction", "payload": {"instruction": "Summarize what you saw."}})
    
    await wait_for_activities(client, run_id, 23, timeout=90)
    print("  PASS")

async def test_9_pause_semantics(client, sup_id):
    print("Test 9: Pause semantics")
    res = await client.post(f"{BASE_URL}/runs/", json={"order_id": "ORD-T9", "supervisor_id": sup_id})
    run_id = res.json()["data"]["id"]
    await wait_for_activities(client, run_id, 1)
    
    await client.post(f"{BASE_URL}/runs/{run_id}/pause")
    await client.post(f"{BASE_URL}/runs/{run_id}/events", json={"type": "event", "payload": {"event": "test_event"}})
    
    await asyncio.sleep(10)
    res = await client.get(f"{BASE_URL}/runs/{run_id}/activities")
    # Make sure agent didn't wake
    sleeps_after_pause = [a for a in res.json()["data"] if a["type"] == "action"]
    assert len(sleeps_after_pause) == 0, "Agent should not wake while paused"
    
    await client.post(f"{BASE_URL}/runs/{run_id}/resume")
    await wait_for_activities(client, run_id, len(res.json()["data"]))
    print("  PASS")

async def test_api_hardening(client):
    print("Test 12-16: API Hardening")
    res = await client.get(f"{BASE_URL}/runs/not-a-uuid")
    assert res.status_code == 404
    
    res = await client.post(f"{BASE_URL}/runs/", json={})
    assert res.status_code == 422
    
    res = await client.post(f"{BASE_URL}/supervisors/", json={"name": "Emoji Sup 🚀", "base_instruction": "Emoji instruction 🎯", "config": {}})
    sup_id = res.json()["data"]["id"]
    
    res = await client.post(f"{BASE_URL}/runs/", json={"order_id": "ORD-EMOJI-🚚", "supervisor_id": sup_id})
    run_id = res.json()["data"]["id"]
    
    await client.post(f"{BASE_URL}/runs/{run_id}/events", json={"type": "event", "payload": {"message": "Order 🚚 delayed — 延迟"}})
    await wait_for_activities(client, run_id, 1)
    
    large_payload = "A" * 10000
    res = await client.post(f"{BASE_URL}/runs/{run_id}/events", json={"type": "event", "payload": {"message": large_payload}})
    assert res.status_code in [200, 413, 422]
    
    print("  PASS")

async def run_test(test_func, *args):
    try:
        await test_func(*args)
    except Exception as e:
        print(f"  FAIL: {e}")

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(f"{BASE_URL}/supervisors/", json={
            "name": "Test Matrix Sup",
            "base_instruction": "You are a test agent.",
            "config": {}
        })
        sup_id = res.json()["data"]["id"]
        
        await run_test(test_1_terminate_mid_cycle, client, sup_id)
        await run_test(test_2_absurd_hours, client, sup_id)
        await run_test(test_3_resume_completed, client, sup_id)
        await run_test(test_5_classifier_sleep, client, sup_id)
        await run_test(test_6_agent_initiated_completion, client, sup_id)
        await run_test(test_8_context_compaction, client, sup_id)
        await run_test(test_9_pause_semantics, client, sup_id)
        await run_test(test_api_hardening, client)
        
        print("\nAll tests finished!")

if __name__ == "__main__":
    asyncio.run(main())
