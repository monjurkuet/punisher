import httpx
import json
import base64
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def decrypt(encrypted_text, key_str):
    try:
        key = key_str.encode("utf-8")
        cipher = AES.new(key, AES.MODE_ECB)
        decoded = base64.b64decode(encrypted_text)
        decrypted = cipher.decrypt(decoded)
        return unpad(decrypted, AES.block_size).decode("utf-8")
    except Exception as e:
        return f"Decryption failure: {e}"


async def test_api():
    url = "https://fapi.coinglass.com/api/hyperliquid/address/user/List"
    key = "1f68efd73f8d4921acc0dead41dd39bc"

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "cache-ts-v2": str(int(time.time() * 1000)),
        "encryption": "true",
        "language": "en",
        "origin": "https://www.coinglass.com",
        "referer": "https://www.coinglass.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }

    params = {"groupId": 1, "pageNum": 1, "pageSize": 20}

    async with httpx.AsyncClient(headers=headers, http2=True) as client:
        # Try once with encryption=true
        print("--- Testing with encryption: true ---")
        response = await client.get(url, params=params)
        print(f"Status: {response.status_code}")
        data = response.json()
        print("Response Keys:", list(data.keys()))

        if "data" in data and isinstance(data["data"], str):
            encrypted_data = data["data"]
            print(f"Encrypted data length: {len(encrypted_data)}")
            result = decrypt(encrypted_data, key)
            print("Decrypted Sample:", result[:200])
        elif "data" in data and isinstance(data["data"], dict):
            print("Received cleartext data in dictionary!")
        elif "list" in data or "data" in data:
            print("Received cleartext data directly!")
        else:
            print("No data field found in response.")

        # Try with encryption=false
        print("\n--- Testing with encryption: false ---")
        headers["encryption"] = "false"
        response = await client.get(url, params=params)
        data = response.json()
        print("Response Keys:", list(data.keys()))
        if "data" in data:
            print("Data field found with encryption=false")
            print(json.dumps(data.get("data"), indent=2)[:500])


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_api())
