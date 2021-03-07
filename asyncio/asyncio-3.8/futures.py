"""A Future class similar to the one in PEP 3148."""

__all__ = (
    'Future', 'wrap_future', 'isfuture',
)

import concurrent.futures
import contextvars
import logging
import sys

from . import base_futures
from . import events
from . import exceptions
from . import format_helpers


isfuture = base_futures.isfuture


#######################################################################################################################
# Future有三种状态
# _PENDING: 进行中
# _CANCELLED: 已取消
# _FINISHED: 已结束
#######################################################################################################################
_PENDING = base_futures._PENDING
_CANCELLED = base_futures._CANCELLED
_FINISHED = base_futures._FINISHED


STACK_DEBUG = logging.DEBUG - 1  # heavy-duty debugging


class Future:
    """This class is *almost* compatible with concurrent.futures.Future.

    Differences:

    - This class is not thread-safe.

    - result() and exception() do not take a timeout argument and
      raise an exception when the future isn't done yet.

    - Callbacks registered with add_done_callback() are always called
      via the event loop's call_soon().

    - This class is not compatible with the wait() and as_completed()
      methods in the concurrent.futures package.

    (In Python 3.4 or later we may be able to unify the implementations.)
    """

    # 这些重要的变量定义在这里, 需要格外注意:
    # 1. 已实例化的对象, 在第一次访问 self._loop 时, 其实是访问到 Future._loop 的值.
    # 2. 已实例化的对象, 做赋值操作 self._loop = xxx 并不会影响 Future._loop 的值.
    # 从这两个表现来看, 变量定义在这里的作用和目的是:
    # 1. 可以充当默认值.
    # 2. 如果想要一劳永逸的话, 可以直接 Future._loop = events.get_event_loop() 那么后续的代码就不需要再每次都做获取的动作,
    #    这也就延申出来为什么在 __init__ 中会有 if loop is None 这个条件句, 就是为了支持一劳永逸的做法.
    # Class variables serving as defaults for instance variables.
    _state = _PENDING
    _result = None
    _exception = None
    _loop = None
    _source_traceback = None

    # This field is used for a dual purpose:
    # - Its presence is a marker to declare that a class implements
    #   the Future protocol (i.e. is intended to be duck-type compatible).
    #   The value must also be not-None, to enable a subclass to declare
    #   that it is not compatible by setting this to None.
    # - It is set by __iter__() below so that Task._step() can tell
    #   the difference between
    #   `await Future()` or`yield from Future()` (correct) vs.
    #   `yield Future()` (incorrect).
    _asyncio_future_blocking = False                # 该属性用于标识当前对象是一个Future对象.

    __log_traceback = False

    def __init__(self, *, loop=None):
        """Initialize the future.

        The optional event_loop argument allows explicitly setting the event
        loop object used by the future. If it's not provided, the future uses
        the default event loop.
        """
        if loop is None:
            # 由于 asyncio 是单线程循环机制, 所以这里获取 loop 就是获取那个正在运行的loop
            # TODO: events.get_event_loop() 源码说明待补充.
            self._loop = events.get_event_loop()
        else:
            # 如果在实例化之前已经给Future._loop单独设定过 loop 对象,
            # 那么这里就不会再去尝试获取, 而是直接拿来使用(写入到self._loop)实例中.
            self._loop = loop

        self._callbacks = []

        if self._loop.get_debug():
            self._source_traceback = format_helpers.extract_stack(
                sys._getframe(1))

    _repr_info = base_futures._future_repr_info

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__,
                                ' '.join(self._repr_info()))

    def __del__(self):
        if not self.__log_traceback:
            # set_exception() was not called, or result() or exception()
            # has consumed the exception
            return
        exc = self._exception
        context = {
            'message':
                f'{self.__class__.__name__} exception was never retrieved',
            'exception': exc,
            'future': self,
        }
        if self._source_traceback:
            context['source_traceback'] = self._source_traceback
        self._loop.call_exception_handler(context)

    @property
    def _log_traceback(self):
        return self.__log_traceback

    @_log_traceback.setter
    def _log_traceback(self, val):
        if bool(val):
            raise ValueError('_log_traceback can only be set to False')
        self.__log_traceback = False

    ###################################################################################################################
    # 对外开放的接口: 获取 self._loop 对象.
    # 如果 self._loop 尚未赋值, 则会报错.
    ###################################################################################################################
    def get_loop(self):
        """Return the event loop the Future is bound to."""
        loop = self._loop
        if loop is None:
            raise RuntimeError("Future object is not initialized.")
        return loop

    ###################################################################################################################
    # 对外开放的接口: 将当前 future 对象的状态改为 _CANCELLED, 并通知 loop 去执行 callbacks.
    #
    # 当 self._state != _PENDING 时, 表示它已经是 _CANCELLED 或者 _FINISHED 状态,
    # 那么就不需要再去更改状态, 也不需要再通知 loop 去执行 callbacks 了.
    ###################################################################################################################
    def cancel(self):
        """Cancel the future and schedule callbacks.

        If the future is already done or cancelled, return False.  Otherwise,
        change the future's state to cancelled, schedule the callbacks and
        return True.
        """
        self.__log_traceback = False
        if self._state != _PENDING:
            return False
        self._state = _CANCELLED
        self.__schedule_callbacks()
        return True

    ###################################################################################################################
    # 通知 loop 去执行 callbacks
    ###################################################################################################################
    def __schedule_callbacks(self):
        """Internal: Ask the event loop to call all callbacks.

        The callbacks are scheduled to be called as soon as possible. Also
        clears the callback list.
        """
        # 将所有 self._callbacks 中的成员, shadow-copy 到 callbacks 本地变量中.
        # 这么做是因为接下来要清空 self._callbacks 对象.
        #
        # shadow-copy 的定义:
        # A shallow copy constructs a new compound object and then (to the extent possible)
        # inserts references into it to the objects found in the original.
        # https://docs.python.org/3/library/copy.html
        #
        # shadow-copy 举例:
        # class Hole: pass
        # s = [Hole(), Hole(), Hole()]  # [<Hole object at 0x1820>, <Hole object at 0x1850>, <Hole object at 0x1970>]
        # b = s[:]                      # [<Hole object at 0x1820>, <Hole object at 0x1850>, <Hole object at 0x1970>]
        # 这里 shadow-copy 完成后, 两个列表的成员对象再内存中的位置是一样的,
        # 即: 对于 Hole 对象来说它内部的reference是递增的,
        #     当s[2]这个对象被删除之后python解释器也不会回收这个对象, 因为 b[2] 仍然在引用这个对象.
        # 这说明 s 和 b 不是同一个内存位置的变量, 但是引用着相同位置的Hole对象.
        #
        # s[2] = Hole()                 # [<Hole object at 0x1820>, <Hole object at 0x1850>, <Hole object at 0xE400>]
        # b                             # [<Hole object at 0x1820>, <Hole object at 0x1850>, <Hole object at 0x1970>]
        # 所以, 这里改变 s[2] 的 Hole 对象, 但是 b[2] 不会发生变化;
        callbacks = self._callbacks[:]
        if not callbacks:
            return

        # 清空 self._callbacks 集合
        self._callbacks[:] = []

        # 挨个将 callback 丢给 loop, 通知 loop 去执行 callback.
        for callback, ctx in callbacks:
            self._loop.call_soon(callback, self, context=ctx)

    ###################################################################################################################
    # 如果当前 future 的状态是 _CANCELLED 状态, 则返回 True, 否则返回 False.
    ###################################################################################################################
    def cancelled(self):
        """Return True if the future was cancelled."""
        return self._state == _CANCELLED

    # Don't implement running(); see http://bugs.python.org/issue18699

    ###################################################################################################################
    # 如果当前 future 的状态是 _CANCELLED 或 _FINISHED, 则返回True(表示已结束), 否则返回False(表示进行中).
    ###################################################################################################################
    def done(self):
        """Return True if the future is done.

        Done means either that a result / exception are available, or that the
        future was cancelled.
        """
        return self._state != _PENDING

    ###################################################################################################################
    # 如果当前 future 的状态是 _FINISHED 时, 才会返回结果.
    ###################################################################################################################
    def result(self):
        """Return the result this future represents.

        If the future has been cancelled, raises CancelledError.  If the
        future's result isn't yet available, raises InvalidStateError.  If
        the future is done and has an exception set, this exception is raised.
        """
        # 只要 self._state 不是 _FINISHED 状态, 那么都会报错.
        #
        # 当 self._state 是 _CANCELLED 状态时, 抛出 exceptions.CancelledError
        # 当 self._state 是 _PENDING 状态时, 抛出 exceptions.InvalidStateError('Result is not ready.')
        if self._state == _CANCELLED:
            raise exceptions.CancelledError
        if self._state != _FINISHED:
            raise exceptions.InvalidStateError('Result is not ready.')

        # 进入到这里表示, self._state == _FINISHED

        # 在返回结果之前, 先检查是否含有异常信息.
        self.__log_traceback = False
        if self._exception is not None:
            raise self._exception

        # 返回结果
        return self._result

    ###################################################################################################################
    # 如果当前 future 的状态是 _FINISHED 时, 才会返回异常结果.
    ###################################################################################################################
    def exception(self):
        """Return the exception that was set on this future.

        The exception (or None if no exception was set) is returned only if
        the future is done.  If the future has been cancelled, raises
        CancelledError.  If the future isn't done yet, raises
        InvalidStateError.
        """
        # 如果 self._state == _CANCELLED, 表示当前 future 的状态是已取消状态, 这里会直接抛异常, 而不是返回一个异常对象.
        if self._state == _CANCELLED:
            raise exceptions.CancelledError

        # 如果 self._state != _FINISHED, 表示当前 future 的状态可能是 _PENDING 或 _CANCELLED,
        # 这表示异常对象还没有设定(future.set_exception), 所以这里会直接抛异常, 而不是返回一个异常对象.
        if self._state != _FINISHED:
            raise exceptions.InvalidStateError('Exception is not set.')

        # 代码进入到这里表示, self._exception 已经被设定过了, 所以这里可以返回 self._exception 异常对象.
        self.__log_traceback = False
        return self._exception

    ###################################################################################################################
    # 只允许在当前 future 是 _PENDING 状态下添加callback回调函数到self._callbacks回调函数集合中.
    # 否则直接通知loop去执行这个callback回调函数, 而不是添加到self._callbacks回调函数集合中.
    ###################################################################################################################
    def add_done_callback(self, fn, *, context=None):
        """Add a callback to be run when the future becomes done.

        The callback is called with a single argument - the future object. If
        the future is already done when this is called, the callback is
        scheduled with call_soon.
        """
        # 不是 _PENDING 状态, 直接通知loop去执行这个函数.
        if self._state != _PENDING:
            self._loop.call_soon(fn, self, context=context)

        # 是 _PENDING 状态, 添加到self._callbacks回调函数集合中.
        #
        # 知识点:
        # context: contextvars.Context
        # 这是一个类似 mock.dict 的一个东西,
        # context是一个作用域, 它提供了run方法, 用于在该作用域中运行.
        # 该作用域从创建到结束, 整个过程中对外部变量的set仅在作用域声明周期内起作用,
        # 作用域结束后, 外部的变量不会发生变化. 举例:
        # from contextvars import ContextVar, copy_context
        #
        # var = ContextVar('var')           # 作用域外部
        # var.set('spam')                   # 作用域外部
        #
        # def main():
        #                                   # 进入作用域
        #     var.set('ham')                # 作用域内部:        更改 var 变量的值
        #     print('main: ', var.get())    # 作用域内部:        main: ham
        #                                   # 离开作用域
        #
        # ctx = copy_context()              # 创建作用域
        # ctx.run(main)                     # 由 context 执行 main 函数
        #
        # print('outside: ', var.get())     # 作用域外部:        outside: spam
        else:
            if context is None:
                context = contextvars.copy_context()
            self._callbacks.append((fn, context))

    # New method not in PEP 3148.

    ###################################################################################################################
    # 任何状态下的 future 都可以从 self._callbacks 中移除 callback 回调函数.
    # 返回值类型: int;
    # 返回值描述: 返回已移除数量;
    ###################################################################################################################
    def remove_done_callback(self, fn):
        """Remove all instances of a callback from the "call when done" list.

        Returns the number of callbacks removed.
        """
        # 这里采用筛选模式, 只留下那些不等于fn的回调函数.
        filtered_callbacks = [(f, ctx)
                              for (f, ctx) in self._callbacks
                              if f != fn]

        # self._callbacks: 总量集合
        # filtered_callbacks: 已筛选集合
        # 总量 - 已筛选 = 已移除
        #
        # 如果 已移除 == 0, 那么就不做任何操作, 直接返回 0
        # 如果 已移除 != 0, 那么就将 filtered_callbacks 覆盖掉 self._callbacks.
        removed_count = len(self._callbacks) - len(filtered_callbacks)
        if removed_count:
            self._callbacks[:] = filtered_callbacks
        return removed_count

    # So-called internal methods (note: no set_running_or_notify_cancel()).

    ###################################################################################################################
    # 只允许在当前 future 是 _PENDING 状态下设定结果信息.
    ###################################################################################################################
    def set_result(self, result):
        """Mark the future done and set its result.

        If the future is already done when this method is called, raises
        InvalidStateError.
        """
        # 不是 _PENDING 状态的 future 对象, 不能设定结果信息, 这里会抛异常.
        if self._state != _PENDING:
            raise exceptions.InvalidStateError(f'{self._state}: {self!r}')

        # 写入结果
        self._result = result
        # 将当前future状态设定为_FINISHED
        self._state = _FINISHED
        # 通知loop执行所有callbacks回调函数
        self.__schedule_callbacks()

    ###################################################################################################################
    # 只允许在当前 future 是 _PENDING 状态下设定异常信息.
    ###################################################################################################################
    def set_exception(self, exception):
        """Mark the future done and set an exception.

        If the future is already done when this method is called, raises
        InvalidStateError.
        """
        # 不是 _PENDING 状态的 future 对象, 不能设定异常信息, 这里会抛异常.
        if self._state != _PENDING:
            raise exceptions.InvalidStateError(f'{self._state}: {self!r}')

        # 参数 exception 如果类型是 type 的话, 表示它是一个类对象, 尚未被初始化, 这里期望的是一个已实例化的异常对象.
        if isinstance(exception, type):
            exception = exception()

        # Future对象不是一个generators对象, 所以不允许设定这个异常对象.
        if type(exception) is StopIteration:
            raise TypeError("StopIteration interacts badly with generators "
                            "and cannot be raised into a Future")

        # 写入异常对象
        self._exception = exception
        # 将当前future状态设定为_FINISHED
        self._state = _FINISHED
        # 通知loop执行所有callback回调函数.
        self.__schedule_callbacks()
        # TODO: 待补充
        self.__log_traceback = True

    def __await__(self):
        if not self.done():
            self._asyncio_future_blocking = True
            yield self  # This tells Task to wait for completion.
        if not self.done():
            raise RuntimeError("await wasn't used with future")
        return self.result()  # May raise too.

    __iter__ = __await__  # make compatible with 'yield from'.


# Needed for testing purposes.
_PyFuture = Future


def _get_loop(fut):
    # Tries to call Future.get_loop() if it's available.
    # Otherwise fallbacks to using the old '_loop' property.
    try:
        get_loop = fut.get_loop
    except AttributeError:
        pass
    else:
        return get_loop()
    return fut._loop


def _set_result_unless_cancelled(fut, result):
    """Helper setting the result only if the future was not cancelled."""
    if fut.cancelled():
        return
    fut.set_result(result)


def _convert_future_exc(exc):
    exc_class = type(exc)
    if exc_class is concurrent.futures.CancelledError:
        return exceptions.CancelledError(*exc.args)
    elif exc_class is concurrent.futures.TimeoutError:
        return exceptions.TimeoutError(*exc.args)
    elif exc_class is concurrent.futures.InvalidStateError:
        return exceptions.InvalidStateError(*exc.args)
    else:
        return exc


def _set_concurrent_future_state(concurrent, source):
    """Copy state from a future to a concurrent.futures.Future."""
    assert source.done()
    if source.cancelled():
        concurrent.cancel()
    if not concurrent.set_running_or_notify_cancel():
        return
    exception = source.exception()
    if exception is not None:
        concurrent.set_exception(_convert_future_exc(exception))
    else:
        result = source.result()
        concurrent.set_result(result)


def _copy_future_state(source, dest):
    """Internal helper to copy state from another Future.

    The other Future may be a concurrent.futures.Future.
    """
    assert source.done()
    if dest.cancelled():
        return
    assert not dest.done()
    if source.cancelled():
        dest.cancel()
    else:
        exception = source.exception()
        if exception is not None:
            dest.set_exception(_convert_future_exc(exception))
        else:
            result = source.result()
            dest.set_result(result)


def _chain_future(source, destination):
    """Chain two futures so that when one completes, so does the other.

    The result (or exception) of source will be copied to destination.
    If destination is cancelled, source gets cancelled too.
    Compatible with both asyncio.Future and concurrent.futures.Future.
    """
    if not isfuture(source) and not isinstance(source,
                                               concurrent.futures.Future):
        raise TypeError('A future is required for source argument')
    if not isfuture(destination) and not isinstance(destination,
                                                    concurrent.futures.Future):
        raise TypeError('A future is required for destination argument')
    source_loop = _get_loop(source) if isfuture(source) else None
    dest_loop = _get_loop(destination) if isfuture(destination) else None

    def _set_state(future, other):
        if isfuture(future):
            _copy_future_state(other, future)
        else:
            _set_concurrent_future_state(future, other)

    def _call_check_cancel(destination):
        if destination.cancelled():
            if source_loop is None or source_loop is dest_loop:
                source.cancel()
            else:
                source_loop.call_soon_threadsafe(source.cancel)

    def _call_set_state(source):
        if (destination.cancelled() and
                dest_loop is not None and dest_loop.is_closed()):
            return
        if dest_loop is None or dest_loop is source_loop:
            _set_state(destination, source)
        else:
            dest_loop.call_soon_threadsafe(_set_state, destination, source)

    destination.add_done_callback(_call_check_cancel)
    source.add_done_callback(_call_set_state)


def wrap_future(future, *, loop=None):
    """Wrap concurrent.futures.Future object."""
    if isfuture(future):
        return future
    assert isinstance(future, concurrent.futures.Future), \
        f'concurrent.futures.Future is expected, got {future!r}'
    if loop is None:
        loop = events.get_event_loop()
    new_future = loop.create_future()
    _chain_future(future, new_future)
    return new_future


try:
    import _asyncio
except ImportError:
    pass
else:
    # _CFuture is needed for tests.
    Future = _CFuture = _asyncio.Future
