import asyncio
import sys
from opsyield.mcp_stdio import run_finops_intelligence, aggregate_finops

async def main():
    try:
        print("Testing run_finops_intelligence...")
        res = await run_finops_intelligence(provider="gcp", days=1, project_id="fake-project")
        print("Result:", res)
    except Exception as e:
        print("run_finops_intelligence failed:", e)

    try:
        print("Testing aggregate_finops...")
        res = await aggregate_finops(providers="gcp,aws", days=1)
        print("Result:", res)
    except Exception as e:
        print("aggregate_finops failed:", e)

if __name__ == "__main__":
    asyncio.run(main())
