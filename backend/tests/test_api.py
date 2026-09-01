import pytest
from httpx import AsyncClient
from unittest.mock import patch

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_create_supervisor(client: AsyncClient):
    response = await client.post("/api/supervisors/", json={
        "name": "Test Supervisor",
        "base_instruction": "Test instructions",
        "config": {}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "Test Supervisor"
    assert "id" in data["data"]

@pytest.mark.asyncio
@patch("app.agent.trigger_agent")
async def test_create_run(mock_trigger, client: AsyncClient):
    # First create a supervisor
    sup_response = await client.post("/api/supervisors/", json={
        "name": "Run Supervisor",
        "base_instruction": "Run instructions",
        "config": {}
    })
    sup_id = sup_response.json()["data"]["id"]

    # Now create a run
    run_response = await client.post("/api/runs/", json={
        "order_id": "ORD-123",
        "supervisor_id": sup_id
    })
    assert run_response.status_code == 200
    run_data = run_response.json()
    assert run_data["data"]["order_id"] == "ORD-123"
    assert run_data["data"]["supervisor_id"] == sup_id
    assert run_data["data"]["status"] == "active"
    assert "id" in run_data["data"]

@pytest.mark.asyncio
@patch("app.agent.trigger_agent")
async def test_inject_event(mock_trigger, client: AsyncClient):
    sup_response = await client.post("/api/supervisors/", json={
        "name": "Event Supervisor",
        "base_instruction": "Event instructions",
        "config": {}
    })
    sup_id = sup_response.json()["data"]["id"]

    run_response = await client.post("/api/runs/", json={
        "order_id": "ORD-456",
        "supervisor_id": sup_id
    })
    run_id = run_response.json()["data"]["id"]

    event_response = await client.post(f"/api/runs/{run_id}/events", json={
        "type": "test_event",
        "payload": {"message": "hello"}
    })
    assert event_response.status_code == 200
    event_data = event_response.json()
    assert event_data["data"]["type"] == "test_event"
