"""Support for tasks, coroutines and the scheduler."""

__all__ = (
    'Task', 'create_task',
    'FIRST_COMPLETED', 'FIRST_EXCEPTION', 'ALL_COMPLETED',
    'wait', 'wait_for', 'as_completed', 'sleep',
    'gather', 'shield', 'ensure_future', 'run_coroutine_threadsafe',
    'current_task', 'all_tasks',
    '_register_task', '_unregister_task', '_enter_task', '_leave_task',
)

import concurrent.futures
import contextvars
import functools
import inspect
import itertools
import types
import warnings
import weakref

from . import base_tasks
from . import coroutines
from . import events
from . import exceptions
from . import futures
from .coroutines import _is_coroutine

# Helper to generate new task names
# This uses itertools.count() instead of a "+= 1" operation because the latter
# is not thread safe. See bpo-11866 for a longer explanation.
_task_name_counter = itertools.count(1).__next__


def current_task(loop=None):
    """Return a currently executed task."""
    if loop is None:
        loop = events.get_running_loop()
    return _current_tasks.get(loop)


def all_tasks(loop=None):
    """Return a set of all tasks for the loop."""
    if loop is None:
        loop = events.get_running_loop()
    # Looping over a WeakSet (_all_tasks) isn't safe as it can be updated from another
    # thread while we do so. Therefore we cast it to list prior to filtering. The list
    # cast itself requires iteration, so we repeat it several times ignoring
    # RuntimeErrors (which are not very likely to occur). See issues 34970 and 36607 for
    # details.
    i = 0
    while True:
        try:
            tasks = list(_all_tasks)
        except RuntimeError:
            i += 1
            if i >= 1000:
                raise
        else:
            break
    return {t for t in tasks
            if futures._get_loop(t) is loop and not t.done()}


def _all_tasks_compat(loop=None):
    # Different from "all_task()" by returning *all* Tasks, including
    # the completed ones.  Used to implement deprecated "Tasks.all_task()"
    # method.
    if loop is None:
        loop = events.get_event_loop()
    # Looping over a WeakSet (_all_tasks) isn't safe as it can be updated from another
    # thread while we do so. Therefore we cast it to list prior to filtering. The list
    # cast itself requires iteration, so we repeat it several times ignoring
    # RuntimeErrors (which are not very likely to occur). See issues 34970 and 36607 for
    # details.
    i = 0
    while True:
        try:
            tasks = list(_all_tasks)
        except RuntimeError:
            i += 1
            if i >= 1000:
                raise
        else:
            break
    return {t for t in tasks if futures._get_loop(t) is loop}


def _set_task_name(task, name):
    if name is not None:
        try:
            set_name = task.set_name
        except AttributeError:
            pass
        else:
            set_name(name)


#######################################################################################################################
# Task
# Task 是 asyncio 重要的一个成员, 服务于开发者, 用于将 coroutine 函数推送给 loop 去执行.
# Task 本身继承了 Future 对象, 主要是为了保存一些状态(Pending/Cancelled/Finished)和异常信息.
#######################################################################################################################
class Task(futures._PyFuture):  # Inherit Python Task implementation
                                # from a Python Future implementation.

    """A coroutine wrapped in a Future."""

    # An important invariant maintained while a Task not done:
    #
    # - Either _fut_waiter is None, and _step() is scheduled;
    # - or _fut_waiter is some Future, and _step() is *not* scheduled.
    #
    # The only transition from the latter to the former is through
    # _wakeup().  When _fut_waiter is not None, one of its callbacks
    # must be _wakeup().

    # If False, don't log a message if the task is destroyed whereas its
    # status is still pending
    _log_destroy_pending = True

    @classmethod
    def current_task(cls, loop=None):
        """Return the currently running task in an event loop or None.

        By default the current task for the current event loop is returned.

        None is returned when called not in the context of a Task.
        """
        warnings.warn("Task.current_task() is deprecated since Python 3.7, "
                      "use asyncio.current_task() instead",
                      DeprecationWarning,
                      stacklevel=2)
        if loop is None:
            loop = events.get_event_loop()
        return current_task(loop)

    @classmethod
    def all_tasks(cls, loop=None):
        """Return a set of all tasks for an event loop.

        By default all tasks for the current event loop are returned.
        """
        warnings.warn("Task.all_tasks() is deprecated since Python 3.7, "
                      "use asyncio.all_tasks() instead",
                      DeprecationWarning,
                      stacklevel=2)
        return _all_tasks_compat(loop)

    ###############################################################################################################
    # 参数 coro: 期望一个coroutine对象(在python3.6之后是 async def 对象).
    #
    # 备注:
    # 参数 * 号右侧的参数表示, 在提供 loop, name 这两个实参时, 必须提供参数名称.
    ###############################################################################################################
    def __init__(self, coro, *, loop=None, name=None):
        super().__init__(loop=loop)
        if self._source_traceback:
            del self._source_traceback[-1]

        # 如果参数 coro 的值不是一个coroutine对象那么就会抛出异常.
        if not coroutines.iscoroutine(coro):
            # raise after Future.__init__(), attrs are required for __del__
            # prevent logging for pending task in __del__
            self._log_destroy_pending = False
            raise TypeError(f"a coroutine was expected, got {coro!r}")

        # 如果没有提供name参数, 那么这里按 Task-number 来命名这个任务.
        if name is None:
            self._name = f'Task-{_task_name_counter()}'
        else:
            self._name = str(name)

        # 这是一个私有变量, 外部程序篡改该值会出现不可预期的行为.
        # 这个变量只有 Task.cancel 方法可以设定为 True, 用于表示取消当前 Task 任务.
        # 由于 task 任务的执行不取决于它自己, 决定权在 loop 对象上,
        # 因此能做的就是标记和声明任务是取消状态, 当 loop 开始执行 task 任务时(self.__step),
        # task会执行之前检查 self._must_cancel 是不是 True, 如果是True则抛出异常或者跳过执行.
        self._must_cancel = False

        # 这是一个私有变量, 外部程序篡改该值会出现不可预期的行为.
        # 变量类型: Future
        # 用于暂存 coro 执行过程中挂起的 Future 对象.
        self._fut_waiter = None

        # 将 coro 函数, 存储在 self._coro 中(目的是: 强引用保留对象不被回收.)
        self._coro = coro
        self._context = contextvars.copy_context()

        # 将任务推送给 loop .
        self._loop.call_soon(self.__step, context=self._context)

        # 将当前 Task 加入到弱引用集合
        # 弱引用就是引用, 只不过是当对象存在时, 可以跟引用一样正常使用,
        # 当对象被销毁之后, 弱引用的属性或方法的调用将会触发异常报错,
        # 所以, 弱引用通常在使用之前都要判断一下弱引用是否有效.
        _register_task(self)

    def __del__(self):
        if self._state == futures._PENDING and self._log_destroy_pending:
            context = {
                'task': self,
                'message': 'Task was destroyed but it is pending!',
            }
            if self._source_traceback:
                context['source_traceback'] = self._source_traceback
            self._loop.call_exception_handler(context)
        super().__del__()

    def _repr_info(self):
        return base_tasks._task_repr_info(self)

    def get_coro(self):
        return self._coro

    def get_name(self):
        return self._name

    def set_name(self, value):
        self._name = str(value)

    ###################################################################################################################
    # 不让开发者调用Task.set_result方法, 但是内部可以使用 super().set_result() 方式来做一些其他事情.
    ###################################################################################################################
    def set_result(self, result):
        raise RuntimeError('Task does not support set_result operation')

    ###################################################################################################################
    # 不让开发者调用Task.set_exception方法, 但是内部可以使用 super().set_exception() 方式来做一些其他事情.
    ###################################################################################################################
    def set_exception(self, exception):
        raise RuntimeError('Task does not support set_exception operation')

    def get_stack(self, *, limit=None):
        """Return the list of stack frames for this task's coroutine.

        If the coroutine is not done, this returns the stack where it is
        suspended.  If the coroutine has completed successfully or was
        cancelled, this returns an empty list.  If the coroutine was
        terminated by an exception, this returns the list of traceback
        frames.

        The frames are always ordered from oldest to newest.

        The optional limit gives the maximum number of frames to
        return; by default all available frames are returned.  Its
        meaning differs depending on whether a stack or a traceback is
        returned: the newest frames of a stack are returned, but the
        oldest frames of a traceback are returned.  (This matches the
        behavior of the traceback module.)

        For reasons beyond our control, only one stack frame is
        returned for a suspended coroutine.
        """
        return base_tasks._task_get_stack(self, limit)

    def print_stack(self, *, limit=None, file=None):
        """Print the stack or traceback for this task's coroutine.

        This produces output similar to that of the traceback module,
        for the frames retrieved by get_stack().  The limit argument
        is passed to get_stack().  The file argument is an I/O stream
        to which the output is written; by default output is written
        to sys.stderr.
        """
        return base_tasks._task_print_stack(self, limit, file)

    ###################################################################################################################
    # 彻底覆盖 Future 的 cancel 接口, 因为它并没有执行 super().cancel, 所以说是彻底覆盖.
    #
    # Future.cancel 是将状态设定为 Cancelled 并且将所有的_callbacks推送(通知)给 loop 去执行.
    # task.cancel 是将等待的那个Future(即: self._fut_waiter)的状态设定为Cancelled, 并且声明当前任务是取消状态(self._must_cancel).
    ###################################################################################################################
    def cancel(self):
        """Request that this task cancel itself.

        This arranges for a CancelledError to be thrown into the
        wrapped coroutine on the next cycle through the event loop.
        The coroutine then has a chance to clean up or even deny
        the request using try/except/finally.

        Unlike Future.cancel, this does not guarantee that the
        task will be cancelled: the exception might be caught and
        acted upon, delaying cancellation of the task or preventing
        cancellation completely.  The task may also return a value or
        raise a different exception.

        Immediately after this method is called, Task.cancelled() will
        not return True (unless the task was already cancelled).  A
        task will be marked as cancelled when the wrapped coroutine
        terminates with a CancelledError exception (even if cancel()
        was not called).
        """
        self._log_traceback = False
        if self.done():
            return False
        if self._fut_waiter is not None:
            if self._fut_waiter.cancel():
                # Leave self._fut_waiter; it may be a Task that
                # catches and ignores the cancellation so we may have
                # to cancel it again later.
                return True
        # It must be the case that self.__step is already scheduled.
        self._must_cancel = True
        return True

    ###################################################################################################################
    # 当前函数负责执行 coro 函数,
    # 如果 coro 返回的对象是堵塞状态(Future是Pending), 那么就将 self.__wakeup 丢到 add_done_callback 中.
    # 如果 coro 返回的对象是非堵塞状态(Future是Cancelled或Finished), 那么就通知 loop 执行 self.__step 提取结果.
    ###################################################################################################################
    def __step(self, exc=None):
        # 如果当前任务已经是 Cancelled 或 Finished 转台, 那么就抛出异常.
        if self.done():
            raise exceptions.InvalidStateError(
                f'_step(): already done: {self!r}, {exc!r}')

        # self._must_cancel == True, 意味着已经声明取消当前 task.
        # 所以这里会定义 exc 异常对象信息, 后续再执行 coro 的时候就会 coro.throw(exc)
        if self._must_cancel:
            if not isinstance(exc, exceptions.CancelledError):
                exc = exceptions.CancelledError()
            self._must_cancel = False

        coro = self._coro
        self._fut_waiter = None

        _enter_task(self._loop, self)
        # Call either coro.throw(exc) or coro.send(None).
        try:
            # 定义了async def 的函数, 都是 coroutine 对象.
            # coroutine 有三种运作方式:
            # 1. 通过 return 关键字返回一个具体值.(抛出一个 StopIteratorException)
            # 2. 通过 await 关键字, 递归进入被await的那个函数, 被await的函数返回一个具体值.(抛出一个 StopIteratorException).
            # 3. 通过 await 关键字, 递归进入被await的那个函数, 被await的函数返回一个Future,
            #    由于 Future.__await__ 中有定义 yield self, 所以这里不会抛出 StopIteratorException.
            #    也正是因为 Future.__await__ 中定义了 yield self,
            #    它会把 coroutine 这个函数给hang住, 让 loop 可以继续去执行其他代码, 举例:
            #    def hello():
            #        count = 1
            #        while True:
            #            yield count
            #            count += 1
            #
            #    h = hello()
            #    print(h.send(None))             # 1
            #    print(h.send(None))             # 2
            #    print(h.send(None))             # 3
            #    print(h.send(None))             # 4
            #
            #    这段代码完全没有堵塞, yield每次都会返回一个值, 并且hang住, 不会堵塞主程序.
            if exc is None:
                # We use the `send` method directly, because coroutines
                # don't have `__iter__` and `__next__` methods.
                result = coro.send(None)
            else:
                result = coro.throw(exc)
        except StopIteration as exc:
            # 如果抛出异常, 代表 coroutine 函数对象已经执行结束了, 并且返回一个具体值(没有值的话就是None).
            if self._must_cancel:
                # Task is cancelled right before coro stops.
                self._must_cancel = False
                super().cancel()
            else:
                # 从 exc 异常对象中提取返回值, 保存在 task.result (task也是一个Future) 中.
                super().set_result(exc.value)
        except exceptions.CancelledError:
            # 如果在 coroutine 函数对象中, 主动抛出 CancelledError,
            # 那么这里就将task状态更改为 Cancelled, 并通知执行所有的callbacks.
            super().cancel()  # I.e., Future.cancel(self).
        except (KeyboardInterrupt, SystemExit) as exc:
            # 如果在 coroutine 函数对象正在运行过程中, 由人工手工 Ctrl + C 触发异常,
            # 那么就将 task 状态更改为 Cancelled, 并通知执行所有的callbacks.
            super().set_exception(exc)
            raise
        except BaseException as exc:
            # 如果在 coroutine 函数对象中, 任何代码异常都会进入到这里,
            # 这里会将 Task 状态更改为 Cancelled, 并通知执行所有的callbacks.
            super().set_exception(exc)
        else:
            # 代码进入到这里表示 coroutine 还没有运行结束, 同时也没有报错, 可以确定的是 coroutine 里面一定使用了 yield.
            # 那么接下来要做的就是判断 result 是个什么东西,
            # 1. 如果 result._asyncio_future_blocking 属性存在, 那么它就是一个Future(也就是进入: if blocking is not None 条件块.)
            # 2. 如果 result 是 None, 那么就表示 yield None(也就是进入: elif result is None), 为了能把 coroutine 执行完,
            #    这里还是会将self.__step(自己)再次丢给 loop 让它再执行一次, 把整个 coroutine 函数执行完.
            # 3. 如果 result 是 generator 函数对象(也就是进入: elif inspect.isgenerator), 那么就抛出异常.
            # 4. 其他情况(也就是进入: else ), 那么就抛出异常了.
            blocking = getattr(result, '_asyncio_future_blocking', None)
            if blocking is not None:
                # TODO: 会有多个 loop ?
                # Yielded Future must come from Future.__iter__().
                if futures._get_loop(result) is not self._loop:
                    new_exc = RuntimeError(
                        f'Task {self!r} got Future '
                        f'{result!r} attached to a different loop')
                    self._loop.call_soon(
                        self.__step, new_exc, context=self._context)
                elif blocking:
                    if result is self:
                        new_exc = RuntimeError(
                            f'Task cannot await on itself: {self!r}')
                        self._loop.call_soon(
                            self.__step, new_exc, context=self._context)
                    else:
                        # 代码进入到这里表示: result._asyncio_future_blocking == True,
                        # 意味着当前这个 Future 是堵塞状态, 稍后在执行.
                        #
                        # 然而这里紧接着就将 result._asyncio_future_blocking 设置为 False,
                        # 目的是告诉 self.__wakeup (add_done_callback), 下次执行的时候不是堵塞状态.
                        #
                        # result.add_done_callback 会将 self.__weakup 放入到 result._callbacks 中,
                        # 至于什么时候会执行 self.__weakup, 取决于以下三种场景:
                        # 1. result.cancel()        # 取消任务
                        # 2. result.set_exception() # 任务异常
                        # 3. result.set_result()    # 任务已完成(重要: 由异步客户端完成堵塞任务之后执行set_result,)
                        #                                            set_result会将 result 这个future的状态更改为
                        #                                            _FINISHED, 并通过 loop.call_soon 让 loop 将
                        #                                            __weakup放入到 loop._ready 列表中.
                        #                                            loop 会再循环的例行事务中读取_ready中的__weakup
                        #                                            方法并执行.
                        result._asyncio_future_blocking = False
                        result.add_done_callback(
                            self.__wakeup, context=self._context)

                        # 将 result 这个 Future 暂存到 self._fut_waiter 属性中.
                        self._fut_waiter = result

                        # 如果声明了取消任务, 那么这里就将 self._fut_waiter 设定为取消.
                        if self._must_cancel:
                            if self._fut_waiter.cancel():
                                self._must_cancel = False
                else:
                    new_exc = RuntimeError(
                        f'yield was used instead of yield from '
                        f'in task {self!r} with {result!r}')
                    self._loop.call_soon(
                        self.__step, new_exc, context=self._context)

            elif result is None:
                # Bare yield relinquishes control for one event loop iteration.
                self._loop.call_soon(self.__step, context=self._context)
            elif inspect.isgenerator(result):
                # Yielding a generator is just wrong.
                new_exc = RuntimeError(
                    f'yield was used instead of yield from for '
                    f'generator in task {self!r} with {result!r}')
                self._loop.call_soon(
                    self.__step, new_exc, context=self._context)
            else:
                # Yielding something else is an error.
                new_exc = RuntimeError(f'Task got bad yield: {result!r}')
                self._loop.call_soon(
                    self.__step, new_exc, context=self._context)
        finally:
            _leave_task(self._loop, self)
            self = None  # Needed to break cycles when an exception occurs.

    ###################################################################################################################
    # 该方法试图读取 future 的结果值,
    # 如果读取到具体值, 则表示该事务算就结束了;
    # 如果读取报错, 则表示 future 仍然是堵塞状态, 再次执行 self.__step ,
    # 目的是让它再次执行 coro.send(None), 从而触发 coro 函数内的 await 的后半段代码, 周而复始...
   ###################################################################################################################
    def __wakeup(self, future):
        try:
            future.result()
        except BaseException as exc:
            # This may also be a cancellation.
            self.__step(exc)
        else:
            # Don't pass the value of `future.result()` explicitly,
            # as `Future.__iter__` and `Future.__await__` don't need it.
            # If we call `_step(value, None)` instead of `_step()`,
            # Python eval loop would use `.send(value)` method call,
            # instead of `__next__()`, which is slower for futures
            # that return non-generator iterators from their `__iter__`.
            self.__step()
        self = None  # Needed to break cycles when an exception occurs.


_PyTask = Task


try:
    import _asyncio
except ImportError:
    pass
else:
    # _CTask is needed for tests.
    Task = _CTask = _asyncio.Task


def create_task(coro, *, name=None):
    """Schedule the execution of a coroutine object in a spawn task.

    Return a Task object.
    """
    loop = events.get_running_loop()
    task = loop.create_task(coro)
    _set_task_name(task, name)
    return task


# wait() and as_completed() similar to those in PEP 3148.

FIRST_COMPLETED = concurrent.futures.FIRST_COMPLETED
FIRST_EXCEPTION = concurrent.futures.FIRST_EXCEPTION
ALL_COMPLETED = concurrent.futures.ALL_COMPLETED


async def wait(fs, *, loop=None, timeout=None, return_when=ALL_COMPLETED):
    """Wait for the Futures and coroutines given by fs to complete.

    The sequence futures must not be empty.

    Coroutines will be wrapped in Tasks.

    Returns two sets of Future: (done, pending).

    Usage:

        done, pending = await asyncio.wait(fs)

    Note: This does not raise TimeoutError! Futures that aren't done
    when the timeout occurs are returned in the second set.
    """
    if futures.isfuture(fs) or coroutines.iscoroutine(fs):
        raise TypeError(f"expect a list of futures, not {type(fs).__name__}")
    if not fs:
        raise ValueError('Set of coroutines/Futures is empty.')
    if return_when not in (FIRST_COMPLETED, FIRST_EXCEPTION, ALL_COMPLETED):
        raise ValueError(f'Invalid return_when value: {return_when}')

    if loop is None:
        loop = events.get_running_loop()
    else:
        warnings.warn("The loop argument is deprecated since Python 3.8, "
                      "and scheduled for removal in Python 3.10.",
                      DeprecationWarning, stacklevel=2)

    fs = {ensure_future(f, loop=loop) for f in set(fs)}

    return await _wait(fs, timeout, return_when, loop)


def _release_waiter(waiter, *args):
    if not waiter.done():
        waiter.set_result(None)


async def wait_for(fut, timeout, *, loop=None):
    """Wait for the single Future or coroutine to complete, with timeout.

    Coroutine will be wrapped in Task.

    Returns result of the Future or coroutine.  When a timeout occurs,
    it cancels the task and raises TimeoutError.  To avoid the task
    cancellation, wrap it in shield().

    If the wait is cancelled, the task is also cancelled.

    This function is a coroutine.
    """
    if loop is None:
        loop = events.get_running_loop()
    else:
        warnings.warn("The loop argument is deprecated since Python 3.8, "
                      "and scheduled for removal in Python 3.10.",
                      DeprecationWarning, stacklevel=2)

    if timeout is None:
        return await fut

    if timeout <= 0:
        fut = ensure_future(fut, loop=loop)

        if fut.done():
            return fut.result()

        fut.cancel()
        raise exceptions.TimeoutError()

    waiter = loop.create_future()
    timeout_handle = loop.call_later(timeout, _release_waiter, waiter)
    cb = functools.partial(_release_waiter, waiter)

    fut = ensure_future(fut, loop=loop)
    fut.add_done_callback(cb)

    try:
        # wait until the future completes or the timeout
        try:
            await waiter
        except exceptions.CancelledError:
            fut.remove_done_callback(cb)
            fut.cancel()
            raise

        if fut.done():
            return fut.result()
        else:
            fut.remove_done_callback(cb)
            # We must ensure that the task is not running
            # after wait_for() returns.
            # See https://bugs.python.org/issue32751
            await _cancel_and_wait(fut, loop=loop)
            raise exceptions.TimeoutError()
    finally:
        timeout_handle.cancel()


async def _wait(fs, timeout, return_when, loop):
    """Internal helper for wait().

    The fs argument must be a collection of Futures.
    """
    assert fs, 'Set of Futures is empty.'
    waiter = loop.create_future()
    timeout_handle = None
    if timeout is not None:
        timeout_handle = loop.call_later(timeout, _release_waiter, waiter)
    counter = len(fs)

    def _on_completion(f):
        nonlocal counter
        counter -= 1
        if (counter <= 0 or
            return_when == FIRST_COMPLETED or
            return_when == FIRST_EXCEPTION and (not f.cancelled() and
                                                f.exception() is not None)):
            if timeout_handle is not None:
                timeout_handle.cancel()
            if not waiter.done():
                waiter.set_result(None)

    for f in fs:
        f.add_done_callback(_on_completion)

    try:
        await waiter
    finally:
        if timeout_handle is not None:
            timeout_handle.cancel()
        for f in fs:
            f.remove_done_callback(_on_completion)

    done, pending = set(), set()
    for f in fs:
        if f.done():
            done.add(f)
        else:
            pending.add(f)
    return done, pending


async def _cancel_and_wait(fut, loop):
    """Cancel the *fut* future or task and wait until it completes."""

    waiter = loop.create_future()
    cb = functools.partial(_release_waiter, waiter)
    fut.add_done_callback(cb)

    try:
        fut.cancel()
        # We cannot wait on *fut* directly to make
        # sure _cancel_and_wait itself is reliably cancellable.
        await waiter
    finally:
        fut.remove_done_callback(cb)


# This is *not* a @coroutine!  It is just an iterator (yielding Futures).
def as_completed(fs, *, loop=None, timeout=None):
    """Return an iterator whose values are coroutines.

    When waiting for the yielded coroutines you'll get the results (or
    exceptions!) of the original Futures (or coroutines), in the order
    in which and as soon as they complete.

    This differs from PEP 3148; the proper way to use this is:

        for f in as_completed(fs):
            result = await f  # The 'await' may raise.
            # Use result.

    If a timeout is specified, the 'await' will raise
    TimeoutError when the timeout occurs before all Futures are done.

    Note: The futures 'f' are not necessarily members of fs.
    """
    if futures.isfuture(fs) or coroutines.iscoroutine(fs):
        raise TypeError(f"expect a list of futures, not {type(fs).__name__}")

    from .queues import Queue  # Import here to avoid circular import problem.
    done = Queue(loop=loop)

    if loop is None:
        loop = events.get_event_loop()
    else:
        warnings.warn("The loop argument is deprecated since Python 3.8, "
                      "and scheduled for removal in Python 3.10.",
                      DeprecationWarning, stacklevel=2)
    todo = {ensure_future(f, loop=loop) for f in set(fs)}
    timeout_handle = None

    def _on_timeout():
        for f in todo:
            f.remove_done_callback(_on_completion)
            done.put_nowait(None)  # Queue a dummy value for _wait_for_one().
        todo.clear()  # Can't do todo.remove(f) in the loop.

    def _on_completion(f):
        if not todo:
            return  # _on_timeout() was here first.
        todo.remove(f)
        done.put_nowait(f)
        if not todo and timeout_handle is not None:
            timeout_handle.cancel()

    async def _wait_for_one():
        f = await done.get()
        if f is None:
            # Dummy value from _on_timeout().
            raise exceptions.TimeoutError
        return f.result()  # May raise f.exception().

    for f in todo:
        f.add_done_callback(_on_completion)
    if todo and timeout is not None:
        timeout_handle = loop.call_later(timeout, _on_timeout)
    for _ in range(len(todo)):
        yield _wait_for_one()


@types.coroutine
def __sleep0():
    """Skip one event loop run cycle.

    This is a private helper for 'asyncio.sleep()', used
    when the 'delay' is set to 0.  It uses a bare 'yield'
    expression (which Task.__step knows how to handle)
    instead of creating a Future object.
    """
    yield


async def sleep(delay, result=None, *, loop=None):
    """Coroutine that completes after a given time (in seconds)."""
    if delay <= 0:
        await __sleep0()
        return result

    if loop is None:
        loop = events.get_running_loop()
    else:
        warnings.warn("The loop argument is deprecated since Python 3.8, "
                      "and scheduled for removal in Python 3.10.",
                      DeprecationWarning, stacklevel=2)

    future = loop.create_future()
    h = loop.call_later(delay,
                        futures._set_result_unless_cancelled,
                        future, result)
    try:
        return await future
    finally:
        h.cancel()


#######################################################################################################################
# 如果参数 coro_or_future 是 coroutine 对象, 那么就创建一个 Task 对象(它也是一个Future).
# 如果参数 coro_or_future 是 Future 对象, 那么就直接返回该 Future 对象.
# 如果参数 coro_or_future 是 awaitable 对象, 那么就封装 awaitable 对象为 coroutine 对象, 然后再次递归调用自己, 创建并返回Task对象.
# 如果参数 coro_or_future 不是上述三种对象, 那么就抛出异常, 退出程序.
#######################################################################################################################
def ensure_future(coro_or_future, *, loop=None):
    """Wrap a coroutine or an awaitable in a future.

    If the argument is a Future, it is returned directly.
    """
    if coroutines.iscoroutine(coro_or_future):
        if loop is None:
            loop = events.get_event_loop()
        task = loop.create_task(coro_or_future)
        if task._source_traceback:
            del task._source_traceback[-1]
        return task
    elif futures.isfuture(coro_or_future):
        if loop is not None and loop is not futures._get_loop(coro_or_future):
            raise ValueError('The future belongs to a different loop than '
                             'the one specified as the loop argument')
        return coro_or_future
    elif inspect.isawaitable(coro_or_future):
        return ensure_future(_wrap_awaitable(coro_or_future), loop=loop)
    else:
        raise TypeError('An asyncio.Future, a coroutine or an awaitable is '
                        'required')


@types.coroutine
def _wrap_awaitable(awaitable):
    """Helper for asyncio.ensure_future().

    Wraps awaitable (an object with __await__) into a coroutine
    that will later be wrapped in a Task by ensure_future().
    """
    return (yield from awaitable.__await__())

_wrap_awaitable._is_coroutine = _is_coroutine


class _GatheringFuture(futures.Future):
    """Helper for gather().

    This overrides cancel() to cancel all the children and act more
    like Task.cancel(), which doesn't immediately mark itself as
    cancelled.
    """

    def __init__(self, children, *, loop=None):
        super().__init__(loop=loop)
        self._children = children
        self._cancel_requested = False

    def cancel(self):
        if self.done():
            return False
        ret = False
        for child in self._children:
            if child.cancel():
                ret = True
        if ret:
            # If any child tasks were actually cancelled, we should
            # propagate the cancellation request regardless of
            # *return_exceptions* argument.  See issue 32684.
            self._cancel_requested = True
        return ret


def gather(*coros_or_futures, loop=None, return_exceptions=False):
    """Return a future aggregating results from the given coroutines/futures.

    Coroutines will be wrapped in a future and scheduled in the event
    loop. They will not necessarily be scheduled in the same order as
    passed in.

    All futures must share the same event loop.  If all the tasks are
    done successfully, the returned future's result is the list of
    results (in the order of the original sequence, not necessarily
    the order of results arrival).  If *return_exceptions* is True,
    exceptions in the tasks are treated the same as successful
    results, and gathered in the result list; otherwise, the first
    raised exception will be immediately propagated to the returned
    future.

    Cancellation: if the outer Future is cancelled, all children (that
    have not completed yet) are also cancelled.  If any child is
    cancelled, this is treated as if it raised CancelledError --
    the outer Future is *not* cancelled in this case.  (This is to
    prevent the cancellation of one child to cause other children to
    be cancelled.)
    """
    if not coros_or_futures:
        if loop is None:
            loop = events.get_event_loop()
        else:
            warnings.warn("The loop argument is deprecated since Python 3.8, "
                          "and scheduled for removal in Python 3.10.",
                          DeprecationWarning, stacklevel=2)
        outer = loop.create_future()
        outer.set_result([])
        return outer

    def _done_callback(fut):
        nonlocal nfinished
        nfinished += 1

        if outer.done():
            if not fut.cancelled():
                # Mark exception retrieved.
                fut.exception()
            return

        if not return_exceptions:
            if fut.cancelled():
                # Check if 'fut' is cancelled first, as
                # 'fut.exception()' will *raise* a CancelledError
                # instead of returning it.
                exc = exceptions.CancelledError()
                outer.set_exception(exc)
                return
            else:
                exc = fut.exception()
                if exc is not None:
                    outer.set_exception(exc)
                    return

        if nfinished == nfuts:
            # All futures are done; create a list of results
            # and set it to the 'outer' future.
            results = []

            for fut in children:
                if fut.cancelled():
                    # Check if 'fut' is cancelled first, as
                    # 'fut.exception()' will *raise* a CancelledError
                    # instead of returning it.
                    res = exceptions.CancelledError()
                else:
                    res = fut.exception()
                    if res is None:
                        res = fut.result()
                results.append(res)

            if outer._cancel_requested:
                # If gather is being cancelled we must propagate the
                # cancellation regardless of *return_exceptions* argument.
                # See issue 32684.
                outer.set_exception(exceptions.CancelledError())
            else:
                outer.set_result(results)

    arg_to_fut = {}
    children = []
    nfuts = 0
    nfinished = 0
    for arg in coros_or_futures:
        if arg not in arg_to_fut:
            fut = ensure_future(arg, loop=loop)
            if loop is None:
                loop = futures._get_loop(fut)
            if fut is not arg:
                # 'arg' was not a Future, therefore, 'fut' is a new
                # Future created specifically for 'arg'.  Since the caller
                # can't control it, disable the "destroy pending task"
                # warning.
                fut._log_destroy_pending = False

            nfuts += 1
            arg_to_fut[arg] = fut
            fut.add_done_callback(_done_callback)

        else:
            # There's a duplicate Future object in coros_or_futures.
            fut = arg_to_fut[arg]

        children.append(fut)

    outer = _GatheringFuture(children, loop=loop)
    return outer


def shield(arg, *, loop=None):
    """Wait for a future, shielding it from cancellation.

    The statement

        res = await shield(something())

    is exactly equivalent to the statement

        res = await something()

    *except* that if the coroutine containing it is cancelled, the
    task running in something() is not cancelled.  From the POV of
    something(), the cancellation did not happen.  But its caller is
    still cancelled, so the yield-from expression still raises
    CancelledError.  Note: If something() is cancelled by other means
    this will still cancel shield().

    If you want to completely ignore cancellation (not recommended)
    you can combine shield() with a try/except clause, as follows:

        try:
            res = await shield(something())
        except CancelledError:
            res = None
    """
    if loop is not None:
        warnings.warn("The loop argument is deprecated since Python 3.8, "
                      "and scheduled for removal in Python 3.10.",
                      DeprecationWarning, stacklevel=2)
    inner = ensure_future(arg, loop=loop)
    if inner.done():
        # Shortcut.
        return inner
    loop = futures._get_loop(inner)
    outer = loop.create_future()

    def _inner_done_callback(inner):
        if outer.cancelled():
            if not inner.cancelled():
                # Mark inner's result as retrieved.
                inner.exception()
            return

        if inner.cancelled():
            outer.cancel()
        else:
            exc = inner.exception()
            if exc is not None:
                outer.set_exception(exc)
            else:
                outer.set_result(inner.result())


    def _outer_done_callback(outer):
        if not inner.done():
            inner.remove_done_callback(_inner_done_callback)

    inner.add_done_callback(_inner_done_callback)
    outer.add_done_callback(_outer_done_callback)
    return outer


def run_coroutine_threadsafe(coro, loop):
    """Submit a coroutine object to a given event loop.

    Return a concurrent.futures.Future to access the result.
    """
    if not coroutines.iscoroutine(coro):
        raise TypeError('A coroutine object is required')
    future = concurrent.futures.Future()

    def callback():
        try:
            futures._chain_future(ensure_future(coro, loop=loop), future)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as exc:
            if future.set_running_or_notify_cancel():
                future.set_exception(exc)
            raise

    loop.call_soon_threadsafe(callback)
    return future


# WeakSet containing all alive tasks.
_all_tasks = weakref.WeakSet()

# Dictionary containing tasks that are currently active in
# all running event loops.  {EventLoop: Task}
_current_tasks = {}


def _register_task(task):
    """Register a new task in asyncio as executed by loop."""
    _all_tasks.add(task)


def _enter_task(loop, task):
    current_task = _current_tasks.get(loop)
    if current_task is not None:
        raise RuntimeError(f"Cannot enter into task {task!r} while another "
                           f"task {current_task!r} is being executed.")
    _current_tasks[loop] = task


def _leave_task(loop, task):
    current_task = _current_tasks.get(loop)
    if current_task is not task:
        raise RuntimeError(f"Leaving task {task!r} does not match "
                           f"the current task {current_task!r}.")
    del _current_tasks[loop]


def _unregister_task(task):
    """Unregister a task."""
    _all_tasks.discard(task)


_py_register_task = _register_task
_py_unregister_task = _unregister_task
_py_enter_task = _enter_task
_py_leave_task = _leave_task


try:
    from _asyncio import (_register_task, _unregister_task,
                          _enter_task, _leave_task,
                          _all_tasks, _current_tasks)
except ImportError:
    pass
else:
    _c_register_task = _register_task
    _c_unregister_task = _unregister_task
    _c_enter_task = _enter_task
    _c_leave_task = _leave_task
