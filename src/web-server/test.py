import httpx

async def test_connection():
    url = "http://unruffled_bose:8000/infer"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            print("Response:", response.text)
    except httpx.ConnectError as e:
        print("Connection failed:", e)

# Run the test
import asyncio
asyncio.run(test_connection())

