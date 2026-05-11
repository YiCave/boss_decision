import asyncio
import httpx

async def main():
    urls = [
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    ]
    headers = {"Authorization": "Bearer AIzaSyAQJJriMtIB6_nScuUZHzbZ365H7Hs6pHU"}
    payload = {
        "model": "gemini-2.5-flash-lite",
        "messages": [{"role": "user", "content": "hi"}],
        "temperature": 0.3
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for url in urls:
            try:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                print(f"Success for {url}: {resp.json()}")
            except Exception as e:
                print(f"Error for {url}: {type(e).__name__} - '{e}'")

asyncio.run(main())
