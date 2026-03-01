import asyncio

from tech_digest.db import init_db
from tech_digest.services import run_scrape


async def main():
    init_db()
    result = await run_scrape()
    for source, count in result.items():
        print(f"  {source}: {count} items")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
