import asyncio

from agents.agent import ask_agent


async def main():
    result = await ask_agent("Convénceme de contratar a Jeyker")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())