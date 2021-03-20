__all__ = 'run',

from . import coroutines
from . import events
from . import tasks


def run(main, *, debug=False):
    """Execute the coroutine and return the result.

    This function runs the passed coroutine, taking care of
    managing the asyncio event loop and finalizing asynchronous
    generators.

    This function cannot be called when another asyncio event loop is
    running in the same thread.

    If debug is True, the event loop will be run in debug mode.

    This function always creates a new event loop and closes it at the end.
    It should be used as a main entry point for asyncio programs, and should
    ideally only be called once.

    Example:

        async def main():
            await asyncio.sleep(1)
            print('hello')

        asyncio.run(main())
    """
    # run 函数是 asyncio 设计的一个启动入口函数,
    # 如果之前已经创建过 loop 对象, 抛出异常.
    if events._get_running_loop() is not None:
        raise RuntimeError(
            "asyncio.run() cannot be called from a running event loop")

    # main 必须是一个 coroutine 对象, 否则抛出异常.
    if not coroutines.iscoroutine(main):
        raise ValueError("a coroutine was expected, got {!r}".format(main))

    # 创建一个 loop 对象.
    # windows: Iocp
    # linux: epoll
    # unix: kqueue
    loop = events.new_event_loop()

    try:
        # 将 loop 写入到 DefaultEventLoopPolicy._local._loop
        # windows: WindowsProactorEventLoopPolicy
        # linux: UnixDefaultEventLoopPolicy
        # unix: UnixDefaultEventLoopPolicy
        #
        # 其中 _local 的类型是: threading.local(), 用于不同线程之间共享变量.
        events.set_event_loop(loop)
        loop.set_debug(debug)

        # 开始运行 loop 对象(开始执行无限循环: while),
        # run_until_compelete -> run_forever -> while
        return loop.run_until_complete(main)
    finally:
        try:
            _cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            events.set_event_loop(None)
            loop.close()


def _cancel_all_tasks(loop):
    to_cancel = tasks.all_tasks(loop)
    if not to_cancel:
        return

    for task in to_cancel:
        task.cancel()

    loop.run_until_complete(
        tasks.gather(*to_cancel, loop=loop, return_exceptions=True))

    for task in to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler({
                'message': 'unhandled exception during asyncio.run() shutdown',
                'exception': task.exception(),
                'task': task,
            })
