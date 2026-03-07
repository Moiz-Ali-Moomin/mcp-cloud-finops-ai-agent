import asyncio
from opsyield.providers.factory import ProviderFactory


async def main():
    try:
        print("Fetching kubernetes provider from factory...")
        provider = ProviderFactory.get_provider("kubernetes")
        print(f"Provider class: {type(provider).__name__}")

        print("\nChecking get_status():")
        status = await provider.get_status()
        print(status)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
