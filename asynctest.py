import asyncio
import time


async def job(sleep: int, jid: int):
    start = time.time()
    print(f"running job {jid}")
    await asyncio.sleep(sleep)
    fin = time.time() - start
    return f"done job {jid} in {fin}"


async def main():
    results = await asyncio.gather(job(1, 3), job(2, 2), job(3, 1))
    print(results)


asyncio.run(main())
