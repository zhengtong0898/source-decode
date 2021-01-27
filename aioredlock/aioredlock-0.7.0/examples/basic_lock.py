import asyncio
import logging

from aioredlock import Aioredlock, LockError


async def basic_lock():
    lock_manager = Aioredlock([{
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None
    }])

    if await lock_manager.is_locked("resource"):
        print('The resource is already acquired')

    try:
        lock = await lock_manager.lock("resource")
    except LockError:
        print('Something is wrong')
        raise
    assert lock.valid is True
    assert await lock_manager.is_locked("resource") is True

    # Do your stuff having the lock

    await lock_manager.unlock(lock)
    assert lock.valid is False
    assert await lock_manager.is_locked("resource") is False

    await lock_manager.destroy()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(basic_lock())
