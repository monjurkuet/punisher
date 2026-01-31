import httpx
import json


async def debug():
    url = "https://fapi.coinglass.com/api/hyperliquid/address/user/List"
    params = {"groupId": 1, "pageNum": 1, "pageSize": 20}
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "referer": "https://www.coinglass.com/",
        "origin": "https://www.coinglass.com",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }

    async with httpx.AsyncClient(headers=headers, http2=True) as client:
        response = await client.get(url, params=params)
        print(f"Status: {response.status_code}")
        try:
            data = response.json()
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Error: {e}")
            print(f"Raw: {response.text[:200]}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(debug())
