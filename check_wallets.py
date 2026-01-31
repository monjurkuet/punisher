import asyncio
from punisher.db.mongo import mongo


async def main():
    db = await mongo.get_db()
    count = await db.tracked_wallets.count_documents({})
    print(f"Total Wallets: {count}")


if __name__ == "__main__":
    asyncio.run(main())
