import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        res = await client.post("http://127.0.0.1:8000/api/runs/de9b20eb-36ef-4b06-99c3-9b1aad768349/events", json={
            "type": "event",
            "payload": {"event": "order_shipped"}
        })
        print(res.json())
        print("Waiting for agent to process the event...")
        for _ in range(15): # Poll for up to 45 seconds (15 * 3s)
            await asyncio.sleep(3)
            res = await client.get("http://127.0.0.1:8000/api/runs/de9b20eb-36ef-4b06-99c3-9b1aad768349/activities")
            activities = res.json()["data"]
            # Check if there are new activities beyond the initial inject event
            if any(a["type"] in ["action", "sleep", "complete"] for a in activities):
                print("ACTIVITIES:")
                for a in activities:
                    print(a["type"], a["payload"])
                break
        else:
            print("Timed out waiting for agent to respond. Check backend logs.")

if __name__ == "__main__":
    asyncio.run(main())
