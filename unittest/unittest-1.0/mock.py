# mock.py
# Test tools for mocking and patching.
# Maintained by Michael Foord
# Backport for other versions of Python available from
# https://pypi.org/project/mock

#######################################################################################################################
# metaclass
#######################################################################################################################
#
# 默认情况下 class 对象的创建, Python使用的是 type 内置函数来完成创建工作.
#
# type 有两种使用方法:
# 1). type(obj)                                         返回obj对象的类型
# 2). type(string, (BaseClass, ), {"attr": "value"})    Python创建class对象(不是实例化)采用这种方式.
#
# metaclass 是python提供的一种方式, 让开发者来完成对象的创建工作(把 type(string,(), {}) 这个指令留给开发者来完成).
# class MetaOne(type): pass
# class ExampleOne(metaclass=MetaOne): pass
# 有两个注意事项:
# 1. MetaOne 必须继承的是type对象.
# 2. ExampleOne 必须指定metaclass参数, 才能表示ExampleOne类的实例化过程交给MetaOne来完成.
#
# metaclass 的生命周期, 举例说明:
# class MetaA(type):
#
#     def __new__(cls, *args, **kwargs):
#         print("MetaA: __new__")
#         return super(MetaA, cls).__new__(cls, *args, **kwargs)  # 创建未实例化的类, 等同于: return type("Hello", (), {})
#
#     def __init__(cls, *args, **kwargs):
#         print("MetaA: __init__")
#
#     def __call__(cls, *args, **kwargs):
#         print("MetaA: __call__: begin")
#         ss = super(MetaA, cls).__call__(*args, **kwargs)        # 实例化Hello类, 等同于 ss = Hello(*args, **kwargs)
#         print("MetaA: __call__: end")
#
#     def good(cls):                                              # 由于Hello并不是继承MetaA, 所以Hello对象不拥有这个方法.
#         print("MetaA good")
#
#
# class Hello(metaclass=MetaA):
#
#     def __new__(cls, *args, **kwargs):
#         print("Hello: __new__")
#         return super(Hello, cls).__new__(cls, *args, **kwargs)
#
#     def __init__(self):
#         print("Hello: __init__")
#
#
# h = Hello()
#
#
# Output:
# MetaA: __new__
# MetaA: __init__
# MetaA: __call__: begin        这里开始执行 Hello 的 __new__ 和 __init__, 称为实例化
# Hello: __new__
# Hello: __init__
# MetaA: __call__: end          这里退出和销毁Hello对象.
#
#######################################################################################################################


#######################################################################################################################
# generator
#######################################################################################################################
# 在python2中, 在函数中使用了yield关键字, 这个函数就会被Python视为是一个generator对象.
# generator对象可以有两个通用的使用场景: producer 和 consumer.
# 当使用yield当作函数(generator)单次返回值时, 它是一个producer.
# 当使用yield在函数(generator)内赋值给一个变量, 它就是一个consumer, 这时它依赖外部使用 s.send(ASCII-characters) 来传递消息给它.
#######################################################################################################################


#######################################################################################################################
# coroutine
#######################################################################################################################
# 在python2中, generator有两个状态, just-started status 和 coroutine status
# 刚完成赋值的generator对象是 just-started 状态, 例如:
# def hello():
#     print("start")
#     count = 0
#     while count < 20:
#         print("running")
#         yield count
#         count += 1
#     print("stop")
#
# h = hello()               # just-started
# next(h)                   # coroutine: generator is ready to produce something.
#                                        or        is ready to consum something.
# output:
# start
# running
#
#
# 除了手动进入coroutine状态, 另一种更便捷的方式进入coroutine状态是使用装饰器.
# def coroutine(func):
#     def wrapper(*args, **kwargs):
#         ss = func(*args, **kwargs)
#         next(ss)
#         return ss
#     return wrapper
#
#
# @coroutine
# def hello():
#     print("start")
#     count = 0
#     while count < 20:
#         print("running")
#         yield count
#         count += 1
#     print("stop")
#
#
# h = hello()                               # 省略了手动next(h)步骤, 由coroutine装饰器来负责进入coroutine状态.
#
# output:
# start
# running
#######################################################################################################################


#######################################################################################################################
# coroutine pipeline
#######################################################################################################################
# linux 的命令行的多个命令可以使用管道(pipeline)来配合完成数据的实时筛选,
# 例如: cat xx.log | grep "error" ; 这条命令的意思是从文件开头处开始读取数据, 每读取到一行就即时传递这一行数据给grep命令进行筛选,
#                                   如果匹配到数据那么就打印出来, 如果没有匹配到就不打印任何信息.
#
# 用coroutine来开发相同效果的是实现.
# import time
#
#
# def coroutine(func):
#     def wrapper(*args, **kwargs):
#         ss = func(*args, **kwargs)
#         next(ss)
#         return ss
#     return wrapper
#
#
# @coroutine
# def cat(file_obj, target):
#     while True:
#         line = file_obj.readline()
#         if not line:
#             time.sleep(0.1)
#             continue
#         target.send(line)
#
#
# @coroutine
# def printer():
#     while True:
#         line = yield
#         print(line)
#
#
# @coroutine
# def grep(pattern, target):
#     while True:
#         line = yield
#         if pattern in line:
#             target.send(line)
#
#
# if __name__ == '__main__':
#     with open("xx.log") as f:
#         cat(f, grep("error", printer()))
#
#######################################################################################################################


#######################################################################################################################
# Asynchronous(异步)
#######################################################################################################################
# 在python2中, 异步是一个模糊不定、难以摸透的概念和技术特征.
# 三方库提供的concurrency.futures异步解决方案, 它提供了Future对象用于在
# 异步中传递和暂存结果和状态, 同时它也提供了线程池和进程池解决方案;
# 以前在研究tornado的时候认为, 只要使用下面两种方式解决io型请求和密集计算型请求, 就能发挥出tornado这个异步框架的威力了.
# 1). 堵塞的数据库请求用线程池的coroutine来包裹,
# 2). 密集型的计算用进程池的coroutine来包裹.
# 直到最近看了asyncio的源码, 才发现上面的线程池和进程池其实是一种迫不得已的解决办法,
# 它存在的目的和意义是: 当你实在无法用异步来处理堵塞时, 再来考虑使用线程池或进程池来弥补框架的缺陷.
#
# synchronous(同步):
# 首先需要明确的一点是, 在异步概念出现之前, 所有的代码编写方式都是一行一个指令,
# 解释器和编译器也是按照一行一个指令来完成代码的执行工作.
# 在synchronous模式下, 解决并发的办法是使用线程或进程, 然而当并发量较大时线程或进程
# 的启动/销毁/代码切换执行都比较消耗cpu和内存和响应时间.
#
# 为什么synchronous模式下需要使用线程或进程才能解决并发问题?
# 以webserver为例, 如果有两个请求在同一时间向webserver发送请求, 那么webserver通常情况下有两种解决方案:
# 方案1: 先处理一个请求, 然后再处理另外一个请求.               python的wsgi就是以这种方式运行
# 方案2: 每个请求拉起一个线程, 同时并发处理两个请求.           python的django就是以这种方式运行
#
# 方案1面临的问题:
# 当第一个请求如果因为某种原因发生了堵塞, 例如: 数据库查询慢, 导致这个请求堵塞了20秒,
# 那么第二个请求将会一直处于等待状态, 直到第一个请求处理完毕, webserver才能处理第二个请求.
# 这个过程其实并没有消耗cpu也没有消耗内存, 但是服务器就是处理不过来这两个请求.
#
# 方案2面临的问题:
# 方案2可以解决方案1的问题;
# 方案2的缺点是线程或进程的启动本身是消耗内存的(python:4K, java:1M), 操作系统的内核对线程的计算切换需要消耗cpu计算.
# 方案2的问题在小范围使用时不会有任何问题, 但是在高并发场景下可能会出现系统资源不足而产生一些不可预料的异常错误.
#
# asynchronous(异步)
# 前面两个问题, 其实都不是编程语言的问题, 因为瓶颈并不在编程语言本身;
# 以python为例, 在一台i5的笔记本电脑上运行, python可以每秒执行两千万行简单代码(rust和c++每秒可以执行2亿行简单代码),
# 所以理论上来说一个webserver可以使用单线程来处理所有请求(c10k问题), 只需要一种神奇的方式能够解决
# 那些 "数据库查询慢"/"事务执行时间长" 的问题; 异步其实就是为了解决这个问题的最终办法.
#
# 那什么是异步?
# 异步就是当遇到 "可能需要等待" 的地方, 将其挂起(由编程语言或框架提供机制, 例如: yield或await),
# 挂起后框架继续去处理其他请求, 当 "等待" 结束后通知框架回调执行后续代码.
# 通过这种方式, 框架几乎可以持续处理无限的请求.
#
# 依旧描述的含糊不清, 它的运行机制是什么, 为什么可以这么神奇?
# 1. 异步通常由一个框架来提供运行机制.
# 2. 异步框架负责while无限循环来处理请求, 所有的请求通常都会对应一个handler, 如果没有找到对应的handler那么就不处理这个请求.
# 3. 这个handler通常来说就是开发者需要填充代码的函数, 可以再这个handler中写一些满足业务的代码.
#    代码中需要 "等待" 的地方使用 await 或者 yield 配合三方库的异步客户端来挂起当前handler.
# 4. 三方库的异步客户端与异步框架沟通的唯一方式就是通过Future对象的状态和add_done_callback来流转,
#    当异步客户端正在处理堵塞请求时, Future的状态时Pending, 当处理完堵塞请求后, 会将Future的状态设定为Finished,
#    并且通过add_done_callback的回调去通知ioloop将当前future添加到ioloop._ready集合中.
# 5. 异步框架的while负责处理那些ioloop._ready集合中的Future对象, 并唤醒对应的handler.
#
#######################################################################################################################


#######################################################################################################################
# asyncio Awaitable Object
#
# Awaitables: There are three main types of awaitable objects: coroutines, Tasks, and Futures.
# 划重点: 声明了 async 关键字的函数都会具备 __await__ 属性, 表明它是一个 awaitable 对象.
#
# 1. Coroutine
#    声明了 async 关键字的函数, 或者是迭代循环; 都被称为 Coroutine;
#    例如, 下面这个就是一个最简单版本的coroutine函数.
#
#    async def hello():
#        return 42
#
#    print(hello)                                   <function hello at 0x00000245679F1820>
#    s = hello()
#    print(s)                                       <coroutine object hello at 0x000002456799EE40>
#    print(dir(s))                                  具备了 __await__ 属性的对象, 都是 awaitable 对象.
#
#    备注: 这个hello函数里面不可以使用 await 42; 因为 42 是一个常量对象, 不是awaitable对象;
#          然而并不是 hello 函数内不可以使用 await , 而是 await 之后等待那些 awaitable 对象;
#
# 2. Task
#    Task 是由 asyncio 框架提供的一个类对象, 它继承了Future并再基于此的基础上
#    提供了一套符合 asyncio 运行机制的功能, 使其能够满足异步运行机制.
#
# 3. Future
#    Future 是一个状态/数据暂存对象, 并包含add_done_callback功能.
#    Future 对象将传统的异步(例如: bs架构+ajax通知回调模式)抽象成一个可编程并且稍微增加耦合度的对象.
#
#
# 在 Python2 中, 并没有官方承认的 coroutine 对象; 前面说的 coroutine 和 coroutine pipeline ,
# 打印出来它们依旧是 generator, 区别在于状态: just-started 和 非just-started(即: coroutine).
#
# 在 Python3 中, 虽然asyncio提供了coroutine装饰器进行补充, 但打印出来依旧是generator,
# asyncio的解决方案是给generator对象增加一个_is_coroutine属性用于标记它是一个coroutine对象;
# asyncio.iscoroutine 和 asyncio.iscoroutinefunction 都会检查,
# 如果一个函数具有_is_coroutine属性, 那么就是一个coroutine对象; 举例:
# async版本
# import asyncio
#
# async def nested():
#     return 42
#
# async def main():
#     ss = nested()
#     task = asyncio.create_task(ss)
#
#     zz = await task
#     print("zz: ", zz)                             # zz: 42
#
# asyncio.run(main())
#
# generator版本
# import asyncio
#
# @asyncio.coroutine
# def hello():
#     yield from asyncio.sleep(1)
#     return 42
#
# async def main():
#     ss = hello()
#     task = asyncio.create_task(ss)
#
#     zz = await task
#     print("zz: ", zz)                              # zz: 42
#
# asyncio.run(main())
#
#######################################################################################################################
__all__ = (
    'Mock',
    'MagicMock',
    'patch',
    'sentinel',
    'DEFAULT',
    'ANY',
    'call',
    'create_autospec',
    'AsyncMock',
    'FILTER_DIR',
    'NonCallableMock',
    'NonCallableMagicMock',
    'mock_open',
    'PropertyMock',
    'seal',
)


__version__ = '1.0'

import asyncio
import contextlib
import io
import inspect
import pprint
import sys
import builtins
from types import CodeType, ModuleType, MethodType
from unittest.util import safe_repr
from functools import wraps, partial


_builtins = {name for name in dir(builtins) if not name.startswith('_')}

FILTER_DIR = True

# Workaround for issue #12370
# Without this, the __class__ properties wouldn't be set correctly
_safe_super = super


#######################################################################################################################
# _is_async_obj(obj)
# 该函数用于判断obj(已实例化的对象)是不是一个async对象.
#
# asyncio.iscoroutinefunction 用于判断一个未执行赋值的函数是不是定义了async def
# inspect.isawaitable     1.已执行赋值的函数是不是一个 async def 对象.    isinstance(object, types.CoroutineType)
#                         2.已执行赋值的函数是不是一个generator对象.      isinstance(object, types.GeneratorType)
#                         3.已执行赋值的函数是不是一个abc.Awaitable对象.  isinstance(object, collections.abc.Awaitable)
#
#######################################################################################################################
def _is_async_obj(obj):
    if _is_instance_mock(obj) and not isinstance(obj, AsyncMock):
        return False
    return asyncio.iscoroutinefunction(obj) or inspect.isawaitable(obj)


#######################################################################################################################
# _is_async_func(func)
# 该函数用于判断func(未赋值的函数)是不是一个async函数.
#
# getattr(func, '__code__', None)  未执行的函数对象拥有 __code__ 属性, 已执行的函数没有 __code__ 属性.
# asyncio.iscoroutinefunction      根据函数func.__code__.co_flags 来判断是不是一个coroutine.
#
#######################################################################################################################
def _is_async_func(func):
    if getattr(func, '__code__', None):
        return asyncio.iscoroutinefunction(func)
    else:
        return False


#######################################################################################################################
# _is_instance_mock(obj)
# 该函数用于判断obj(已实例化的对象)是不是一个mock对象.
#
# issubclass的第一个参数要求必须是一个 class , 所以如果传递的是一个未实例化的 class,
# 是也是可以做判断的, 但这样通常判断通常没有意义, 因为未实例化的对象不符合判断场景.
#
# 然而实例化过后的对象(它是一个instanced对象), 并不符合issubclass的参数类型(class)要求,
# 所以这里需要使用type(obj)将它的class调出来(<class 'unittest.mock.Mock'>).
#
# 由于所有的mock类都继承了NonCallableMock, 所以只要使用isusbclass判断
# 这个对象是不是NonCallableMock的子类, 就可以识别出它是不是一个mock对象.
#
# 实例化对象和为实例化对象的类型区别:
# class Hollo(object): pass
# ss = Hollo()
#
# print(ss)                            # <__main__.Hollo object at 0x00000188EB75A820>      这是实例化对象
# print(Hello)                         # <class '__main__.Hollo'>                           这是未实例化对象
# print(type(ss))                      # <class '__main__.Hollo'>                           这是未实例化对象
#######################################################################################################################
def _is_instance_mock(obj):
    # can't use isinstance on Mock objects because they override __class__
    # The base class for all mocks is NonCallableMock
    return issubclass(type(obj), NonCallableMock)


#######################################################################################################################
# _is_exception
# 该函数用于判断一个对象是不是一个Exception类型的对象:
# 内置的Exception类在这里: https://docs.python.org/3/library/exceptions.html
#
# isinstance(obj, BaseException)   判断obj这个对象是不是一个BaseException对象.
# isinstance(obj, type)            判断obj这个对象是不是一个type对象.
# isinstance(obj, BaseException)   判断obj这个对象是不是一个BaseException的子类.
#
# 这里三个条件联合在一起做判断,
# 如果obj是一个BaseException那么就不再做后续的判断直接返回True, 结束;
# 如果obj不是一个BaseException, 那么就往下判断;
# 如果obj是一个type(由于dict,list这些内置类型也是type类型), 单独的type并不能证明它是Exception, 还需要往下判断;
# 如果obj是一个type同时也是BaseException的子类(派生类), 那么就返回True, 结束;
# 如果obj是一个type但不是一个BaseException的子类, 那么就返回False, 结束;
#######################################################################################################################
def _is_exception(obj):
    return (
        isinstance(obj, BaseException) or
        isinstance(obj, type) and issubclass(obj, BaseException)
    )


#######################################################################################################################
# _extract_mock
# 该函数用于提取obj(已实例化的对象)的mock属性(obj.mock), 如果obj是一个Autospecced function, 那么它就应该拥有mock属性.
# 如果参数obj没有mock属性, 那么就返回obj对象.
# 如果参数obj有mock属性, 那么就返回obj.mock对象.
#######################################################################################################################
def _extract_mock(obj):
    # Autospecced functions will return a FunctionType with "mock" attribute
    # which is the actual mock object that needs to be used.
    if isinstance(obj, FunctionTypes) and hasattr(obj, 'mock'):
        return obj.mock
    else:
        return obj


#######################################################################################################################
# inspect.signature(func)
# 主要是采集函数的参数信息: 参数名, 参数类型(注解);
# signature(签名) == 函数名 + 参数名 + 参数类型(注解);
# 详细说明参考: https://docs.python.org/3/library/inspect.html#inspect.Signature
#             https://docs.python.org/3/library/inspect.html#inspect.Parameter
#
#
# _get_signature_object(func, as_instance, eat_self)
# 该函数用于提取 func 的签名信息(函数名 + 参数名 + 参数类型注解).
# 返回值: 如果 func 参数不符合提取signature的条件, 那就返回None;
#
# 什么是符合signature的条件呢?
# 1). func必须是一个函数(callable或者具有 .__call__ 属性表明它是一个callable对象).
# 2). 如果 func 不是一个函数, 那必须是一个类对象(未实例化的), 并且参数 as_instance 必须未False,
#     _get_signature_object会尝试提取 class.__init__ 的签名(使用 functools.partial 来包裹, 即eat_self).
#######################################################################################################################
def _get_signature_object(func, as_instance, eat_self):
    """
    Given an arbitrary, possibly callable object, try to create a suitable
    signature object.
    Return a (reduced func, signature) tuple, or None.
    """
    if isinstance(func, type) and not as_instance:
        # If it's a type and should be modelled as a type, use __init__.
        func = func.__init__
        # Skip the `self` argument in __init__
        eat_self = True
    elif not isinstance(func, FunctionTypes):
        # If we really want to model an instance of the passed type,
        # __call__ should be looked up, not __init__.
        try:
            func = func.__call__
        except AttributeError:
            return None
    if eat_self:
        sig_func = partial(func, None)
    else:
        sig_func = func
    try:
        return func, inspect.signature(sig_func)
    except ValueError:
        # Certain callable types are not supported by inspect.signature()
        return None


#######################################################################################################################
# _check_signature(func, mock, skipfirst, instance=False)
# 该函数用于为 type(mock) 类添加 _mock_check_sig 和 __signature__ 属性.
#          为 checksig 添加 func 属性.
# TODO: 作用和目的暂时还不直到, 待后续补充.
#
# 知识点补充:
# type(mock) 返回的是 <class 'unittest.mock.Mock'> 类对象, 这个类对象只属于这个mock.
# 也就是说 type(mock) != unittest.mock.Mock.
#
# 因此 type(mock)._mock_check_sig = checksig 并不是作用再 unittest.mock.Mock 类对象中,
# 而是作用在基于这个mock实例对象上.
#######################################################################################################################
def _check_signature(func, mock, skipfirst, instance=False):
    sig = _get_signature_object(func, instance, skipfirst)
    if sig is None:
        return
    func, sig = sig
    def checksig(self, /, *args, **kwargs):
        sig.bind(*args, **kwargs)
    _copy_func_details(func, checksig)
    type(mock)._mock_check_sig = checksig
    type(mock).__signature__ = sig


#######################################################################################################################
# _copy_func_details(func, funcopy)
# 该函数用于将 func 函数对象的属性(仅下面这两个属性, 不含func.__dict__), 复制一份给 funcopy 函数对象.
#######################################################################################################################
def _copy_func_details(func, funcopy):
    # we explicitly don't copy func.__dict__ into this copy as it would
    # expose original attributes that should be mocked
    for attribute in (
        '__name__', '__doc__', '__text_signature__',
        '__module__', '__defaults__', '__kwdefaults__',
    ):
        try:
            setattr(funcopy, attribute, getattr(func, attribute))
        except AttributeError:
            pass


#######################################################################################################################
# _callable
# 调用该函数来判断obj是不是一个可调用对象.
#
# 这段代码示例来源于: Lib/types.py#51行位置
# class _C:
#     def _m(self): pass
#
# ClassType = type(_C)                    # _C是一个未实例化的类对象, type(_C)生成一个类类型.
# UnboundMethodType = type(_C._m)         # _C._m是一个为实例化的方法, type(_C._m)生成一个未绑定的方法.
# _x = _C()                               # _x 是一个_C的实例化对象
# InstanceType = type(_x)                 # type(_x) 是一个类实例化类型.
# MethodType = type(_x._m)                # type(_x._m) 是一个实例化方法类型.
#
#
# isinstance(obj, type):
# list, dict, NameError, ValueError 这些都是type, 都是callable对象.
#
# isinstance(obj, (staticmethod, classmethod, MethodType)) 这些都是判断obj是不是一个类对象中的方法.
#
# getattr(obj, '__call__', None) is not None 是判断obj是不是一个独立的函数.
#######################################################################################################################
def _callable(obj):
    if isinstance(obj, type):
        return True
    if isinstance(obj, (staticmethod, classmethod, MethodType)):
        return _callable(obj.__func__)
    if getattr(obj, '__call__', None) is not None:
        return True
    return False


#######################################################################################################################
# _is_list(obj)
# 该函数用于判断 obj 是不是一个列表或元组类型.
#######################################################################################################################
def _is_list(obj):
    # checks for list or tuples
    # XXXX badly named!
    return type(obj) in (list, tuple)


#######################################################################################################################
# _instance_callable(obj)
# 该函数用于判断 obj 是不是一个可以调用的对象:
# 1. 如果 obj 不是type类型, 那么就去看看它的属性里面是否包含 __call__, 包含 __call__ 表示这是一个可以调用的方法或函数.
# 2. 如果 obj 是type类型, 那么mro里面找, 如果全部都没有 __call__ 那么就返回失败, 如果任意一个有__call__那么就返回True.
#######################################################################################################################
def _instance_callable(obj):
    """Given an object, return True if the object is callable.
    For classes, return True if instances would be callable."""
    if not isinstance(obj, type):
        # already an instance
        return getattr(obj, '__call__', None) is not None

    # *could* be broken by a class overriding __mro__ or __dict__ via
    # a metaclass
    for base in (obj,) + obj.__mro__:
        if base.__dict__.get('__call__') is not None:
            return True
    return False


#######################################################################################################################
# _set_signature(mock, original, instance=False)
# 该函数的作用是按照original的参数签名来创建一个新的mock对象,
# 并且将新的mock对象作为第一个参数mock对象委托对象(意思是处理mock事务先交给新的mock对象处理, 然后再到第一个参数mock对象).
#######################################################################################################################
def _set_signature(mock, original, instance=False):
    # creates a function with signature (*args, **kwargs) that delegates to a
    # mock. It still does signature checking by calling a lambda with the same
    # signature as the original.

    # 获取 original 的 signature.
    skipfirst = isinstance(original, type)
    result = _get_signature_object(original, instance, skipfirst)
    if result is None:
        return mock
    func, sig = result

    # 重点:
    # 这个函数并没有返回值, 所以它的目的并不是产生或者绑定内部属性,
    # 而是尝试验证传递的参数与函数本身的参数要求是否吻合(是否符合实例化或执行的条件).
    def checksig(*args, **kwargs):
        sig.bind(*args, **kwargs)

    _copy_func_details(func, checksig)

    # 获取original的函数名称.
    name = original.__name__
    if not name.isidentifier():
        name = 'funcopy'

    # context的作用是一个scope
    context = {'_checksig_': checksig, 'mock': mock}

    # 定义一个函数, 该函数返回mock对象.
    src = """def %s(*args, **kwargs):
    _checksig_(*args, **kwargs)
    return mock(*args, **kwargs)""" % name

    # 创建一个函数, 并且写入到context中.
    exec (src, context)

    # 从context中提取出函数.
    funcopy = context[name]

    # 将mock的方法和属性, 写入到funcopy中,
    # 并且将funcopy作为mock的委托对象.
    _setup_func(funcopy, mock, sig)

    return funcopy


#######################################################################################################################
# _setup_func(funcopy, mock, sig)
# 该函数主要是将 mock 对象的属性和方法写入到funcopy中, 并且将funcopy作为mock的委托对象.
#######################################################################################################################
def _setup_func(funcopy, mock, sig):
    funcopy.mock = mock

    def assert_called_with(*args, **kwargs):
        return mock.assert_called_with(*args, **kwargs)
    def assert_called(*args, **kwargs):
        return mock.assert_called(*args, **kwargs)
    def assert_not_called(*args, **kwargs):
        return mock.assert_not_called(*args, **kwargs)
    def assert_called_once(*args, **kwargs):
        return mock.assert_called_once(*args, **kwargs)
    def assert_called_once_with(*args, **kwargs):
        return mock.assert_called_once_with(*args, **kwargs)
    def assert_has_calls(*args, **kwargs):
        return mock.assert_has_calls(*args, **kwargs)
    def assert_any_call(*args, **kwargs):
        return mock.assert_any_call(*args, **kwargs)
    def reset_mock():
        funcopy.method_calls = _CallList()
        funcopy.mock_calls = _CallList()
        mock.reset_mock()
        ret = funcopy.return_value
        if _is_instance_mock(ret) and not ret is mock:
            ret.reset_mock()

    funcopy.called = False
    funcopy.call_count = 0
    funcopy.call_args = None
    funcopy.call_args_list = _CallList()
    funcopy.method_calls = _CallList()
    funcopy.mock_calls = _CallList()

    funcopy.return_value = mock.return_value
    funcopy.side_effect = mock.side_effect
    funcopy._mock_children = mock._mock_children

    funcopy.assert_called_with = assert_called_with
    funcopy.assert_called_once_with = assert_called_once_with
    funcopy.assert_has_calls = assert_has_calls
    funcopy.assert_any_call = assert_any_call
    funcopy.reset_mock = reset_mock
    funcopy.assert_called = assert_called
    funcopy.assert_not_called = assert_not_called
    funcopy.assert_called_once = assert_called_once
    funcopy.__signature__ = sig

    mock._mock_delegate = funcopy

#######################################################################################################################
# _setup_async_mock(mock)
# 该函数主要是为mock参数添加一些标识(异步的)属性和方法.
#######################################################################################################################
def _setup_async_mock(mock):
    # 为异步mock对象添加 _is_coroutine 属性.
    # 为异步mock对象添加 await_count , await_args, await_args_list 属性(并提供初始化值).
    mock._is_coroutine = asyncio.coroutines._is_coroutine
    mock.await_count = 0
    mock.await_args = None
    mock.await_args_list = _CallList()

    # Mock is not configured yet so the attributes are set
    # to a function and then the corresponding mock helper function
    # is called when the helper is accessed similar to _setup_func.
    def wrapper(attr, /, *args, **kwargs):
        # TODO: 这里没看懂, 为什么要写mock.mock?
        #       还有getattr(mock, 'assert_awaited')会报错: Attributes cannot start with 'assert' or 'assret'.
        #       所以这里待后续debug后再补充.
        return getattr(mock.mock, attr)(*args, **kwargs)

    # 为mock对象添加七项属性.
    for attribute in ('assert_awaited',
                      'assert_awaited_once',
                      'assert_awaited_with',
                      'assert_awaited_once_with',
                      'assert_any_await',
                      'assert_has_awaits',
                      'assert_not_awaited'):

        # setattr(mock, attribute, wrapper) causes late binding
        # hence attribute will always be the last value in the loop
        # Use partial(wrapper, attribute) to ensure the attribute is bound
        # correctly.
        setattr(mock, attribute, partial(wrapper, attribute))


#######################################################################################################################
# _is_magic(name)
# 该函数用于判断 name 参数 是不是一个魔法方法, 例如:
# '__dir__'[2:-2] 等于 'dir'
# '__%s__' % dir 等于 '__dir__'
# 两个相比较是相等的, 表示name参数就是一个前后两下划线的魔法方法.
#######################################################################################################################
def _is_magic(name):
    return '__%s__' % name[2:-2] == name


#######################################################################################################################
#
# _SentinelObject
# 该类对象用于存储一个字符串名字, 备注上说是一个命名唯一的哨兵对象,
# 我的理解是它起到一个枚举成员(也是起到唯一)的作用.
#
# 至于 __repr__ 中, 为什么返回: "sentinel.%s" % self.name
# 我猜测是为了于下面的这几组变量保持统一:
# sentinel = _Sentinel()
# DEFAULT = sentinel.DEFAULT
# _missing = sentinel.MISSING
# _deleted = sentinel.DELETED
#
#######################################################################################################################
class _SentinelObject(object):
    "A unique, named, sentinel object."
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'sentinel.%s' % self.name

    ###################################################################################################################
    # __reduce__
    # 是一个object的内置方法(也被称为魔法方法), 它存在的目的是为了服务pickle.dumps和pickle.loads函数.
    # __reduce__ 返回值必须按照特定规则来定义: 要么返回一个字符串, 要么返回一个元组.
    #                                        当返回一个字符串时, 这个字符串必须是当前文件全局变量中能找到并被import的变量名.
    #                                        当返回一个元组时, 第一个参数必须是一个callable对象,
    #                                        第二个参数是一个元组(用来传递参数给第一个参数对象).
    # 返回值规则参考这里:                     https://docs.python.org/3/library/pickle.html#object.__reduce__
    #
    # pickle.dump  可以将一个对象序列化成字符串, 这个字符串可以保存到文本中;
    # pickle.dumps 可以将一个对象序列化成字符串, 这个字符串可以保存到内存中(变量);
    # pickle.load  可以从文件中加载这段序列化的文本, 并将其re-create/re-load成一个对象.
    # pickle.loads 可以将一个字符串变量, re-create/re-load成一个对象.
    #
    # pickle.dump 大致保存了文件的路径, 模块和对象名称;
    # pickle.load 大致使用了import来根据路径/模块名称/变量名来完成对象创建.
    #
    # TODO: 由于整个mock.py文件中都没有使用到pickle来加载sentinel对象, 所以暂时不明白它的必要性, 后续需要追踪测试用例去理解.
    ###################################################################################################################
    def __reduce__(self):
        return 'sentinel.%s' % self.name


#######################################################################################################################
#
# _Sentinel
# 该类是一个容器, 用于存储 _SentinelObject 集合.
# 它的作用是提供一组类似于枚举的对象.
#
#######################################################################################################################
class _Sentinel(object):
    """Access attributes to return a named object, usable as a sentinel."""
    def __init__(self):
        self._sentinels = {}

    ###################################################################################################################
    # __getattr__
    # 是一个object的内置方法(也被称为魔法方法), 它的作用是当调用了不存在的方法或属性时会触发__getattr__方法.
    #
    # 当前函数作用:
    # 当前_Sentinel类对象除了 __init__, __getattr__, __reduce__ 这三个内置方法(外部不可调用)之外, 并没有定义任何方法.
    # 也就是说: sentinel.DEFAULT, sentinel.MISSING, sentinel.DELETED 都会触发 __getattr__ 方法.
    # _Sentinel内部维护了一个self._sentinels字典, 用来当作名字唯一的_SentinelObject对象容器.
    #
    # 当前函数返回值:
    # 根据参数给定的名字, 从 self._sentinels 中检索出 _SentinelObject 对象并返回;
    # 检索的原则是: 如果参数 name 已存在于 self._sentinels 字典中, 那么就返回字典中的对应对象, 并且不做写入动作.
    #              如果参数 name 不存在于 self._sentinels 字典中, 那么就写入到字典, 并返回对应的对象.
    #
    ###################################################################################################################
    def __getattr__(self, name):
        if name == '__bases__':
            # Without this help(unittest.mock) raises an exception
            raise AttributeError
        return self._sentinels.setdefault(name, _SentinelObject(name))

    def __reduce__(self):
        return 'sentinel'


sentinel = _Sentinel()

DEFAULT = sentinel.DEFAULT
_missing = sentinel.MISSING
_deleted = sentinel.DELETED


_allowed_names = {
    'return_value', '_mock_return_value', 'side_effect',
    '_mock_side_effect', '_mock_parent', '_mock_new_parent',
    '_mock_name', '_mock_new_name'
}


#######################################################################################################################
# _delegating_property(name)
# 该函数用于判断是否需要返回self._mock_delegate的name值,
# 如果self._mock_delegate没有定义, 那么就返回当前Mock对象的 _mock_ + name (例如: _mock_called)的值.
# 如果self._mock_delegate有定义, 那么就返回self._mock_delegate的name的值,
# 这会促使代码二次进入当前函数去尝试去提取 self._mock_delegate.'_mock_called' 的值, 这个过程是一个递归过程.
#######################################################################################################################
def _delegating_property(name):
    _allowed_names.add(name)
    _the_name = '_mock_' + name
    def _get(self, name=name, _the_name=_the_name):
        sig = self._mock_delegate
        if sig is None:
            return getattr(self, _the_name)
        return getattr(sig, name)
    def _set(self, value, name=name, _the_name=_the_name):
        sig = self._mock_delegate
        if sig is None:
            self.__dict__[_the_name] = value
        else:
            setattr(sig, name, value)

    return property(_get, _set)


#######################################################################################################################
# _CallList(list)
# 该类继承了list内置数据类型, 所以_CallList本质上也是一个list.
# 该类重构了 __contains__ 内置方法: 即 in 关键词判断操作会触发这个内置方法.
#
# 如果 value 参数不是列表, 那么就采用list默认的比较方式, 即: 将value参数与列表中每个元素进行比较判断是否相等.
# 如果 value 参数是一个列表, 那么就尝试比较两个列表是否相等, 或者当前列表的一段连续的元素与 value参数列表相等.
#######################################################################################################################
class _CallList(list):

    def __contains__(self, value):
        # 如果value不是list类型, 那么采用list默认的比较方式来完成比较工作;
        # 即: 将value参数与列表中每个元素进行比较判断是否相等.
        if not isinstance(value, list):
            return list.__contains__(self, value)

        # value 是一个list类型.
        # 获取value这个列表的长度.
        len_value = len(value)

        # 获取当前列表的长度.
        len_self = len(self)

        # 如果value这个列表的长度 大于 当前列表的长度, 返回False.
        if len_value > len_self:
            return False

        # 条件来到这里, 表示当前列表的长度 大于 value这个列表的长度.
        # (len_self - len_value) 的意思是: 从大的那个列表中截取出于小的那个列表一样大的列表.
        #  + 1 是因为 range 读取一个列表从 0 开始, 读取到这个列表末尾是 n - 1, 所以要+1才能等于 n.
        # 假设: len_value = 20 ; len_self = 30
        # range(0, 30 - 20 + 1)
        # range(0, 11)                      等于        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        for i in range(0, len_self - len_value + 1):
            # self[0:0+20]                  20个元素            len_self == 30 所以不会报错.
            # self[1:1+20]                  20个元素
            # self[2:2+20]                  20个元素
            # self[10:10+20]                20个元素
            sub_list = self[i:i+len_value]

            # 重点:
            # sub_list是20个元素的列表, value也是20个元素的列表.
            # 如果任何一次相等, 则表示大的列表中有一段连续的元素与 value 这个列表相等.
            if sub_list == value:
                return True

        return False

    def __repr__(self):
        return pprint.pformat(list(self))


#######################################################################################################################
# _check_and_set_parent(parent, value, name, new_name)
# 该函数检查 value 参数是不是已经设定了 parent,
# 如果已经设定那么就不再设定并返回False.
# 如果没有设定那么就为value添加一组parent属性并返回True.
#######################################################################################################################
def _check_and_set_parent(parent, value, name, new_name):
    """ parent: 的类型是 mock 实例. """

    # 如果 value 拥有 mock 属性, 那么就把 mock 对象提取并返回, 即: value 就是一个mock对象.
    # 如果 value 没有 mock 属性, 那么就原封不动的返回value.
    value = _extract_mock(value)

    # 如果 value 不是一个mock实例, 那么就退出并返回 False.
    if not _is_instance_mock(value):
        return False

    # 三组条件, 任意一个为True则退出并返回False.
    # 挨个拆分查看其含义:
    # (value._mock_name or value._mock_new_name): 如果value 含有 _mock_name 或 _mock_new_name 则为True.
    # (value._mock_parent is not None):           如果 value 含有 _mock_parent 则为True.
    # (value._mock_new_parent is not None):       如果 value 含有 _mock_new_parent 则为True.
    # 大致含义是: 只要 value 对象 含有这四个属性, 就退出并返回False.
    if ((value._mock_name or value._mock_new_name) or
        (value._mock_parent is not None) or
        (value._mock_new_parent is not None)):
        return False

    # 这里是递归提取._mock_new_parent然后判断这个值是否和value相同,
    # 如果递归提取出来的parent与value相同, 则这表示添加过parent了, 不在做添加操作.
    _parent = parent
    while _parent is not None:
        # setting a mock (value) as a child or return value of itself
        # should not modify the mock
        if _parent is value:
            return False
        _parent = _parent._mock_new_parent

    # 添加parent属性
    if new_name:
        value._mock_new_parent = parent
        value._mock_new_name = new_name

    # 添加parent属性
    if name:
        value._mock_parent = parent
        value._mock_name = name

    return True

#######################################################################################################################
# _MockIter
# Internal class to identify if we wrapped an iterator object or not.
#
# 该类用于将一个集合对象设定成一个可迭代对象(iterable).
# 由于 obj 需要是 list , tuple 这种对象, 所以也就只能for或者next, 并没有隐藏什么方法或者属性.
#######################################################################################################################
class _MockIter(object):
    def __init__(self, obj):
        self.obj = iter(obj)
    def __next__(self):
        return next(self.obj)


#######################################################################################################################
#
# class Base(object)
# 该类是所有Mock对象的一个基类: NonCallableMock , CallableMixin , MagicMixin , MagicProxy , AsyncMockMixin ;
# 用于声明 Base._mock_return_value 和 Base._mock_side_effect 这两个类变量;
# 也就是说Base的派生类都具备这两个类变量.
#
#######################################################################################################################
class Base(object):
    _mock_return_value = DEFAULT
    _mock_side_effect = None
    def __init__(self, /, *args, **kwargs):
        pass


class NonCallableMock(Base):
    """A non-callable version of `Mock`"""

    ###################################################################################################################
    # __new__
    # 该方法在赋值之前执行, 这段代码的目的是为了扩展支持AsyncMock的继承扩展.
    #
    # 代码大致的含义是: 如果 当前类的派生类不是一个 AsyncMock, 那么就看看参数里面有没有指定 spec 或者 spec_set,
    #                  如果 设定了 spec 或者 spec_set, 那么在创建构造对象是, 为其增加一个AsyncMock基类, 使其能具备相应的能力.
    #
    # 如果不考虑AsyncMock的话, 那么这段代码其实没有存在的必要, 因为下面这四行代码其实就是一个常规的默认实现.
    # bases = (cls, )
    # new = type(cls.__name__, bases, {'__doc__': cls.__doc__})
    # instance = _safe_super(NonCallableMock, cls).__new__(new)
    # return instance
    #
    ###################################################################################################################
    def __new__(cls, /, *args, **kw):
        # every instance has its own class
        # so we can create magic methods on the
        # class without stomping on other mocks
        bases = (cls,)
        if not issubclass(cls, AsyncMock):
            # Check if spec is an async object or function
            sig = inspect.signature(NonCallableMock.__init__)
            bound_args = sig.bind_partial(cls, *args, **kw).arguments
            spec_arg = [
                arg for arg in bound_args.keys()
                if arg.startswith('spec')
            ]
            if spec_arg:
                # what if spec_set is different than spec?
                if _is_async_obj(bound_args[spec_arg[0]]):
                    bases = (AsyncMockMixin, cls,)
        new = type(cls.__name__, bases, {'__doc__': cls.__doc__})
        instance = _safe_super(NonCallableMock, cls).__new__(new)
        return instance

    ###################################################################################################################
    # __init__
    # 该方法在赋值之后执行, 这段代码是初始化代码, 用于给对象创建一系列属性成员.
    # self.__dict__ = {"_mock_parent":            parent,
    #                  "_mock_name":              name,
    #                  "_mock_new_name":          _new_name,
    #                  "_mock_new_parent":        _mock_new_parent,
    #                  "_mock_sealed":            False,
    #                  "_spec_class":             _spec_class,                  spec_class
    #                  "_spec_set":               spec_set,                     bool
    #                  "_spec_signature":         _spec_signature,              inspect.Signature
    #                  "_mock_methods":           spec,                         dir(spec)
    #                  "_spec_asyncs":            _spec_asyncs,                 [spec_methods: asyncFunction]
    #                  "_mock_children":          {},
    #                  "_mock_wraps":             wraps,
    #                  "_mock_delegate":          None,
    #                  "_mock_called":            False,
    #                  "_mock_call_args":         None,
    #                  "_mock_call_count":        0,
    #                  "_mock_call_args_list":    _CallList(),
    #                  "_mock_mock_calls":        _CallList(),
    #                  "method_calls":            _CallList(),
    #                  "_mock_unsafe":            unsafe}
    #
    # parent参数期望的时一个mock对象, 使用场景在__getattr__中有说明.
    #
    # spec参数期望的是一个对象, 该对象用于限定当前Mock对象的属性,
    # 即: 调用 <Mock原本的属性和方法+spec的属性和方法> 之外的任何方法都会报错.
    # 备注: 虽然调用之外的attribute和method会报错, 但是可以 setattr 去增加来规避报错.
    #
    # spec_set参数期望的是一个对象, 这是spec的严谨版本,
    # 即: 不允许 setattr 的方式来规避报错, 也就是说设定了spec_set之后, 这个对象就是一个immutable对象.
    #
    ###################################################################################################################
    def __init__(
            self, spec=None, wraps=None, name=None, spec_set=None,
            parent=None, _spec_state=None, _new_name='', _new_parent=None,
            _spec_as_instance=False, _eat_self=None, unsafe=False, **kwargs
        ):
        if _new_parent is None:
            _new_parent = parent

        __dict__ = self.__dict__
        __dict__['_mock_parent'] = parent
        __dict__['_mock_name'] = name
        __dict__['_mock_new_name'] = _new_name
        __dict__['_mock_new_parent'] = _new_parent
        __dict__['_mock_sealed'] = False

        # 如果 spec_set 制定了, 那就将它同意赋值给 spec, 然后将spec_set声明为True(bool值);
        # 表明 spec_set = True 是一个严谨对象.
        # 槽点: python变量的类型随意发生变化.
        if spec_set is not None:
            spec = spec_set
            spec_set = True

        # 当 _eat_self 是 True 时, 通常表明spec是一个class类(未实例化)
        # 当 _eat_self 是 False 时, 通常表明spec是一个函数惑方法.
        # 当 parent 不是None时, 通常表明spec是一个类对象(不保证一定是未实例化的).
        if _eat_self is None:
            _eat_self = parent is not None

        # 尝试添加spec限定对象.
        self._mock_add_spec(spec, spec_set, _spec_as_instance, _eat_self)

        __dict__['_mock_children'] = {}
        __dict__['_mock_wraps'] = wraps
        __dict__['_mock_delegate'] = None

        __dict__['_mock_called'] = False
        __dict__['_mock_call_args'] = None
        __dict__['_mock_call_count'] = 0
        __dict__['_mock_call_args_list'] = _CallList()
        __dict__['_mock_mock_calls'] = _CallList()

        __dict__['method_calls'] = _CallList()
        __dict__['_mock_unsafe'] = unsafe

        # 通过kwargs去配置当前mock对象(self)的属性和值.
        # self.configure_mock这个方法的目的是为了简化代码和简化操作,
        # 仅通过配置即可完成对mock对象的属性和值的设定.
        if kwargs:
            self.configure_mock(**kwargs)

        # 执行父类的__init__函数(这里通常是: Base.__init__)
        _safe_super(NonCallableMock, self).__init__(
            spec, wraps, name, spec_set, parent,
            _spec_state
        )


    ###################################################################################################################
    # attach_mock(self, mock, attribute)
    # attribute: 该参数期望的是一个字符串.
    # 该方法的用于将 attribute 字符串参数作为属性名和 mock 对象作为属性值, 写入到 self 这个mock对象中.
    # 在写入之前先重置mock参数的_mock_parent, _mock_new_parent, _mock_name 和 _mock_new_name 属性.
    ###################################################################################################################
    def attach_mock(self, mock, attribute):
        """
        Attach a mock as an attribute of this one, replacing its name and
        parent. Calls to the attached mock will be recorded in the
        `method_calls` and `mock_calls` attributes of this one."""
        inner_mock = _extract_mock(mock)

        inner_mock._mock_parent = None
        inner_mock._mock_new_parent = None
        inner_mock._mock_name = ''
        inner_mock._mock_new_name = None

        setattr(self, attribute, mock)


    def mock_add_spec(self, spec, spec_set=False):
        """Add a spec to a mock. `spec` can either be an object or a
        list of strings. Only attributes on the `spec` can be fetched as
        attributes from the mock.

        If `spec_set` is True then only attributes on the spec can be set."""
        self._mock_add_spec(spec, spec_set)

    ###################################################################################################################
    # _mock_add_spec
    # 该方法的作用是给mock.__dict__增加一组属性.
    # 这些属性主要为了根据参数来决定是否要限定mock对象的属性读取和写入的范围.
    ###################################################################################################################
    def _mock_add_spec(self, spec, spec_set, _spec_as_instance=False,
                       _eat_self=False):
        _spec_class = None
        _spec_signature = None
        _spec_asyncs = []

        # 暂不考虑async.
        # 但是从这个代码来看: 作者期望spec是一个对象类对象? 从spec中尝试遍历所有的attribute(和method)
        # 如果spec有method是coroutine类型的函数, 那么就将其标识纳入到 self.__dict__['_spec_asyncs'] 中.
        for attr in dir(spec):
            if asyncio.iscoroutinefunction(getattr(spec, attr, None)):
                _spec_asyncs.append(attr)

        if spec is not None and not _is_list(spec):

            # 当spec是未实例化的类对象时, isinstance(spec, type) == True;  _spec_class 就是 spec 这个类对象.
            # 当spec是已实例化的对象时, isinstance(spec, type) == False; _spec_class 就是 type(spec);
            # type(已实例化的对象), 得到该对象的类对象. 举例:
            # class Hello(object):
            #     pass
            #
            # print(isinstance(Hello, type))      # True
            # not_instance = Hello
            # print(not_instance)                 # <class '__main__.Hello'>
            # instanced = Hello()
            # print(instanced)                    # <__main__.Hello object at 0x0000029EE61D6DF0>
            # instanced_class = type(instanced)
            # print(instanced_class)              # <class '__main__.Hello'>
            # instance_again = instanced_class()
            # print(instance_again)               # <__main__.Hello object at 0x000001EC406A0250>
            if isinstance(spec, type):
                _spec_class = spec
            else:
                _spec_class = type(spec)
            res = _get_signature_object(spec,
                                        _spec_as_instance, _eat_self)
            _spec_signature = res and res[1]      # 如果res存在, 那么它一定是一个元组对象, 提取第二个元素(Signature对象).

            spec = dir(spec)                      # 提取spec的所有__dict__方法(字符串集合: [str, ...])

        # 代码执行到这里, spec由可能是两种类型的值:
        # 1. list
        # 2. None
        __dict__ = self.__dict__
        __dict__['_spec_class'] = _spec_class
        __dict__['_spec_set'] = spec_set
        __dict__['_spec_signature'] = _spec_signature
        __dict__['_mock_methods'] = spec
        __dict__['_spec_asyncs'] = _spec_asyncs

    ###################################################################################################################
    # __get_return_value
    # __set_return_value
    # __return_value_doc
    # return_value = property(__get_return_value, __set_return_value, __return_value_doc)
    #
    # 这四行代码是python2里面的久语法, 用于读取和赋值NonCallableMock.return_value属性的值.
    ###################################################################################################################
    def __get_return_value(self):
        # 一般来说, 实例化Mock时会再其继承的父类(CallableMixin)中完成赋值
        # self.__dict__['_mock_return_value'] = return_value 动作,
        # 这个值默认情况下时 sentinel.DEFAULT, 或者是实例化时传递的具体值.
        ret = self._mock_return_value

        # TODO: 委托对象处理机制待补充.
        if self._mock_delegate is not None:
            ret = self._mock_delegate.return_value

        # 如果实例化Mock对象时, 没有提供return_value参数,
        # 那么就子mock的return_value, 通常情况也是一个sentinel.DEFAULT.
        if ret is DEFAULT:
            ret = self._get_child_mock(
                _new_parent=self, _new_name='()'
            )
            self.return_value = ret                     # 这里将会进入 __set_return_value 方法, 完成赋值动作.

        # 如果实例化Mock对象时, 提供了return_value参数, 那么就返回这个参数值.
        return ret

    def __set_return_value(self, value):
        if self._mock_delegate is not None:
            self._mock_delegate.return_value = value
        else:
            self._mock_return_value = value
            _check_and_set_parent(self, value, None, '()')

    __return_value_doc = "The value to be returned when the mock is called."
    return_value = property(__get_return_value, __set_return_value,
                            __return_value_doc)


    ###################################################################################################################
    # __class__
    # 覆盖默认的object内置方法, 用于返回具体的类对象.
    # 当实例化Mock时提供了spec或者spec_set参数, 返回 spec 参数值: self._spec_class.
    # 当实例化Mock时未提供spec或者spec_set参数, 返回当前实例的类对象; 例如:
    #
    # class Hello(object): pass
    # h1 = Hello
    # print(h1)                                 h1不是实例, 而是类(<class '__main__.Hello'>)
    # h2 = Hello()
    # print(h2)                                 当前实例(h2)的类(<__main__.Hello object at 0x000002019E77F220>)
    ###################################################################################################################
    @property
    def __class__(self):
        if self._spec_class is None:
            return type(self)
        return self._spec_class

    # 这里要么返回当前Mock对象的_mock_called值, 要么范围委托类的_mock_called值.
    called = _delegating_property('called')
    call_count = _delegating_property('call_count')
    call_args = _delegating_property('call_args')
    call_args_list = _delegating_property('call_args_list')
    mock_calls = _delegating_property('mock_calls')

    ###################################################################################################################
    # __get_side_effect
    # __set_side_effect
    # side_effect = property(__get_side_effect, __set_side_effect)
    #
    # 这三行代码是python2里面的久语法, 仍然是要读取或者写入 self._mock_side_effect 对象值.
    # 这些代码的目的是为了增加委托代理的扩展点, 即:
    # 当设定了self._mock_delegate时, 就读取 self._mock_delegate 对象的 _mock_side_effect 对象值.
    # 当没有设定self._mock_delegate时, 就读取当前Mock对象的_mock_side_effect对象值.
    ###################################################################################################################
    def __get_side_effect(self):
        delegated = self._mock_delegate
        if delegated is None:
            return self._mock_side_effect
        sf = delegated.side_effect
        if (sf is not None and not callable(sf)
                and not isinstance(sf, _MockIter) and not _is_exception(sf)):
            sf = _MockIter(sf)
            delegated.side_effect = sf
        return sf

    def __set_side_effect(self, value):
        value = _try_iter(value)
        delegated = self._mock_delegate
        if delegated is None:
            self._mock_side_effect = value
        else:
            delegated.side_effect = value

    side_effect = property(__get_side_effect, __set_side_effect)

    ###################################################################################################################
    # reset_mock(self,  visited=None, *, return_value=False, side_effect=False)
    # 重新初始化mock对象, 即: 把mock对象的called重置为未调用过状态, 把call_count重置为0, 以及其他关联的收集全部倒退到初始化状态.
    #
    # 参数*表示: 星号后面的参数, 再提供实参时必须提供参数名, 忽略参数名的话会报错.
    # return_value参数: 当值为False时, 表示不需要重置self._mock_return_value的值;
    #                  当值为True时, 表示重置 self._mock_return_value 的值为 sentinel.DEFAULT 值.
    # side_effect参数: 当值为False时, 表示不需要重置self._mock_side_effect的值;
    #                 当值为True时, 表示重置 self._mock_side_effect的值为 None 值.
    ###################################################################################################################
    def reset_mock(self,  visited=None,*, return_value=False, side_effect=False):
        "Restore the mock object to its initial state."
        if visited is None:
            visited = []
        if id(self) in visited:
            return
        visited.append(id(self))

        self.called = False
        self.call_args = None
        self.call_count = 0
        self.mock_calls = _CallList()
        self.call_args_list = _CallList()
        self.method_calls = _CallList()

        if return_value:
            self._mock_return_value = DEFAULT
        if side_effect:
            self._mock_side_effect = None

        # 已经知道 _mock_children 的作用(在__getattr__中有说明).
        # 这里只是递归的去重置 _mock_children 的属性值, 使其恢复到初始状态(并不是清空 _mock_children).
        for child in self._mock_children.values():
            if isinstance(child, _SpecState) or child is _deleted:
                continue
            child.reset_mock(visited)

        ret = self._mock_return_value
        if _is_instance_mock(ret) and ret is not self:
            ret.reset_mock(visited)

    ###################################################################################################################
    # configure_mock
    # 该函数通过kwargs参数来设定当前Mock对象, 这是一个非常常规的函数,
    # 主要目的时为了省略赋值操作, 简化到只需要提供一个字典当作配置信息,
    # 即可完成对Mock的配置, 作者的目的可能是为了实例化和配置分离.
    ###################################################################################################################
    def configure_mock(self, /, **kwargs):
        """Set attributes on the mock through keyword arguments.

        Attributes plus return values and side effects can be set on child
        mocks using standard dot notation and unpacking a dictionary in the
        method call:

        >>> attrs = {'method.return_value': 3, 'other.side_effect': KeyError}
        >>> mock.configure_mock(**attrs)"""
        for arg, val in sorted(kwargs.items(),
                               # we sort on the number of dots so that
                               # attributes are set before we set attributes on
                               # attributes
                               key=lambda entry: entry[0].count('.')):
            args = arg.split('.')
            final = args.pop()
            obj = self
            for entry in args:
                obj = getattr(obj, entry)
            setattr(obj, final, val)

    ###################################################################################################################
    # __getattr__(self, name)
    # 该方法原本是一个object的内置方法, 用于获取那些不存在的属性.
    # 该方法的作用时当获取不到有效属性时, 创建一个mock对象并范围这个新创建的mock对象,
    # 同时记录下来这个不存在的属性(写入到self._mock_children字典中).
    #
    # from unittest.mock import Mock
    #
    # m = Mock()
    # print(m)                    # mock对象:        <Mock id='1603201309712'>
    # print(m.goodmorning)        # 返回新的mock:    <Mock name='mock.goodmorning' id='2317134082448'>
    # print(m._mock_children)     # _mock_children: {'goodmorning': <Mock name='mock.goodmorning' id='1603209933200'>}
    ###################################################################################################################
    def __getattr__(self, name):
        # mock对象必须拥有'_mock_methods'和'_mock_unsafe'属性,
        # 如果因为缺少这两个属性而触发进入到这里, 会抛出AtrributeError异常.
        # TODO: 只要是正常实例化的mock对象在__init__里面都设定了这两个属性,
        #       那什么场景下会把这两个属性移除掉, 从而导致进入到__getattr__方法中来?
        if name in {'_mock_methods', '_mock_unsafe'}:
            raise AttributeError(name)

        # self._mock_methods 的值有两种类型: None 或 列表(dir(spec)).
        # name not in self._mock_methods 的意思是:
        # 如果name这个字符串参数即不再 mock 的属性范围内, 也不在限定对象spec的属性范围内, 那么就抛出异常.
        elif self._mock_methods is not None:
            if name not in self._mock_methods or name in _all_magics:
                raise AttributeError("Mock object has no attribute %r" % name)

        # name参数是不是前后双下划线的魔法方法, 如果是的花并且不在属性范围内的那么就抛出异常.
        elif _is_magic(name):
            raise AttributeError(name)

        # 默认情况下: _mock_unsafe 是一个 False 值.
        # 这里想表达的是: _mock_unsafe 是 False 时, name参数不可以是 'assert' 或 'assret' 开头的属性调用.
        # TODO: 什么情况下 _mock_unsafe 才会是 True 呢?
        if not self._mock_unsafe:
            if name.startswith(('assert', 'assret')):
                raise AttributeError("Attributes cannot start with 'assert' "
                                     "or 'assret'")

        # 默认情况下 self._mock_children 是一个空字典, 所以result通常情况下应该是一个None.
        # 下面这一整段代码的意思是:
        # 从 self._mock_children这个字典中获取name的对应的值:
        # 当值为_deleted(sentinel.DELETE)时, 就报错.
        # 当值为None时, 就创建一个mock对象, 然后写入到 self._mock_children 字典中, 然后返回这个新创建的mock.
        # 当值为_SpecState类时, 创建一个带有限定属性的mock对象的, 写入self._mock_children字典中, 返回这个新创建的mock.
        #
        # 这里延申出来一个配对的属性, 那就是 parent 概念, 在创建新的mock时, 会将当前的mock当作parent来实例化.
        result = self._mock_children.get(name)
        if result is _deleted:
            raise AttributeError(name)
        elif result is None:
            wraps = None
            if self._mock_wraps is not None:
                # XXXX should we get the attribute without triggering code
                # execution?
                wraps = getattr(self._mock_wraps, name)

            result = self._get_child_mock(
                parent=self, name=name, wraps=wraps, _new_name=name,
                _new_parent=self
            )
            self._mock_children[name] = result

        elif isinstance(result, _SpecState):
            result = create_autospec(
                result.spec, result.spec_set, result.instance,
                result.parent, result.name
            )
            self._mock_children[name]  = result

        return result

    ###################################################################################################################
    # _extract_mock_name
    # 该方法负责提取mock对象的_mock_name属性的值, 这个属性值通常情况下是在Mock实例化时的参数提供: name 或 new_name.
    # 如果实例化时没有提供 name 或 new_name 参数值, 那么当前函数就会返回 'mock' 字符串.
    # 如果实例化时提供了 name 或者 new_name 参数值, 那么当前函数就会收集它所有的parent. 合并返回 'parent.parent.name'
    #
    # 当调用不存在的属性时, OriginMock会返回一个新的NewMock对象, 并将这个对象记录在OriginMock._mock_children这个字典中.
    # 举例:
    # from unittest.mock import Mock
    #
    # m = Mock()
    # x = m.goodmorning
    #
    # 说明:
    # 变量 x 是新的Mock对象, 它的_mock_new_name是 goodmorning.
    # 变量 m 的__dict__字典中也多了一个 goodmorning 的key, 对应存储的值是 x .
    # 变量 m 的_mock_children字典中也多了一个 goodmorning 的key, 对应存储的值是 x .
    #
    # m.goodmorning 由于m这个mock对象没有goodmorning属性, 当执行这个命令时会触发 __getattr__ 方法,
    # 在 __getattr__ 方法中使用了 _get_child_mock 方法来创建一个新的mock对象,并将其纳入 m._mock_children字典中.
    ###################################################################################################################
    def _extract_mock_name(self):
        _name_list = [self._mock_new_name]                      # _name_list = ['goodmorning']
        _parent = self._mock_new_parent                         # _parent == m == <Mock id='10000'>
        last = self                                             # last == <Mock name='mock.goodmorning' id='1002'>

        dot = '.'
        if _name_list == ['()']:
            dot = ''

        # 递归把所有parent都提取出来, 然后把这些parent的_mock_new_name都加入到 _name_list中.
        while _parent is not None:
            last = _parent                                      # last = <Mock id='10000'>

            _name_list.append(_parent._mock_new_name + dot)     # _name_list = ['goodmorning', '.']
            dot = '.'
            if _parent._mock_new_name == '()':
                dot = ''

            _parent = _parent._mock_new_parent

        _name_list = list(reversed(_name_list))                 # _name_list = ['.', 'goodmorning']
        _first = last._mock_name or 'mock'                      # _first = 'mock'
        if len(_name_list) > 1:
            if _name_list[1] not in ('()', '().'):
                _first += '.'                                   # _first = 'mock.'
        _name_list[0] = _first                                  # _name_list = ['mock.', 'goodmorning']
        return ''.join(_name_list)                              # 'mock.goodmorning'

    ###################################################################################################################
    # __repr__
    # 该方法是object的内置方法, 当使用print打印当前对象时会触发这个函数, 用于定制化显示实例信息.
    # 例如: <Mock id='10000'>                             # 实例化Mock时没有提供name参数
    #       <Mock name='mock' id='10001'>                 # 实例化Mock时提供了name参数
    #       <Mock name='mock.goodmorning' id='10001'>     # 子mock对象(实例化时提供了name参数)
    #       <Mock spec='Hello' id='10003'>                # 实例化Mock时提供了spec限定对象.
    #       <Mock spec_set='HelloStrict' id='10004'>      # 实例化Mock时提供了spec_set严格限定对象.
    ###################################################################################################################
    def __repr__(self):
        name = self._extract_mock_name()

        # 如果 name 不等于 'mock' 也不等于 'mock.' 那么 name_string 就是一个空字符串对象.
        name_string = ''
        if name not in ('mock', 'mock.'):
            name_string = ' name=%r' % name

        # 如果 spec_string 是 None , 那么spec_string 就是一个空字符串对象.
        spec_string = ''
        if self._spec_class is not None:
            spec_string = ' spec=%r'
            if self._spec_set:
                spec_string = ' spec_set=%r'
            spec_string = spec_string % self._spec_class.__name__

        # type(self).__name__ 是类的名称: Mock
        # name_string: 如果是空字符串, 那么就是留白.
        # spec_string: 如果是空字符串, 那么就是留白.
        # id(self): id串
        return "<%s%s%s id='%s'>" % (
            type(self).__name__,
            name_string,
            spec_string,
            id(self)
        )

    ###################################################################################################################
    # __dir__
    # 该方法是object的内置方法, 当使用dir(mock)时会触发这个函数,
    # 这里重新定制了__dir__方法的返回结果: 仅显示常用的属性和方法.
    ###################################################################################################################
    def __dir__(self):
        """Filter the output of `dir(mock)` to only useful members."""
        if not FILTER_DIR:
            return object.__dir__(self)

        # self._mock_methods 通常是 spec 或 spec_set 限定对象的属性和方法的集合.
        # 如果实例化Mock对象时没有提供spec或spec_set参数, 那么extras就是一个空列表.
        extras = self._mock_methods or []

        # type(self) == <class unittest.mock.Mock>
        # from_type == dir(unittest.mock.Mock) == 类对象的类变量和方法集合
        # from_dict == 实例对象的属性和方法集合
        # from_child_mocks == self._mock_children + 排除掉 sentinels.DELETE 状态的mock对象的 name的集合
        from_type = dir(type(self))
        from_dict = list(self.__dict__)
        from_child_mocks = [
            m_name for m_name, m_value in self._mock_children.items()
            if m_value is not _deleted]

        # 排除掉魔法方法
        from_type = [e for e in from_type if not e.startswith('_')]
        from_dict = [e for e in from_dict if not e.startswith('_') or
                     _is_magic(e)]

        # 合并和排序, 然后返回这个集合
        return sorted(set(extras + from_type + from_dict + from_child_mocks))

    ###################################################################################################################
    # __setattr__(self, name, value)
    # 该函数为确保行为与定义时的表现的一致性, 要根据设定的值做必要的分流检查.
    # 例如: 当Mock实例化时设定了 spec_set 对象时, 那么就限定只能设定限定范围内的属性...
    ###################################################################################################################
    def __setattr__(self, name, value):
        # _allowed_names = {
        #     'return_value', '_mock_return_value', 'side_effect',
        #     '_mock_side_effect', '_mock_parent', '_mock_new_parent',
        #     '_mock_name', '_mock_new_name'
        # }
        # 当 name 参数的值是这个范围内的属性时, 可以设定该属性值.
        if name in _allowed_names:
            # property setters go through here
            return object.__setattr__(self, name, value)

        # 当 self._spec_set 有值时, self._mock_methods 的值通常是 dir(self._spec_set), 所以前两个条件通常都会是True.
        # name not in self._mock_methods 表示: 如果 name 不在限定范围内.
        # name not in self.__dict__ 表示: 如果 name 不在当前Mock对象的 self.__dict__ 范围内.
        # 这几个条件都不满足, 则报错.
        elif (self._spec_set and self._mock_methods is not None and
            name not in self._mock_methods and
            name not in self.__dict__):
            raise AttributeError("Mock object has no attribute '%s'" % name)

        # _unsupported_magics = {
        #     '__getattr__', '__setattr__',
        #     '__init__', '__new__', '__prepare__',
        #     '__instancecheck__', '__subclasscheck__',
        #     '__del__'
        # }
        # Mock不允许对 _unsupported_magics 范围的属性做赋值动作,
        # 如果 name 是这个范围的值, 则报错.
        elif name in _unsupported_magics:
            msg = 'Attempting to set unsupported magic method %r.' % name
            raise AttributeError(msg)

        # 涉及到 magics 方法或属性(魔法方法或内置属性) 的赋值, 都进入这个条件分支.
        elif name in _all_magics:
            # self._mock_methods == dir(spec)
            # 所以魔法方法的赋值只限定再 dir(spec) 范围内, 否则报错.
            if self._mock_methods is not None and name not in self._mock_methods:
                raise AttributeError("Mock object has no attribute '%s'" % name)

            # 涉及到 magics 方法或属性的赋值, 主要是围绕value的值来决定如何赋值
            # 当 value 不是一个 mock 实例对象时, 将value的值写入到 Mock类中然后实例化这个Mock类.
            if not _is_instance_mock(value):
                setattr(type(self), name, _get_method(name, value))
                original = value
                value = lambda *args, **kw: original(self, *args, **kw)

            # 当 value 是一个 mock 实例对象时, 将这个 value 视为一个 children 对象.
            else:
                # only set _new_name and not name so that mock_calls is tracked
                # but not method calls
                _check_and_set_parent(self, value, None, name)
                setattr(type(self), name, value)
                self._mock_children[name] = value

        # 当 name 参数的值为 '__class__' 时, 表示 value 时一个限定对象.
        elif name == '__class__':
            self._spec_class = value
            return

        # 如果上述条件都不满足, 最后尝试检查将它添加到children集合中.
        else:
            # TODO: _check_and_set_parent待处理
            if _check_and_set_parent(self, value, name, name):
                self._mock_children[name] = value

        # 当 self._mock_sealed 是 False 时, 表示当访问不存在的属性时创建子mock并返回该子mock对象.
        # 当 self._mock_sealed 是 True 时, 表示当访问不存在的属性时不创建子mock对象并抛出异常.
        if self._mock_sealed and not hasattr(self, name):
            mock_name = f'{self._extract_mock_name()}.{name}'
            raise AttributeError(f'Cannot set {mock_name}')

        # 将 name 和 value 写入到Mock的属性中.
        return object.__setattr__(self, name, value)

    ###################################################################################################################
    # __delattr__(name)
    # 该方法是object的内置方法, 当使用delattr(mock, attr_name)去删除
    # mock对象的attr_name属性, 并且当attr_name不存在时会触发当前方法.
    #
    # 这里重新定制了__delattr__方法的,
    # 1. 尝试删除基于 type(self) 的 unittest.mock.Mock 的类变量.
    # 2. 尝试删除 self 这个mock实例的属性.
    # 3. 尝试删除 self._mock_children[name] 的值.
    # 4. 尝试新增一个标记 self._mock_children[name] = sentinels.DELETE 的值.
    ###################################################################################################################
    def __delattr__(self, name):
        # 尝试从 type(self) 的类中删除该属性.
        # 当 name 属于 _all_magics 范围, 且 name 属于 type(self).__dict__ 范围
        if name in _all_magics and name in type(self).__dict__:
            # 删除 type(self) 类对象的属性.
            delattr(type(self), name)

            # 当 name 不在 self.__dict (实例)范围, 则不做后续删除动作.
            if name not in self.__dict__:
                # for magic methods that are still MagicProxy objects and
                # not set on the instance itself
                return

        # 尝试从当前mock实例的_mock_children中提取name这个mock子对象.
        obj = self._mock_children.get(name, _missing)

        # 如果 name 在 self.__dict__ 范围, 那么就删除该属性.
        if name in self.__dict__:
            _safe_super(NonCallableMock, self).__delattr__(name)

        # 如果 obj 这个子mock是sentinels.DELETE状态, 那么就报错.
        elif obj is _deleted:
            raise AttributeError(name)

        # 如果 obj 这个子mock不是sentinels.MISSING时, 从self._mock_children中删除这个子mock对象.
        if obj is not _missing:
            del self._mock_children[name]

        # 删除后, 标记当前name的值是一个 sentinels.DELETE 状态.
        self._mock_children[name] = _deleted

    ###################################################################################################################
    # _format_mock_call_signature(self, args, kwargs)
    # 该函数用于生成参数签名.
    #
    # 举例:
    # from unittest.mock import Mock
    # m = Mock()
    # _format_mock_call_signature(args=(), kwargs={"name": "mymock"}) 将生成 mock(name="mymock")
    # _format_mock_call_signature(args=(), kwargs={"hello": "world"}) 将生成 mock(hello="world")
    #
    # 生成的mock(name="mymock") 或 mock(hello="world") 被称为是一个mock_call_signature.
    # 生成签名的作用是: 可以拿来比较初始化提供的参数是否一样.
    ###################################################################################################################
    def _format_mock_call_signature(self, args, kwargs):
        name = self._mock_name or 'mock'
        return _format_call_signature(name, args, kwargs)

    ###################################################################################################################
    # _format_mock_failure_message(self, args, kwargs, action='call')
    # 该函数用于返回通用的mock比较失败的错误消息.
    # expected_string = self._format_mock_call_signature(args, kwargs)  期望的签名
    # actual_string = self._format_mock_call_signature(*call_args)      实际的签名
    #
    # 备注: self.call_args 是最后一次执行mock时提供的参数记录.
    ###################################################################################################################
    def _format_mock_failure_message(self, args, kwargs, action='call'):
        message = 'expected %s not found.\nExpected: %s\nActual: %s'
        expected_string = self._format_mock_call_signature(args, kwargs)
        call_args = self.call_args
        actual_string = self._format_mock_call_signature(*call_args)
        return message % (action, expected_string, actual_string)

    ###################################################################################################################
    # _get_call_signature_from_name(self, name)
    # 该函数根据 name 参数来查找嵌套spec的signature, 这是非常抽象的场景, 具体测试使用的例子需要参考这里:
    # https://github.com/python/cpython/commit/c96127821ebda50760e788b1213975a0d5bea37f
    #
    # 通常情况下这里的返回值都是None, sig也是None;
    # 只有那些嵌套对象才会被查找到:
    # 首先它只找 self._mock_children 中的 name, 这意味着要使用
    # mock.meth 这种不存在的对象(它触发了__getattr__才会创建子mock对象并写入到self._mock_children);
    # 不仅如此, 它还要求这个子mock对象要提供spec限定对象参数, 才会提取出一个有效的signature.
    # 因此综合评估下来这个使用场景太少了.
    ###################################################################################################################
    def _get_call_signature_from_name(self, name):
        """
        * If call objects are asserted against a method/function like obj.meth1
        then there could be no name for the call object to lookup. Hence just
        return the spec_signature of the method/function being asserted against.
        * If the name is not empty then remove () and split by '.' to get
        list of names to iterate through the children until a potential
        match is found. A child mock is created only during attribute access
        so if we get a _SpecState then no attributes of the spec were accessed
        and can be safely exited.
        """
        if not name:
            return self._spec_signature                     # 如果没提供spec实例对象, 那么这里就是None

        sig = None
        names = name.replace('()', '').split('.')           # 处理name: 移除'()' 和 分割 '.', names是一个列表对象
        children = self._mock_children

        for name in names:
            child = children.get(name)                      # 通过 name 在 self._mock_children 中找到对应的子mock对象
            if child is None or isinstance(child, _SpecState):
                break
            else:
                children = child._mock_children
                sig = child._spec_signature                 # 将子mock对象的._spec_signature赋值给sig

        return sig

    ###################################################################################################################
    # _call_matcher(self, _call)
    # 该函数用于匹配限定对象(self._spec_signature)的参数签名 或 匹配嵌套的限定对象(也是_spec_signature)的参数签名.
    # 如果没有匹配到参数签名, 那么就原封不动的返回 _call 参数.
    ###################################################################################################################
    def _call_matcher(self, _call):
        """
        Given a call (or simply an (args, kwargs) tuple), return a
        comparison key suitable for matching with other calls.
        This is a best effort method which relies on the spec's signature,
        if available, or falls back on the arguments themselves.
        """

        # 当 _call 是一个 tuple 时, 它有三种形式:
        # _Call(('name', (), {})) == ('name',)               使用_Call来做==操作比较时, 可以省略掉那些空的冗余.
        # _Call(('name', (1,), {})) == ('name', (1,))        使用_Call来做==操作比较时, 可以省略掉那些空的冗余.
        # _Call(((), {'a': 'b'})) == ({'a': 'b'},)           使用_Call来做==操作比较时, 可以省略掉那些空的冗余.
        #
        # 当 _call 大于两个对象时, 表示它肯定提供了 name, 所以下面这里使用_call[0]来取name.
        # 除非有涉及到嵌套的对象, 否则基本上sig就是个None.
        if isinstance(_call, tuple) and len(_call) > 2:
            sig = self._get_call_signature_from_name(_call[0])
        else:
            sig = self._spec_signature

        if sig is not None:
            if len(_call) == 2:
                name = ''
                args, kwargs = _call
            else:
                name, args, kwargs = _call
            try:
                return name, sig.bind(*args, **kwargs)          # 这里通过try去测试_call与sig.bind的参数是否吻合.
            except TypeError as e:
                return e.with_traceback(None)                   # 这里返回一个Exception
        else:
            return _call

    ###################################################################################################################
    # assert_not_called(self)
    # 该方法用于断言当前mock对象没有被调用过.
    #
    # 由于每次调用mock实例对象, 它内部都会调用CallableMixin._increment_mock_call方法
    # 来记录一些统计信息, 其中就包括self.call_count的递增, 用于表示当前这个mock实例对象被调用过多少次.
    #
    # 如果 self.call_count == 0 则表示当前mock实例对象没有被调用过, 不会报错, 也不会返回任何值.
    # 如果 self.call_count != 0 则表示当前mock实例对象已经被调用过, 这是就会抛出异常.
    ###################################################################################################################
    def assert_not_called(self):
        """assert that the mock was never called.
        """
        if self.call_count != 0:
            msg = ("Expected '%s' to not have been called. Called %s times.%s"
                   % (self._mock_name or 'mock',
                      self.call_count,
                      self._calls_repr()))
            raise AssertionError(msg)

    ###################################################################################################################
    # assert_called(self)
    # 该方法用于断言当前mock对象已经调用过.
    #
    # self.call_count == 0 则表示当前mock实例对象没有被调用过.
    ###################################################################################################################
    def assert_called(self):
        """assert that the mock was called at least once
        """
        if self.call_count == 0:
            msg = ("Expected '%s' to have been called." %
                   (self._mock_name or 'mock'))
            raise AssertionError(msg)

    ###################################################################################################################
    # assert_called_once(self)
    # 该方法用于断言当前mock对象仅调用过一次.
    #
    # self.call_count == 1 则表示当前mock实例对象仅调用过一次.
    ###################################################################################################################
    def assert_called_once(self):
        """assert that the mock was called only once.
        """
        if not self.call_count == 1:
            msg = ("Expected '%s' to have been called once. Called %s times.%s"
                   % (self._mock_name or 'mock',
                      self.call_count,
                      self._calls_repr()))
            raise AssertionError(msg)

    ###################################################################################################################
    # assert_called_with
    # 该函数用于验证最后一次调用时传递的参数与当前传递的参数是否一致, 主要体现在对参数的验证上.
    ###################################################################################################################
    def assert_called_with(self, /, *args, **kwargs):
        """assert that the last call was made with the specified arguments.

        Raises an AssertionError if the args and keyword args passed in are
        different to the last call to the mock."""

        # self.call_args 是一个 _Call 对象(一个Tuple对象).
        # 当self.call_args is None 时则表示该mock尚未被调用过, 因此会抛出一个异常.
        if self.call_args is None:
            expected = self._format_mock_call_signature(args, kwargs)
            actual = 'not called.'
            error_message = ('expected call not found.\nExpected: %s\nActual: %s'
                    % (expected, actual))
            raise AssertionError(error_message)

        def _error_message():
            msg = self._format_mock_failure_message(args, kwargs)
            return msg

        # NonCallableMock._call_matcher 在常规情况下会原封不动的返回(args, kwargs).
        # 这里就是判断当前的 (args, kwargs) 和 最后一次执行mock的参数是否一致.
        expected = self._call_matcher((args, kwargs))
        actual = self._call_matcher(self.call_args)
        if expected != actual:
            cause = expected if isinstance(expected, Exception) else None
            raise AssertionError(_error_message()) from cause

    ###################################################################################################################
    # assert_called_once_with(self, /, *args, **kwargs)
    # 该方法用于断言当前mock对象是否仅被调用过一次并且调用的参数与当前方法提供的参数一致.
    ###################################################################################################################
    def assert_called_once_with(self, /, *args, **kwargs):
        """assert that the mock was called exactly once and that that call was
        with the specified arguments."""
        if not self.call_count == 1:
            msg = ("Expected '%s' to be called once. Called %s times.%s"
                   % (self._mock_name or 'mock',
                      self.call_count,
                      self._calls_repr()))
            raise AssertionError(msg)
        return self.assert_called_with(*args, **kwargs)

    ###################################################################################################################
    # assert_has_calls(self, calls, any_order=False)
    # 该方法用于断言当前mock对象的历史调用记录(self.mock_calls)是否包含calls参数, 如果包含则表示都调用过了.
    # 该方法提供了 any_order 参数, 表示其支持两种比较算法:
    # any_order == False 时, 采用连续性匹配算法.
    # any_order == True 时, 采用非连续性匹配算法.
    ###################################################################################################################
    def assert_has_calls(self, calls, any_order=False):
        """assert the mock has been called with the specified calls.
        The `mock_calls` list is checked for the calls.

        If `any_order` is False (the default) then the calls must be
        sequential. There can be extra calls before or after the
        specified calls.

        If `any_order` is True then the calls can be in any order, but
        they must all appear in `mock_calls`."""

        # expected: list; 尝试提取嵌套的对象的执行参数, 如果没有嵌套对象, 那就圆路返回该参数.
        expected = [self._call_matcher(c) for c in calls]

        # (e for e in expected if isinstance(e, Exception): 遍历expected列表是否存在异常信息(那些签名与调用的签名不吻合).
        # next(iterator, None): 提取第一个错误的信息.
        # cause: 是一个异常信息对象 或 None 对象.
        cause = next((e for e in expected if isinstance(e, Exception)), None)

        # self.mock_calls 是一个列表, 用于存储历史调用记录.
        all_calls = _CallList(self._call_matcher(c) for c in self.mock_calls)

        # any_order == False, 表示: 要求连续性的匹配.
        if not any_order:

            # 由于 all_calls 是 _CallList 对象, 所以 这里的 in 操作会
            # 触发 _CallList 对象的__contains__方法来完成连续性匹配.
            # 然后根据返回值来与 not 关键字进行判断; 即:
            # expected 这列表如果连续性匹配all_calls不成立, 那么就抛出异常.
            if expected not in all_calls:

                # 当 cause 是 None 时, 表示 expected 列表没有异常;
                # 那么它就仅抛出没有找到连续性calls错误信息.
                if cause is None:
                    problem = 'Calls not found.'

                # 当 cause 不是 None 时, 表示 expected 列表存在异常;
                # 列出异常对象列表(主要体现在数量上)的错误信息.
                else:
                    problem = ('Error processing expected calls.\n'
                               'Errors: {}').format(
                                   [e if isinstance(e, Exception) else None
                                    for e in expected])

                # 抛出异常; raise AssertionError from cause
                raise AssertionError(
                    f'{problem}\n'
                    f'Expected: {_CallList(calls)}'
                    f'{self._calls_repr(prefix="Actual").rstrip(".")}'
                ) from cause

            # expected in all_calls: 连续性匹配命中; 退出函数
            return

        # any_order == True, 表示: 不要求连续性的匹配.
        # list(all_calls): 将 _CallList 对象转换成常规的list对象.
        all_calls = list(all_calls)

        # 遍历expected, 用每个kall元素去尝试从 all_calls 移除 kall 对象,
        # 如果单个移除成功, 那么就表示单个元素匹配成功.
        # 如果全部移除成功, 那么就表示非连续性的匹配成功.
        # 如果任意一个元素移除失败, 那么就表示匹配失败.
        not_found = []
        for kall in expected:
            try:
                all_calls.remove(kall)
            except ValueError:
                not_found.append(kall)

        # 如果 not_found 列表不为空, 那么就表示有至少一个元素移除失败, 那么就表示匹配失败了.
        # 这是就需要排除异常: raise AssertionError from cause
        if not_found:
            raise AssertionError(
                '%r does not contain all of %r in its call list, '
                'found %r instead' % (self._mock_name or 'mock',
                                      tuple(not_found), all_calls)
            ) from cause

    ###################################################################################################################
    # assert_any_call(self, /, *args, **kwargs)
    # 该方法用于断言当前mock对象的历史调用记录中是否有某个签名参数与当前签名参数一致.
    # 唧唧歪歪: 感觉函数名 assert_has_called 更容易明白是什么意思.
    ###################################################################################################################
    def assert_any_call(self, /, *args, **kwargs):
        """assert the mock has been called with the specified arguments.

        The assert passes if the mock has *ever* been called, unlike
        `assert_called_with` and `assert_called_once_with` that only pass if
        the call is the most recent one."""

        # expected 是单个对象, 而且只提供两个参数.
        expected = self._call_matcher((args, kwargs))

        # 这里为什么使用 self._call_args_list 而不是使用 self.mock_calls ?
        # 主要的原因是: 这里不关注嵌套限定对象, 而只关注限定对象,
        # 即: 仅尝试从 mock 的 self.spec_signature 来验证签名一致性.
        # 另外的原因是: expected是两个参数的_Call,
        # 而self.mock_calls的_Call是三个参数(含name),
        # 而 self.call_args_list 的_Call是两个参数,
        # 所以这里采用 self.call_args_list 来当作比较对象.
        actual = [self._call_matcher(c) for c in self.call_args_list]

        # 如果 expected 对象不在 actual(历史调用记录) 中, 那么就抛出异常.
        if expected not in actual:
            cause = expected if isinstance(expected, Exception) else None
            expected_string = self._format_mock_call_signature(args, kwargs)
            raise AssertionError(
                '%s call not found' % expected_string
            ) from cause

    ###################################################################################################################
    # _get_child_mock(self, /, **kw)
    # 该方法用于创建一个子mock对象.
    ###################################################################################################################
    def _get_child_mock(self, /, **kw):
        """Create the child mocks for attributes and return value.
        By default child mocks will be the same type as the parent.
        Subclasses of Mock may want to override this to customize the way
        child mocks are made.

        For non-callable mocks the callable variant will be used (rather than
        any custom subclass)."""

        # _new_name 有几个场景, 其中一个我已知的是:
        # 当使用 mock.foo 并且 mock 对象不存在 foo 属性或方法时,
        # 就尝试使用这个foo当作_new_name来创建一个子mock对象.
        _new_name = kw.get("_new_name")

        # _spec_asyncs 是一个限定对象的异步方法,
        # 如果 _new_name 与限定对象的方法名一致, 那么就实例化并返回一个 AsyncMock 对象.
        if _new_name in self.__dict__['_spec_asyncs']:
            return AsyncMock(**kw)

        # 当前实例的类对象, 举例: <class unittest.mock.Mock>
        # 重点: 下面这段代码定义了 AsyncMock , MagicMock, Mock 的关系树.
        _type = type(self)

        # 如果当前类对象继承了MagicMock 并且 _new_name 属于 _async_method_magics 范围, 那么 klass 就是一个 AsyncMock 类对象.
        if issubclass(_type, MagicMock) and _new_name in _async_method_magics:
            # Any asynchronous magic becomes an AsyncMock
            klass = AsyncMock

        # 当前类对象继承了AsyncMockMixin.
        elif issubclass(_type, AsyncMockMixin):
            # Any synchronous method on AsyncMock becomes a MagicMock
            # 继承了AsyncMockMixin的类的对象如果含有任意同步的方法, 那么这个类就属于MagicMock类.
            # 重点: 这就是 MagicMock 的定义.
            if (_new_name in _all_sync_magics or
                    self._mock_methods and _new_name in self._mock_methods):
                # Any synchronous method on AsyncMock becomes a MagicMock
                klass = MagicMock
            # 继承了AsyncMockMixin的类的对象不包含任何同步的方法, 那么这个类就属于AsyncMock类.
            else:
                klass = AsyncMock

        elif not issubclass(_type, CallableMixin):
            if issubclass(_type, NonCallableMagicMock):
                klass = MagicMock
            elif issubclass(_type, NonCallableMock):
                klass = Mock

        else:
            klass = _type.__mro__[1]

        # 当 self._mock_sealed 是 False 时, 表示当访问不存在的属性时创建子mock并返回该子mock对象.
        # 当 self._mock_sealed 是 True 时, 表示当访问不存在的属性时不创建子mock对象并抛出异常.
        if self._mock_sealed:
            attribute = "." + kw["name"] if "name" in kw else "()"
            mock_name = self._extract_mock_name() + attribute
            raise AttributeError(mock_name)

        return klass(**kw)

    ###################################################################################################################
    # _calls_repr(self, prefix="Calls")
    # 该方法用于返回一个格式化的字符串, 格式为:
    # "\nCalls: [call(1), call(2), call(3), call(4 [truncated]..."
    # 这里使用了 safe_repr 来限定输出的长度为80, 超出80用 ' [truncated]...' 来显示.
    ###################################################################################################################
    def _calls_repr(self, prefix="Calls"):
        """Renders self.mock_calls as a string.

        Example: "\nCalls: [call(1), call(2)]."

        If self.mock_calls is empty, an empty string is returned. The
        output will be truncated if very long.
        """
        if not self.mock_calls:
            return ""
        return f"\n{prefix}: {safe_repr(self.mock_calls)}."



def _try_iter(obj):
    if obj is None:
        return obj
    if _is_exception(obj):
        return obj
    if _callable(obj):
        return obj
    try:
        return iter(obj)
    except TypeError:
        # XXXX backwards compatibility
        # but this will blow up on first call - so maybe we should fail early?
        return obj


#######################################################################################################################
# class CallableMixin(Base)
# 继承了该类的Mock对象才能通过调用Mock来触发 __call__ 函数, 从而才能完成一系列的统计信息的记录.
#######################################################################################################################
class CallableMixin(Base):

    def __init__(self, spec=None, side_effect=None, return_value=DEFAULT,
                 wraps=None, name=None, spec_set=None, parent=None,
                 _spec_state=None, _new_name='', _new_parent=None, **kwargs):
        self.__dict__['_mock_return_value'] = return_value
        _safe_super(CallableMixin, self).__init__(
            spec, wraps, name, spec_set, parent,
            _spec_state, _new_name, _new_parent, **kwargs
        )

        self.side_effect = side_effect


    def _mock_check_sig(self, /, *args, **kwargs):
        # stub method that can be replaced with one with a specific signature
        pass


    def __call__(self, /, *args, **kwargs):
        # can't use self in-case a function / method we are mocking uses self
        # in the signature
        self._mock_check_sig(*args, **kwargs)
        self._increment_mock_call(*args, **kwargs)
        return self._mock_call(*args, **kwargs)


    def _mock_call(self, /, *args, **kwargs):
        return self._execute_mock_call(*args, **kwargs)

    ###################################################################################################################
    #
    # _increment_mock_call
    # 该函数用于记录和保存mock调用的次数、调用时传递的参数.
    #
    # _Call 由于它继承了 Tuple, 所以它本身也是一个Tuple, 用于将参数组合定义成一个对象,
    # 并且赋予这个对象一系列的操作能力(例如: ==操作, __repr__定制显示, index, count等功能)
    #
    # #################################################################################################################
    def _increment_mock_call(self, /, *args, **kwargs):
        self.called = True
        # 记录mock调用的次数
        self.call_count += 1

        # 将args和kwargs包裹成一个_call对象
        # 然后将_call对象保存到 call_args_list 集合中保存起来.
        # handle call_args
        # needs to be set here so assertions on call arguments pass before
        # execution in the case of awaited calls
        _call = _Call((args, kwargs), two=True)
        self.call_args = _call
        self.call_args_list.append(_call)

        # 这两行代码不应该放在这里, 应该放在_new_parent = self._mock_new_parent 一起.
        # initial stuff for method_calls:
        do_method_calls = self._mock_parent is not None
        method_call_name = self._mock_name

        # 这两行代码不应该放在这里, 应该放在_new_parent = self._mock_new_parent 一起.
        # initial stuff for mock_calls:
        mock_call_name = self._mock_new_name
        is_a_call = mock_call_name == '()'

        # 将所有mock调用的参数都收集到self.mock_calls集合中.
        self.mock_calls.append(_Call(('', args, kwargs)))

        # TODO: 由于尚未深入到 mock 链, 所以暂时不分析这里.
        # follow up the chain of mocks:
        _new_parent = self._mock_new_parent
        while _new_parent is not None:

            # handle method_calls:
            if do_method_calls:
                _new_parent.method_calls.append(_Call((method_call_name, args, kwargs)))
                do_method_calls = _new_parent._mock_parent is not None
                if do_method_calls:
                    method_call_name = _new_parent._mock_name + '.' + method_call_name

            # handle mock_calls:
            this_mock_call = _Call((mock_call_name, args, kwargs))
            _new_parent.mock_calls.append(this_mock_call)

            if _new_parent._mock_new_name:
                if is_a_call:
                    dot = ''
                else:
                    dot = '.'
                is_a_call = _new_parent._mock_new_name == '()'
                mock_call_name = _new_parent._mock_new_name + dot + mock_call_name

            # follow the parental chain:
            _new_parent = _new_parent._mock_new_parent

    ###############################################################################################
    # _execute_mock_call
    # 该函数通过三种可选方式来返回一个特定的值(用于替代那些当前网络访问不到的接口或数据).
    # 1. self.side_effect
    # 2. self.return_value
    # 3. self._mock_wraps
    # 这三种方式依次按照排列的优先级来决定返回值, 比如说当三个值都提供时, 会优先返回self.side_effect的值,
    # 如果self.side_effect不满足返回值条件那么在考虑 self.return_value, 以此类推.
    #
    # self.side_effect: 这个变量可能有三个值(ExceptionObject / IterableObject / CallableObject),
    #                   1. 当值为: ExceptionObject 时, 抛出这个异常.
    #                   2. 当值为: IterableObject 时, 使用 next() 去提取集合中的值.
    #                   3. 当值为: CallableObject 时, 执行这个函数.
    #
    # self._mock_return_value: 是实例化 Mock 或 MagicMock 时指定参数 return_value 的实体,
    #                          如果未指定那么默认就是 sentinel.DEFAULT 值.
    #
    # self._mock_wraps: 是实例化 Mock 或 MagicMock 时指定参数 wraps 的实体, 如果未指定默认是None值.
    #
    # self.return_value: 这个值跟 self._mock_return_value 使用的是同一个值.
    ###############################################################################################
    def _execute_mock_call(self, /, *args, **kwargs):
        # separate from _increment_mock_call so that awaited functions are
        # executed separately from their call, also AsyncMock overrides this method

        # 1. 如果实例化Mock或者MagicMock时提供了side_effect参数值,
        # 那么mock就根据side_effect的值类型来返回具体的值(模拟值).
        effect = self.side_effect
        if effect is not None:
            if _is_exception(effect):
                raise effect
            elif not _callable(effect):
                result = next(effect)
                if _is_exception(result):
                    raise result
            else:
                result = effect(*args, **kwargs)

            if result is not DEFAULT:
                return result

        # 2. 如果实例化Mock或折MagicMock时没有提供side_effect参数值,
        #    接着mock就检查实例化时是否提供了 return_value 参数值,
        #    供了 return_value 那么就返回return_value.
        if self._mock_return_value is not DEFAULT:
            return self.return_value

        # 3. 如果上面两个都没有提供, 则mock会检查实例化时是否提供了 wraps 参数值,
        #    提供了就去执行这个wraps函数, 具体的返回值由这个wraps函数来控制.
        if self._mock_wraps is not None:
            return self._mock_wraps(*args, **kwargs)

        # 4. 如果上面的所有参数都没有提供, 那么就返回一个 return_value (默认时None).
        return self.return_value


#######################################################################################################################
# class Mock(CallableMixin, NonCallableMock)
# 该类是一个空类, 其作用是一个helper类对象, 简化使用者的使用和理解成本.
#######################################################################################################################
class Mock(CallableMixin, NonCallableMock):
    """
    Create a new `Mock` object. `Mock` takes several optional arguments
    that specify the behaviour of the Mock object:

    * `spec`: This can be either a list of strings or an existing object (a
      class or instance) that acts as the specification for the mock object. If
      you pass in an object then a list of strings is formed by calling dir on
      the object (excluding unsupported magic attributes and methods). Accessing
      any attribute not in this list will raise an `AttributeError`.

      If `spec` is an object (rather than a list of strings) then
      `mock.__class__` returns the class of the spec object. This allows mocks
      to pass `isinstance` tests.

    * `spec_set`: A stricter variant of `spec`. If used, attempting to *set*
      or get an attribute on the mock that isn't on the object passed as
      `spec_set` will raise an `AttributeError`.

    * `side_effect`: A function to be called whenever the Mock is called. See
      the `side_effect` attribute. Useful for raising exceptions or
      dynamically changing return values. The function is called with the same
      arguments as the mock, and unless it returns `DEFAULT`, the return
      value of this function is used as the return value.

      If `side_effect` is an iterable then each call to the mock will return
      the next value from the iterable. If any of the members of the iterable
      are exceptions they will be raised instead of returned.

    * `return_value`: The value returned when the mock is called. By default
      this is a new Mock (created on first access). See the
      `return_value` attribute.

    * `wraps`: Item for the mock object to wrap. If `wraps` is not None then
      calling the Mock will pass the call through to the wrapped object
      (returning the real result). Attribute access on the mock will return a
      Mock object that wraps the corresponding attribute of the wrapped object
      (so attempting to access an attribute that doesn't exist will raise an
      `AttributeError`).

      If the mock has an explicit `return_value` set then calls are not passed
      to the wrapped object and the `return_value` is returned instead.

    * `name`: If the mock has a name then it will be used in the repr of the
      mock. This can be useful for debugging. The name is propagated to child
      mocks.

    Mocks can also be called with arbitrary keyword arguments. These will be
    used to set attributes on the mock after it is created.
    """


#######################################################################################################################
# _dot_lookup(thing, comp, import_path)
# 从thing参数中提取comp属性.
#######################################################################################################################
def _dot_lookup(thing, comp, import_path):
    try:
        # 尝试从thing参数(当前级模块)中提取comp属性
        return getattr(thing, comp)
    except AttributeError:
        # 如果提取失败那么尝试加载下一级模块并从下一级模块中提取comp属性并返回
        #
        # 踩坑:
        # 这里重新按照 import_path 再去加载下一级模块, 但是并没有赋值给thing.
        # 但是经过测试加载下一级模块会持续更新到thing变量中.
        __import__(import_path)
        return getattr(thing, comp)


#######################################################################################################################
# _importer(target)
# 该函数用于将字符串导入成module对象.
#######################################################################################################################
def _importer(target):
    components = target.split('.')
    import_path = components.pop(0)

    # 踩坑:
    # __import__ 有个特点: 如果当前文件有使用了 import 语句导入了与 import_path
    #                     字符串一样的模块, 那么__import__也会将这个子模块纳入到thing模块中, 举例说明:
    #
    # 常规情况下, 使用 __import__('unittest') 它并不会去包含 mock 属性,
    # 因为 unittest.__init__.py 文件中并没有声明 mock 对象, 举例:
    #
    # def main():
    #     thing = __import__('unittest')
    #     print(thing)
    #     print(dir(thing))
    #
    # if __name__ == '__main__':
    #     main()
    #
    # 输出结果中并不包含mock对象:
    # <module 'unittest' from 'C:\\Python38\\lib\\unittest\\__init__.py'>
    # ['BaseTestSuite', 'FunctionTestCase', 'IsolatedAsyncioTestCase', 'SkipTest', 'TestCase', 'TestLoader',
    # 'TestProgram', 'TestResult', 'TestSuite', 'TextTestResult', 'TextTestRunner', '_TextTestResult', '__all__',
    # '__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__path__',
    # '__spec__', '__unittest', 'addModuleCleanup', 'async_case', 'case', 'defaultTestLoader', 'expectedFailure',
    # 'findTestCases', 'getTestCaseNames', 'installHandler', 'load_tests', 'loader', 'main', 'makeSuite',
    # 'registerResult', 'removeHandler', 'removeResult', 'result', 'runner', 'signals', 'skip', 'skipIf',
    # 'skipUnless', 'suite', 'util']
    #
    #
    # 但是如果当前文件头部使用了 import unittest.mock 语句, 那么 __import__('unittest') 的返回结果中,
    # 就会包含 mock 属性, 它内部的算法应该时把当前环境变量中前缀一样的变量纳入到返回对象中, 举例:
    #
    # import unittest
    # def ssse(): pass
    # unittest.ssse = ssse                          # 必须是函数, 如果是变量那么__import__不会纳入到返回对象中.
    #
    # def main():
    #     thing = __import__('unittest')
    #     print(thing)
    #     print(dir(thing))
    #
    # if __name__ == '__main__':
    #     main()
    #
    # 输出结果中包含了ssse:
    # <module 'unittest' from 'C:\\Python38\\lib\\unittest\\__init__.py'>
    # ['BaseTestSuite', 'FunctionTestCase', 'IsolatedAsyncioTestCase', 'SkipTest', 'TestCase', 'TestLoader',
    # 'TestProgram', 'TestResult', 'TestSuite', 'TextTestResult', 'TextTestRunner', '_TextTestResult', '__all__',
    # '__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__path__',
    # '__spec__', '__unittest', 'addModuleCleanup', 'async_case', 'case', 'defaultTestLoader', 'expectedFailure',
    # 'findTestCases', 'getTestCaseNames', 'installHandler', 'load_tests', 'loader', 'main', 'makeSuite',
    # 'registerResult', 'removeHandler', 'removeResult', 'result', 'runner', 'signals', 'skip', 'skipIf',
    # 'skipUnless', 'ssse', 'suite', 'util']
    thing = __import__(import_path)

    # 为了保守起见, 这里以穷尽的形式去尝试加载模块, 例如:
    # target = 'unittest.test.testmock.testpatch'
    # import_path = 'unittest'
    # components: ['test', 'testmock', 'testpatch']
    for comp in components:
        # 第一次遍历
        # comp = 'test'
        # import_path = 'unittest.test'
        # thing = _do_lookup(<module 'unittest' from '..\\unittest\\__init__.py'>, 'test', 'unittest.test')
        # thing: <module 'unittest.test' from '..\\unittest\\test\\__init__.py'>
        #
        # 第二次遍历
        # comp = 'testmock'
        # import_path = 'unittest.test.testmock'
        # thing = _do_lookup(<module 'unittest.test' from '..\\unittest\\test\\__init__.py'>,
        #                    'testmock',
        #                    'unittest.test.testmock')
        # thing: <module 'unittest.test.testmock' from '..\\unittest\\test\\testmock\\__init__.py'>
        #
        # 第三次遍历
        # comp = 'testpatch'
        # import_path = 'unittest.test.testmock.testpatch'
        # thing = _do_lookup(<module 'unittest.test.testmock' from '..\\unittest\\test\\testmock\\__init__.py'>,
        #                    'testpatch',
        #                    'unittest.test.testmock.testpatch')
        # thing: <module 'unittest.test.testmock.testpatch' from
        #        'C:\\Python38\\lib\\unittest\\test\\testmock\\testpatch.py'>
        import_path += ".%s" % comp
        thing = _dot_lookup(thing, comp, import_path)
    return thing


#######################################################################################################################
# _is_started(patcher)
# 该函数用于检查和判断 patcher 对象是否拥有 is_local 属性,
# 如果已经拥有 is_local 属性则表示这个patcher已经执行过 start 方法了.
# 如果尚未拥有 is_local 属性则表示这个patcher还没有执行过 start 方法.
#######################################################################################################################
def _is_started(patcher):
    # XXXX horrible
    return hasattr(patcher, 'is_local')


class _patch(object):

    attribute_name = None
    _active_patches = []

    ###################################################################################################################
    # __init__
    # 该方法例行检查参数new_callable和new/autospec参数是否冲突, 其他就是将参数赋值到self实例中(同名).
    ###################################################################################################################
    def __init__(
            self, getter, attribute, new, spec, create,
            spec_set, autospec, new_callable, kwargs
        ):

        # new_callable 参数 和 new / autospec 参数同时设定会发生冲突.
        # TODO: 需要说明为什么会发生冲突.
        if new_callable is not None:
            if new is not DEFAULT:
                raise ValueError(
                    "Cannot use 'new' and 'new_callable' together"
                )
            if autospec is not None:
                raise ValueError(
                    "Cannot use 'autospec' and 'new_callable' together"
                )

        self.getter = getter
        self.attribute = attribute
        self.new = new
        self.new_callable = new_callable
        self.spec = spec
        self.create = create
        self.has_local = False
        self.spec_set = spec_set
        self.autospec = autospec
        self.kwargs = kwargs
        self.additional_patchers = []

    ###################################################################################################################
    # copy(self)
    # 该方法用于复制patch对象.
    # 复制的逻辑是:
    # 1. 将 self 的属性来重新创建一个_patch对象.
    # 2. 将 self 的 attribute_name 赋值给 新patch 对象.
    # 3. 递归赋值 self.addtional_patchers 给 新patch.addtional_patchers;
    #    这里采用 p.copy() for p in self.addtional_patchers 的方式, 实现了deep-copy, 而不是shadow-copy.
    ###################################################################################################################
    def copy(self):
        patcher = _patch(
            self.getter, self.attribute, self.new, self.spec,
            self.create, self.spec_set,
            self.autospec, self.new_callable, self.kwargs
        )
        patcher.attribute_name = self.attribute_name
        patcher.additional_patchers = [
            p.copy() for p in self.additional_patchers
        ]
        return patcher

    ###################################################################################################################
    # __call__(self, func)
    # 该方法是一个魔法方法, p = _patch(*args, **kwargs); p(); 第二步的p()就会触发__call__方法.
    # 该方法的作用是被当作装饰器来使用(因为它的参数 func 就是为了接收函数), 作为patch的入口, 通过该入口延申完成替换对象的创建.
    ###################################################################################################################
    def __call__(self, func):
        # 当 func 类型是 type 时, 说明它是一个类对象.
        if isinstance(func, type):
            return self.decorate_class(func)

        # 当 func 类型时 async function 时, 说明他时一个异步函数对象.
        if inspect.iscoroutinefunction(func):
            return self.decorate_async_callable(func)

        # 当 func 类型是 function 时, 说明他是一个函数对象.
        return self.decorate_callable(func)

    def decorate_class(self, klass):
        for attr in dir(klass):
            if not attr.startswith(patch.TEST_PREFIX):
                continue

            attr_value = getattr(klass, attr)
            if not hasattr(attr_value, "__call__"):
                continue

            patcher = self.copy()
            setattr(klass, attr, patcher(attr_value))
        return klass

    ###################################################################################################################
    # decoration_helper(self, patched, args, keywargs)
    # 该方法用于生成一组参数, 这组参数用于返回给使用了@patch装饰器的函数, 即:
    # from unittest.mock import patch, MagicMock
    #
    # @patch('operator.mul')
    # def main(mul):                           # decoration_helper 生成参数返回给 main 函数.
    #     assert isinstance(mul, MagicMock)
    #
    # if __name__ == '__main__':
    #     main()
    #
    # 关于 @contextlib.contextmanager 装饰器的作用, 加上这个装饰器之后让 decoration_helper 方法
    # 支持了 with decoration_helper(...) as (args, kwargs) 写法,
    # 支持 with 写法的好处是, contextmanager 帮忙try exception 兜底异常, 并且帮忙清理 with 作用域中产生变量.
    ###################################################################################################################
    @contextlib.contextmanager
    def decoration_helper(self, patched, args, keywargs):
        extra_args = []
        entered_patchers = []
        patching = None

        exc_info = tuple()
        try:
            for patching in patched.patchings:
                # patching 是一个 _patch 对象, _patch.__enter__() 将会
                # 返回一个 MagicMock 的实例对象或 AsyncMock 的实例对象.
                arg = patching.__enter__()

                # 这里标记, patching 这个对象已经执行了 __enter__ 函数, mock对象已经生成完毕.
                entered_patchers.append(patching)

                # 如果 patching.attribute_name 的值存在, 那么就把这个值写入到 keywargs 中当作参数返回给上层函数.
                if patching.attribute_name is not None:
                    keywargs.update(arg)

                # 如果 patching.new 是默认值, 那么就将 mock 当作参数返回给上层函数.
                elif patching.new is DEFAULT:
                    extra_args.append(arg)

            args += tuple(extra_args)

            # 这里使用 yield 的原因是, 为了配合 contextmanager 的运行机制.
            # contextmanager.__enter__() 触发前半部分的yield代码,
            yield (args, keywargs)
        except:
            if (patching not in entered_patchers and
                _is_started(patching)):
                # the patcher may have been started, but an exception
                # raised whilst entering one of its additional_patchers
                entered_patchers.append(patching)
            # Pass the exception to __exit__
            exc_info = sys.exc_info()
            # re-raise the exception
            raise
        finally:
            # contextmanager.__exit__() 触发后半部分的yield代码.
            for patching in reversed(entered_patchers):
                patching.__exit__(*exc_info)

    ###################################################################################################################
    # decorate_callable(self, func)
    # 这是一个装饰器函数, 封装了具体创建对象的函数的逻辑.
    ###################################################################################################################
    def decorate_callable(self, func):
        # NB. Keep the method in sync with decorate_async_callable()
        # 当 func 拥有 patchings 属性时, 表示这个函数已经
        # 是一个替换过的对象了, 所以直接返回这个func即可.
        if hasattr(func, 'patchings'):
            func.patchings.append(self)
            return func

        # 这里使用wraps主要是为了保留func对象的信息(保存在patched.__wrapped__中),
        # 通过__wrapped__属性可以看到原始func的哪个函数.
        @wraps(func)
        def patched(*args, **keywargs):
            # 前面从patch到_patch.__call__到这里, 一直是框架性流转代码,
            # 进入self.decoration_helper才是具体创建对象的逻辑(是MagicMock还是AsyncMock还是new).
            with self.decoration_helper(patched,
                                        args,
                                        keywargs) as (newargs, newkeywargs):
                return func(*newargs, **newkeywargs)

        # 为装饰器 patched 函数添加 patchings 属性, 用于表示当前这个函数已经patch过了.
        patched.patchings = [self]
        return patched

    ###################################################################################################################
    # decorate_async_callable(self, func)
    # 这是一个装饰器函数, 代码与 decorate_callable 一致, 区别是装饰器函数上上 async 和 await 关键字.
    ###################################################################################################################
    def decorate_async_callable(self, func):
        # NB. Keep the method in sync with decorate_callable()
        if hasattr(func, 'patchings'):
            func.patchings.append(self)
            return func

        @wraps(func)
        async def patched(*args, **keywargs):
            with self.decoration_helper(patched,
                                        args,
                                        keywargs) as (newargs, newkeywargs):
                return await func(*newargs, **newkeywargs)

        patched.patchings = [self]
        return patched

    ###################################################################################################################
    # get_original(self)
    # 该方法用于提取 _get_target 没有直接提取的结果.
    ###################################################################################################################
    def get_original(self):
        # target 是一个 module 对象
        # name 是这个 module 对象中的一个函数/类/方法的名字
        target = self.getter()
        name = self.attribute

        original = DEFAULT
        local = False

        try:
            # 从 target 模块中提取 name 这个类对象.
            original = target.__dict__[name]
        except (AttributeError, KeyError):
            original = getattr(target, name, DEFAULT)
        else:
            # local == True 表示 从 target 这模块中获取 name 这个方法是无报错的.
            # 当 local == True 时, original也是一个具体的类.
            local = True

        if name in _builtins and isinstance(target, ModuleType):
            self.create = True

        # 如果 name 即不是内置函数名, 也不是target模块中的 函数/类/方法 的名字, 那么就抛出异常.
        if not self.create and original is DEFAULT:
            raise AttributeError(
                "%s does not have the attribute %r" % (target, name)
            )

        return original, local

    ###################################################################################################################
    # __enter__(self)
    # 创建mock对象, 用于替换patch时提供的原函数字符串参数.
    ###################################################################################################################
    def __enter__(self):
        """Perform the patch."""
        new, spec, spec_set = self.new, self.spec, self.spec_set
        autospec, kwargs = self.autospec, self.kwargs
        new_callable = self.new_callable
        self.target = self.getter()

        # normalise False to None
        if spec is False:
            spec = None
        if spec_set is False:
            spec_set = None
        if autospec is False:
            autospec = None

        # spec 和 autospec 这两个参数不可以同时提供.
        if spec is not None and autospec is not None:
            raise TypeError("Can't specify spec and autospec")

        # 由于上面 spec_set is False 时, spec_set 被设定为 None.
        # 所以: 当 spec_set 不是 True 也不是None 时, 一定是一个类对象.
        #
        # 如果 spec_set 和 spec 参数同时提供, 那么就报错.
        # 如果 spec_set 和 autospec 参数同时提供, 那么就报错.
        if ((spec is not None or autospec is not None) and
            spec_set not in (True, None)):
            raise TypeError("Can't provide explicit spec_set *and* spec or autospec")

        # 提取 _get_target 没有直接提取的结果.
        # original 将会被写入到 spec 或 spec_set 限定对象.
        original, local = self.get_original()

        # 这是最常见的条件入口: 当new是默认值, autospec是None时(也是默认值), 进入这个条件块.
        if new is DEFAULT and autospec is None:
            inherit = False

            # 如果 spec 限定参数是True, 那么就将original这个对象当作 spec 对象.
            if spec is True:
                # set spec to the object we are replacing
                spec = original
                # 如果 spec 和 spec_set 同时都设定为True, 那么就以 spec_set 为主.
                if spec_set is True:
                    spec_set = original
                    spec = None

            # 如果 spec 不是True, 也不是 None, 那就是一个对象.
            elif spec is not None:
                # 如果 spec_set 是 True, 那么就以 spec_set 为主.
                if spec_set is True:
                    spec_set = spec
                    spec = None

            # 如果 spec_set 是 True, 那么就以 spec_set 为主.
            elif spec_set is True:
                spec_set = original

            # TODO: 看不懂
            if spec is not None or spec_set is not None:
                if original is DEFAULT:
                    raise TypeError("Can't use 'spec' with create=True")
                if isinstance(original, type):
                    # If we're patching out a class and there is a spec
                    inherit = True

            # 如果 original (被替换的对象) 是一个异步对象, 那么就准备 AsyncMock 对象.
            if spec is None and _is_async_obj(original):
                Klass = AsyncMock
            else:
                Klass = MagicMock

            _kwargs = {}

            # new_callable 的优先级高于 spec 和 spec_set.
            if new_callable is not None:
                Klass = new_callable

            # 如果 spec 或 spec_set 是一个对象.
            elif spec is not None or spec_set is not None:
                this_spec = spec
                if spec_set is not None:
                    this_spec = spec_set

                # 如果 this_spec 是一个列表或元组, 那么表示它是一个 dir() 列表,
                # 如果 __call__ 不在 dir() 范围内， 表示这个spec是不可调用对象.
                if _is_list(this_spec):
                    not_callable = '__call__' not in this_spec

                # 如果 this_spec 是一个对象.
                # 如果 this_spec 不可调用,
                else:
                    not_callable = not callable(this_spec)

                # 如果 this_spec 是一个异步对象, 那么 klass 是 AsyncMock
                if _is_async_obj(this_spec):
                    Klass = AsyncMock

                # 如果 not_callable 为True, 那么klass 就是 NonCallableMagicMock
                elif not_callable:
                    Klass = NonCallableMagicMock

            # 接下来的代码是为 klass 准备参数.
            if spec is not None:
                _kwargs['spec'] = spec
            if spec_set is not None:
                _kwargs['spec_set'] = spec_set

            # add a name to mocks
            if (isinstance(Klass, type) and
                issubclass(Klass, NonCallableMock) and self.attribute):
                _kwargs['name'] = self.attribute

            # 实例化一个mock, original 会被写入到 _kwargs['spec'] 或 _kwargs['spec_set'] 中当作参数传递给mock.
            # 即: mock 虽然是一个替代对象, 但也仍然保留了原始对象在 spec
            _kwargs.update(kwargs)
            new = Klass(**_kwargs)

            # TODO: 待补充
            if inherit and _is_instance_mock(new):
                # we can only tell if the instance should be callable if the
                # spec is not a list
                this_spec = spec
                if spec_set is not None:
                    this_spec = spec_set
                if (not _is_list(this_spec) and not
                    _instance_callable(this_spec)):
                    Klass = NonCallableMagicMock

                _kwargs.pop('name')
                new.return_value = Klass(_new_parent=new, _new_name='()',
                                         **_kwargs)

        # 如果提供了 autospec 参数, 将会采用 create_autospec 来创建 mock 对象.
        elif autospec is not None:
            # spec is ignored, new *must* be default, spec_set is treated
            # as a boolean. Should we check spec is not None and that spec_set
            # is a bool?
            if new is not DEFAULT:
                raise TypeError(
                    "autospec creates the mock for you. Can't specify "
                    "autospec and new."
                )
            if original is DEFAULT:
                raise TypeError("Can't use 'autospec' with create=True")
            spec_set = bool(spec_set)
            if autospec is True:
                autospec = original

            new = create_autospec(autospec, spec_set=spec_set,
                                  _name=self.attribute, **kwargs)
        elif kwargs:
            # can't set keyword args when we aren't creating the mock
            # XXXX If new is a Mock we could call new.configure_mock(**kwargs)
            raise TypeError("Can't pass kwargs to a mock we aren't creating")

        # new 是已经实例化的mock对象.
        new_attr = new

        # original 除了留存在 mock.spec 中, 也会留存在 _patch.temp_original 中.
        self.temp_original = original

        # self.is_local 用于标记已经执行过 __enter__ 了.
        self.is_local = local

        # self.target 是一个module.
        # 这里将 这个mock 对象写入到 self.target[self.attribute] = new_attr 中.
        setattr(self.target, self.attribute, new_attr)

        # TODO: 待补充
        if self.attribute_name is not None:
            extra_args = {}
            if self.new is DEFAULT:
                extra_args[self.attribute_name] =  new
            for patching in self.additional_patchers:
                arg = patching.__enter__()
                if patching.new is DEFAULT:
                    extra_args.update(arg)
            return extra_args

        # 返回 mock 对象.
        return new

    ###################################################################################################################
    # __exit__(self, *exc_info)
    # 回滚patch替换.
    # 1. 将 self.target 这个module 中的 self.attribute(原始函数名) 名字恢复成 self.temp_original(原始函数) 函数.
    # 2. 删除 self.temp_original
    # 3. 删除 self.is_local
    # 4. 删除 self.target 模块
    # 5. 递归回滚所有子patcher
    ###################################################################################################################
    def __exit__(self, *exc_info):
        """Undo the patch."""
        if not _is_started(self):
            return

        if self.is_local and self.temp_original is not DEFAULT:
            setattr(self.target, self.attribute, self.temp_original)
        else:
            delattr(self.target, self.attribute)
            if not self.create and (not hasattr(self.target, self.attribute) or
                        self.attribute in ('__doc__', '__module__',
                                           '__defaults__', '__annotations__',
                                           '__kwdefaults__')):
                # needed for proxy objects like django settings
                setattr(self.target, self.attribute, self.temp_original)

        del self.temp_original
        del self.is_local
        del self.target
        for patcher in reversed(self.additional_patchers):
            if _is_started(patcher):
                patcher.__exit__(*exc_info)

    ###################################################################################################################
    # start(self)
    # 该方法用于那些不采用 with 的场景(即: 装饰器)来返回mock对象.
    ###################################################################################################################
    def start(self):
        """Activate a patch, returning any created mock."""
        result = self.__enter__()
        self._active_patches.append(self)
        return result

    ###################################################################################################################
    # stop(self)
    # 该方法用于那些不采用 with 的场景(即: 装饰器)来返回mock对象.
    ###################################################################################################################
    def stop(self):
        """Stop an active patch."""
        try:
            self._active_patches.remove(self)
        except ValueError:
            # If the patch hasn't been started this will fail
            pass

        return self.__exit__()


#######################################################################################################################
# _get_target(target)
# 该函数用于拆分模块和对象.
# 返回值: 模块(类型: lambda), 对象(类型: 字符串)
#######################################################################################################################
def _get_target(target):
    # talist = 'unittest.mock.Mock'.rsplit(sep='.', maxsplit=1)
    # talist == ['unittest.mock', 'Mock']
    try:
        target, attribute = target.rsplit('.', 1)
    except (TypeError, ValueError):
        raise TypeError("Need a valid target to patch. You supplied: %r" %
                        (target,))

    # 这是因为定义_patch时, 需要考虑结果除了时module对象之外,
    # 还有可能是类的实例对象, 甚至可能是字符串, 所以可能是为了类型统一, 将其定义为 lambda 匿名函数.
    getter = lambda: _importer(target)
    return getter, attribute


#######################################################################################################################
# _patch_object(target, attribute, new=DEFAULT, spec=None,
#               create=False, spec_set=None, autospec=None,
#               new_callable=None, **kwargs)
# 该函数用于patch一个对象, 在这个函数中省略了 get_import 环节的代码
#######################################################################################################################
def _patch_object(
        target, attribute, new=DEFAULT, spec=None,
        create=False, spec_set=None, autospec=None,
        new_callable=None, **kwargs
    ):
    """
    patch the named member (`attribute`) on an object (`target`) with a mock
    object.

    `patch.object` can be used as a decorator, class decorator or a context
    manager. Arguments `new`, `spec`, `create`, `spec_set`,
    `autospec` and `new_callable` have the same meaning as for `patch`. Like
    `patch`, `patch.object` takes arbitrary keyword arguments for configuring
    the mock object it creates.

    When used as a class decorator `patch.object` honours `patch.TEST_PREFIX`
    for choosing which methods to wrap.
    """
    if type(target) is str:
        raise TypeError(
            f"{target!r} must be the actual object to be patched, not a str"
        )
    getter = lambda: target
    return _patch(
        getter, attribute, new, spec, create,
        spec_set, autospec, new_callable, kwargs
    )


#######################################################################################################################
# _patch_multiple(target, spec=None, create=False, spec_set=None,
#                 autospec=None, new_callable=None, **kwargs)
# 该函数用于创建多个patch, 即: 替换多个函数或方法.
# 根据kwargs参数来创建patch, 取任意一组item来当作主patch, 其他的当作副patch放在主patch.additional_patchers中.
#######################################################################################################################
def _patch_multiple(target, spec=None, create=False, spec_set=None,
                    autospec=None, new_callable=None, **kwargs):
    """Perform multiple patches in a single call. It takes the object to be
    patched (either as an object or a string to fetch the object by importing)
    and keyword arguments for the patches::

        with patch.multiple(settings, FIRST_PATCH='one', SECOND_PATCH='two'):
            ...

    Use `DEFAULT` as the value if you want `patch.multiple` to create
    mocks for you. In this case the created mocks are passed into a decorated
    function by keyword, and a dictionary is returned when `patch.multiple` is
    used as a context manager.

    `patch.multiple` can be used as a decorator, class decorator or a context
    manager. The arguments `spec`, `spec_set`, `create`,
    `autospec` and `new_callable` have the same meaning as for `patch`. These
    arguments will be applied to *all* patches done by `patch.multiple`.

    When used as a class decorator `patch.multiple` honours `patch.TEST_PREFIX`
    for choosing which methods to wrap.
    """

    # 如果 target 是字符串, 那么就采用 _importer 去加载具体模块
    if type(target) is str:
        getter = lambda: _importer(target)

    # 如果不是字符串, 就视为是 module 对象.
    else:
        getter = lambda: target

    if not kwargs:
        raise ValueError(
            'Must supply at least one keyword argument with patch.multiple'
        )

    # need to wrap in a list for python 3, where items is a view
    # 第一个元素用来生成替换对象: 主patcher.
    items = list(kwargs.items())
    attribute, new = items[0]
    patcher = _patch(
        getter, attribute, new, spec, create, spec_set,
        autospec, new_callable, {}
    )
    patcher.attribute_name = attribute

    # 第二个和后续的元素, 用来创建其他(副)mock对象,
    # 然后将这些mock对象纳入到主patcher.additional_patchers中.
    for attribute, new in items[1:]:
        this_patcher = _patch(
            getter, attribute, new, spec, create, spec_set,
            autospec, new_callable, {}
        )
        this_patcher.attribute_name = attribute
        patcher.additional_patchers.append(this_patcher)

    # 返回主 patcher
    return patcher


#######################################################################################################################
# patch(target, new=DEFAULT, spec=None, create=False, spec_set=None, autospec=None, new_callable=None, **kwargs)
# 该函数用于当作装饰器来替换target对象,
# 如果提供了new参数, 那么就把target对象替换成new对象.
# 如果没有提供new参数, 那么就会把target对象替换成MagicMock对象或AsyncMock对象.
#
# patch本身只是一个函数, 并不具备装饰器能力, 因为它并没有接收 function 参数(python会将被装饰的对象传递进来),
# 之所以能被当作装饰器使用, 是因为它返回的_patch类中定义了__call__(self, func)来接收function参数.
#######################################################################################################################
def patch(
        target, new=DEFAULT, spec=None, create=False,
        spec_set=None, autospec=None, new_callable=None, **kwargs
    ):
    """
    `patch` acts as a function decorator, class decorator or a context
    manager. Inside the body of the function or with statement, the `target`
    is patched with a `new` object. When the function/with statement exits
    the patch is undone.

    If `new` is omitted, then the target is replaced with an
    `AsyncMock if the patched object is an async function or a
    `MagicMock` otherwise. If `patch` is used as a decorator and `new` is
    omitted, the created mock is passed in as an extra argument to the
    decorated function. If `patch` is used as a context manager the created
    mock is returned by the context manager.

    `target` should be a string in the form `'package.module.ClassName'`. The
    `target` is imported and the specified object replaced with the `new`
    object, so the `target` must be importable from the environment you are
    calling `patch` from. The target is imported when the decorated function
    is executed, not at decoration time.

    The `spec` and `spec_set` keyword arguments are passed to the `MagicMock`
    if patch is creating one for you.

    In addition you can pass `spec=True` or `spec_set=True`, which causes
    patch to pass in the object being mocked as the spec/spec_set object.

    `new_callable` allows you to specify a different class, or callable object,
    that will be called to create the `new` object. By default `AsyncMock` is
    used for async functions and `MagicMock` for the rest.

    A more powerful form of `spec` is `autospec`. If you set `autospec=True`
    then the mock will be created with a spec from the object being replaced.
    All attributes of the mock will also have the spec of the corresponding
    attribute of the object being replaced. Methods and functions being
    mocked will have their arguments checked and will raise a `TypeError` if
    they are called with the wrong signature. For mocks replacing a class,
    their return value (the 'instance') will have the same spec as the class.

    Instead of `autospec=True` you can pass `autospec=some_object` to use an
    arbitrary object as the spec instead of the one being replaced.

    By default `patch` will fail to replace attributes that don't exist. If
    you pass in `create=True`, and the attribute doesn't exist, patch will
    create the attribute for you when the patched function is called, and
    delete it again afterwards. This is useful for writing tests against
    attributes that your production code creates at runtime. It is off by
    default because it can be dangerous. With it switched on you can write
    passing tests against APIs that don't actually exist!

    Patch can be used as a `TestCase` class decorator. It works by
    decorating each test method in the class. This reduces the boilerplate
    code when your test methods share a common patchings set. `patch` finds
    tests by looking for method names that start with `patch.TEST_PREFIX`.
    By default this is `test`, which matches the way `unittest` finds tests.
    You can specify an alternative prefix by setting `patch.TEST_PREFIX`.

    Patch can be used as a context manager, with the with statement. Here the
    patching applies to the indented block after the with statement. If you
    use "as" then the patched object will be bound to the name after the
    "as"; very useful if `patch` is creating a mock object for you.

    `patch` takes arbitrary keyword arguments. These will be passed to
    the `Mock` (or `new_callable`) on construction.

    `patch.dict(...)`, `patch.multiple(...)` and `patch.object(...)` are
    available for alternate use-cases.
    """
    getter, attribute = _get_target(target)
    return _patch(
        getter, attribute, new, spec, create,
        spec_set, autospec, new_callable, kwargs
    )


###################################################################################################################
# class _patch_dict(object)
# 该类用于替换字典
###################################################################################################################
class _patch_dict(object):
    """
    Patch a dictionary, or dictionary like object, and restore the dictionary
    to its original state after the test.

    `in_dict` can be a dictionary or a mapping like container. If it is a
    mapping then it must at least support getting, setting and deleting items
    plus iterating over keys.

    `in_dict` can also be a string specifying the name of the dictionary, which
    will then be fetched by importing it.

    `values` can be a dictionary of values to set in the dictionary. `values`
    can also be an iterable of `(key, value)` pairs.

    If `clear` is True then the dictionary will be cleared before the new
    values are set.

    `patch.dict` can also be called with arbitrary keyword arguments to set
    values in the dictionary::

        with patch.dict('sys.modules', mymodule=Mock(), other_module=Mock()):
            ...

    `patch.dict` can be used as a context manager, decorator or class
    decorator. When used as a class decorator `patch.dict` honours
    `patch.TEST_PREFIX` for choosing which methods to wrap.
    """

    ###################################################################################################################
    # __init__(self, in_dict, values=(), clear=False, **kwargs)
    # 该方法是 _patch_dict 的初始化方方法
    # in_dict: 要被替换字典.
    # values: 预定义字典(patcher), 将in_dict原始字典保存到 self._original 中, 然后再将 values 写入到 self.in_dict 字典.
    # clear: 为True时, 清空self.in_dict后再将values写入self.in_dict;
    #        为False时, 不清空self.in_dict, 将self.values追加写入到 self.in_dict 字典.
    # kwargs: 写入到self.in_dict中.
    ###################################################################################################################
    def __init__(self, in_dict, values=(), clear=False, **kwargs):
        self.in_dict = in_dict
        # support any argument supported by dict(...) constructor
        self.values = dict(values)
        self.values.update(kwargs)
        self.clear = clear
        self._original = None

    ###################################################################################################################
    # __call__(self, f)
    # 该方法是object的内置方法(魔法方法), 在这里用于当作装饰器的入口; 参数 f 期望的类型是一个函数.
    ###################################################################################################################
    def __call__(self, f):
        if isinstance(f, type):
            return self.decorate_class(f)
        @wraps(f)
        def _inner(*args, **kw):
            self._patch_dict()
            try:
                return f(*args, **kw)
            finally:
                self._unpatch_dict()

        return _inner


    def decorate_class(self, klass):
        for attr in dir(klass):
            attr_value = getattr(klass, attr)
            if (attr.startswith(patch.TEST_PREFIX) and
                 hasattr(attr_value, "__call__")):
                decorator = _patch_dict(self.in_dict, self.values, self.clear)
                decorated = decorator(attr_value)
                setattr(klass, attr, decorated)
        return klass

    ###################################################################################################################
    # __enter__(self)
    # 该方法是object的内置方法(魔法方法), 在这里用于当作 with _patch_dict(...) as x: 关键字语法的入口.
    ###################################################################################################################
    def __enter__(self):
        """Patch the dict."""
        self._patch_dict()
        return self.in_dict

    ###################################################################################################################
    # _patch_dict(self)
    # 该方法是装饰器的入口, 用于替换dict对象.
    # 将原始的 字典数据 保存再 self._original 中, 然后将 self.values 的数据更新到 self.in_dict.
    # 再 with 关键字语句 / 装饰器 作用域中 操作的都是 self.in_dict 对象.
    ###################################################################################################################
    def _patch_dict(self):
        # self.values 是一个字典.
        values = self.values

        # 如果 self.in_dict 是字符串, 那么尝试去加载这个字典.
        if isinstance(self.in_dict, str):
            self.in_dict = _importer(self.in_dict)

        in_dict = self.in_dict
        clear = self.clear

        # 将原始值保存到 self._original 中.
        try:
            original = in_dict.copy()
        except AttributeError:
            # dict like object with no copy method
            # must support iteration over keys
            original = {}
            for key in in_dict:
                original[key] = in_dict[key]
        self._original = original

        # 如果 self.clear 为 True, 那么就清空 self.in_dict ; 这意味着在 patch 的作用域内 字典 被替换成空字典.
        # 如果 self.clear 为 False, 那么就保留 self.in_dict 字典; 这意味着在 patch 的作用域内 字典 与外部是一样的.
        if clear:
            _clear_dict(in_dict)

        # self.values 是实例化 _patch_dict 时提供的预定义值, 即: 再 self.in_dict 的基础上, 加上 values 的值.
        try:
            in_dict.update(values)
        except AttributeError:
            # dict like object with no update method
            for key in values:
                in_dict[key] = values[key]

    ###################################################################################################################
    # _unpatch_dict(self)
    # 该方法用于恢复替换对象.
    # 1. 清空 self.in_dict 字典
    # 2. 将 self._original 字典 写回到 self.in_dict 中.
    ###################################################################################################################
    def _unpatch_dict(self):
        in_dict = self.in_dict
        original = self._original

        # 清空 self.in_dict 字典
        _clear_dict(in_dict)

        # 将 self._original 字典 写回到 self.in_dict 中.
        try:
            in_dict.update(original)
        except AttributeError:
            for key in original:
                in_dict[key] = original[key]

    ###################################################################################################################
    # __exit__(self, *args)
    # 该方法是 with 关键字退出作用域时执行代码的hook钩子.
    ###################################################################################################################
    def __exit__(self, *args):
        """Unpatch the dict."""
        self._unpatch_dict()
        return False

    ###################################################################################################################
    # 这两个属性用于支持手写代码(面向过程型编码风格), 即: 不是装饰器语法风格, 也不是 with 语法风格.
    ###################################################################################################################
    start = __enter__
    stop = __exit__


def _clear_dict(in_dict):
    try:
        in_dict.clear()
    except AttributeError:
        keys = list(in_dict)
        for key in keys:
            del in_dict[key]


def _patch_stopall():
    """Stop all active patches. LIFO to unroll nested patches."""
    for patch in reversed(_patch._active_patches):
        patch.stop()


patch.object = _patch_object
patch.dict = _patch_dict
patch.multiple = _patch_multiple
patch.stopall = _patch_stopall
patch.TEST_PREFIX = 'test'

magic_methods = (
    "lt le gt ge eq ne "
    "getitem setitem delitem "
    "len contains iter "
    "hash str sizeof "
    "enter exit "
    # we added divmod and rdivmod here instead of numerics
    # because there is no idivmod
    "divmod rdivmod neg pos abs invert "
    "complex int float index "
    "round trunc floor ceil "
    "bool next "
    "fspath "
    "aiter "
)

numerics = (
    "add sub mul matmul div floordiv mod lshift rshift and xor or pow truediv"
)
inplace = ' '.join('i%s' % n for n in numerics.split())
right = ' '.join('r%s' % n for n in numerics.split())

# not including __prepare__, __instancecheck__, __subclasscheck__
# (as they are metaclass methods)
# __del__ is not supported at all as it causes problems if it exists

_non_defaults = {
    '__get__', '__set__', '__delete__', '__reversed__', '__missing__',
    '__reduce__', '__reduce_ex__', '__getinitargs__', '__getnewargs__',
    '__getstate__', '__setstate__', '__getformat__', '__setformat__',
    '__repr__', '__dir__', '__subclasses__', '__format__',
    '__getnewargs_ex__',
}


def _get_method(name, func):
    "Turns a callable object (like a mock) into a real function"
    def method(self, /, *args, **kw):
        return func(self, *args, **kw)
    method.__name__ = name
    return method


# 这些都是magics(魔法)属性
# {'__rlshift__', '__imod__', '__mod__', '__idiv__', '__sizeof__', '__pos__', '__rdiv__', '__ge__', '__rtruediv__',
# '__mul__', '__ilshift__', '__gt__', '__rmod__', '__radd__', '__isub__', '__lshift__', '__div__', '__round__',
# '__ior__', '__iand__', '__trunc__', '__neg__', '__index__', '__iadd__', '__itruediv__', '__rmatmul__', '__divmod__',
# '__rmul__', '__and__', '__hash__', '__pow__', '__rrshift__', '__exit__', '__float__', '__fspath__', '__rpow__',
# '__ixor__', '__rfloordiv__', '__contains__', '__rsub__', '__invert__', '__complex__', '__bool__', '__irshift__',
# '__floor__', '__aiter__', '__getitem__', '__abs__', '__int__', '__lt__', '__truediv__', '__rshift__', '__rand__',
# '__next__', '__ceil__', '__imul__', '__ror__', '__iter__', '__eq__', '__ne__', '__or__', '__add__', '__rdivmod__',
# '__floordiv__', '__rxor__', '__ifloordiv__', '__str__', '__len__', '__xor__', '__delitem__', '__matmul__', '__le__',
# '__imatmul__', '__ipow__', '__enter__', '__setitem__', '__sub__'}
_magics = {
    '__%s__' % method for method in
    ' '.join([magic_methods, numerics, inplace, right]).split()
}

# Magic methods used for async `with` statements
# __aenter__ 和 __aexit__ 是配合 with 关键字语法完成特定机制的功能, 主要用于简化变量创建和变量回收工作.
# __anext__ 通常和 __aiter__ 一起配合完成工作(使对象编程一个 async_iterator).
# 备注: async_iterator 比 generator 块2.5倍.
# 参考资料:
# https://cloud.tencent.com/developer/article/1420997
# https://www.python.org/dev/peps/pep-0525/
_async_method_magics = {"__aenter__", "__aexit__", "__anext__"}

# Magic methods that are only used with async calls but are synchronous functions themselves
# __aiter__ 它是一个同步函数, 但也只有异步函数调用会触发它.
_sync_async_magics = {"__aiter__"}
_async_magics = _async_method_magics | _sync_async_magics

_all_sync_magics = _magics | _non_defaults
_all_magics = _all_sync_magics | _async_magics

_unsupported_magics = {
    '__getattr__', '__setattr__',
    '__init__', '__new__', '__prepare__',
    '__instancecheck__', '__subclasscheck__',
    '__del__'
}

_calculate_return_value = {
    '__hash__': lambda self: object.__hash__(self),
    '__str__': lambda self: object.__str__(self),
    '__sizeof__': lambda self: object.__sizeof__(self),
    '__fspath__': lambda self: f"{type(self).__name__}/{self._extract_mock_name()}/{id(self)}",
}

_return_values = {
    '__lt__': NotImplemented,
    '__gt__': NotImplemented,
    '__le__': NotImplemented,
    '__ge__': NotImplemented,
    '__int__': 1,
    '__contains__': False,
    '__len__': 0,
    '__exit__': False,
    '__complex__': 1j,
    '__float__': 1.0,
    '__bool__': True,
    '__index__': 1,
    '__aexit__': False,
}


def _get_eq(self):
    def __eq__(other):
        ret_val = self.__eq__._mock_return_value
        if ret_val is not DEFAULT:
            return ret_val
        if self is other:
            return True
        return NotImplemented
    return __eq__

def _get_ne(self):
    def __ne__(other):
        if self.__ne__._mock_return_value is not DEFAULT:
            return DEFAULT
        if self is other:
            return False
        return NotImplemented
    return __ne__

def _get_iter(self):
    def __iter__():
        ret_val = self.__iter__._mock_return_value
        if ret_val is DEFAULT:
            return iter([])
        # if ret_val was already an iterator, then calling iter on it should
        # return the iterator unchanged
        return iter(ret_val)
    return __iter__

def _get_async_iter(self):
    def __aiter__():
        ret_val = self.__aiter__._mock_return_value
        if ret_val is DEFAULT:
            return _AsyncIterator(iter([]))
        return _AsyncIterator(iter(ret_val))
    return __aiter__

_side_effect_methods = {
    '__eq__': _get_eq,
    '__ne__': _get_ne,
    '__iter__': _get_iter,
    '__aiter__': _get_async_iter
}



def _set_return_value(mock, method, name):
    fixed = _return_values.get(name, DEFAULT)
    if fixed is not DEFAULT:
        method.return_value = fixed
        return

    return_calculator = _calculate_return_value.get(name)
    if return_calculator is not None:
        return_value = return_calculator(mock)
        method.return_value = return_value
        return

    side_effector = _side_effect_methods.get(name)
    if side_effector is not None:
        method.side_effect = side_effector(mock)


#######################################################################################################################
# MagicMock 和 Mock 的区别在于:
# MagicMock多继承了MagicMixin对象, 该对象的主要目的是将类 mock 对象的 魔法属性 全部替换成 MagicProxy 对象.
# 即:
# mock对象主要是为了记录那些不存在属性的调用.
# magicmock对象主要是为了记录那些魔法属性的调用.
#######################################################################################################################
class MagicMixin(Base):
    def __init__(self, /, *args, **kw):
        self._mock_set_magics()  # make magic work for kwargs in init
        _safe_super(MagicMixin, self).__init__(*args, **kw)
        self._mock_set_magics()  # fix magic broken by upper level init

    ###################################################################################################################
    # _mock_set_magics(self)
    # 该方法用于替换魔法属性, 将其换成MagicProxy.
    ###################################################################################################################
    def _mock_set_magics(self):
        # set 数据结构的快捷操作
        # |操作符: union
        # &操作符: intersection
        # -操作符: difference
        # ^操作符: symmetric_difference
        orig_magics = _magics | _async_method_magics
        these_magics = orig_magics

        # 如果 self._mock_methods is not None 则表示 spec 或 spec_set 限定对象已经定义了.
        # orig_magics.intersection 的意思是 以 self._mock_metdhos 为主, 其他属性移除掉.
        if getattr(self, "_mock_methods", None) is not None:
            these_magics = orig_magics.intersection(self._mock_methods)

            remove_magics = set()
            remove_magics = orig_magics - these_magics

            for entry in remove_magics:
                if entry in type(self).__dict__:
                    # remove unneeded magic methods
                    delattr(self, entry)

        # 这里采用difference来移除 当前(mock)类对象的__dict__属性, 即: 以 self._mock_methods 为主.
        # 假设如果spec或spec_set没有定义, 那么 self._mock_methods 为空;
        # 那么这里就以 _magics + _async_method_magics 为主, 这里使用 -(difference) 的意思是,
        # 把相同的移除掉, 留下以 these_magics 为主的那些不同的.
        # 当 type(self).__dict__ 很少属性时, 那么下面要替换的魔法属性就很多.
        # 当 type(self).__dict__ 很多属性时, 那么下面要替换的魔法属性就很少甚至不替换.
        # don't overwrite existing attributes if called a second time
        these_magics = these_magics - set(type(self).__dict__)

        # TODO: 这里把Mock类对象剩余的属性替换为MagicProxy对象, 有什么用?
        # ANSERED: 替换成 MagicProxy 对象的作用是, 当调用了魔法属性时, 像mock那样,
        #          给它返回一个mock对象, 并且记录下来他调用了魔法属性.
        _type = type(self)
        for entry in these_magics:
            setattr(_type, entry, MagicProxy(entry, self))


class NonCallableMagicMock(MagicMixin, NonCallableMock):
    """A version of `MagicMock` that isn't callable."""
    def mock_add_spec(self, spec, spec_set=False):
        """Add a spec to a mock. `spec` can either be an object or a
        list of strings. Only attributes on the `spec` can be fetched as
        attributes from the mock.

        If `spec_set` is True then only attributes on the spec can be set."""
        self._mock_add_spec(spec, spec_set)
        self._mock_set_magics()


class AsyncMagicMixin(MagicMixin):
    def __init__(self, /, *args, **kw):
        self._mock_set_magics()  # make magic work for kwargs in init
        _safe_super(AsyncMagicMixin, self).__init__(*args, **kw)
        self._mock_set_magics()  # fix magic broken by upper level init

class MagicMock(MagicMixin, Mock):
    """
    MagicMock is a subclass of Mock with default implementations
    of most of the magic methods. You can use MagicMock without having to
    configure the magic methods yourself.

    If you use the `spec` or `spec_set` arguments then *only* magic
    methods that exist in the spec will be created.

    Attributes and the return value of a `MagicMock` will also be `MagicMocks`.
    """
    def mock_add_spec(self, spec, spec_set=False):
        """Add a spec to a mock. `spec` can either be an object or a
        list of strings. Only attributes on the `spec` can be fetched as
        attributes from the mock.

        If `spec_set` is True then only attributes on the spec can be set."""
        self._mock_add_spec(spec, spec_set)
        self._mock_set_magics()



class MagicProxy(Base):
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent

    def create_mock(self):
        entry = self.name
        parent = self.parent
        m = parent._get_child_mock(name=entry, _new_name=entry,
                                   _new_parent=parent)
        setattr(parent, entry, m)
        _set_return_value(parent, m, entry)
        return m

    def __get__(self, obj, _type=None):
        return self.create_mock()


class AsyncMockMixin(Base):
    await_count = _delegating_property('await_count')
    await_args = _delegating_property('await_args')
    await_args_list = _delegating_property('await_args_list')

    def __init__(self, /, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # asyncio.iscoroutinefunction() checks _is_coroutine property to say if an
        # object is a coroutine. Without this check it looks to see if it is a
        # function/method, which in this case it is not (since it is an
        # AsyncMock).
        # It is set through __dict__ because when spec_set is True, this
        # attribute is likely undefined.
        self.__dict__['_is_coroutine'] = asyncio.coroutines._is_coroutine
        self.__dict__['_mock_await_count'] = 0
        self.__dict__['_mock_await_args'] = None
        self.__dict__['_mock_await_args_list'] = _CallList()
        code_mock = NonCallableMock(spec_set=CodeType)
        code_mock.co_flags = inspect.CO_COROUTINE
        self.__dict__['__code__'] = code_mock

    async def _execute_mock_call(self, /, *args, **kwargs):
        # This is nearly just like super(), except for sepcial handling
        # of coroutines

        _call = self.call_args
        self.await_count += 1
        self.await_args = _call
        self.await_args_list.append(_call)

        effect = self.side_effect
        if effect is not None:
            if _is_exception(effect):
                raise effect
            elif not _callable(effect):
                try:
                    result = next(effect)
                except StopIteration:
                    # It is impossible to propogate a StopIteration
                    # through coroutines because of PEP 479
                    raise StopAsyncIteration
                if _is_exception(result):
                    raise result
            elif asyncio.iscoroutinefunction(effect):
                result = await effect(*args, **kwargs)
            else:
                result = effect(*args, **kwargs)

            if result is not DEFAULT:
                return result

        if self._mock_return_value is not DEFAULT:
            return self.return_value

        if self._mock_wraps is not None:
            if asyncio.iscoroutinefunction(self._mock_wraps):
                return await self._mock_wraps(*args, **kwargs)
            return self._mock_wraps(*args, **kwargs)

        return self.return_value

    def assert_awaited(self):
        """
        Assert that the mock was awaited at least once.
        """
        if self.await_count == 0:
            msg = f"Expected {self._mock_name or 'mock'} to have been awaited."
            raise AssertionError(msg)

    def assert_awaited_once(self):
        """
        Assert that the mock was awaited exactly once.
        """
        if not self.await_count == 1:
            msg = (f"Expected {self._mock_name or 'mock'} to have been awaited once."
                   f" Awaited {self.await_count} times.")
            raise AssertionError(msg)

    def assert_awaited_with(self, /, *args, **kwargs):
        """
        Assert that the last await was with the specified arguments.
        """
        if self.await_args is None:
            expected = self._format_mock_call_signature(args, kwargs)
            raise AssertionError(f'Expected await: {expected}\nNot awaited')

        def _error_message():
            msg = self._format_mock_failure_message(args, kwargs, action='await')
            return msg

        expected = self._call_matcher((args, kwargs))
        actual = self._call_matcher(self.await_args)
        if expected != actual:
            cause = expected if isinstance(expected, Exception) else None
            raise AssertionError(_error_message()) from cause

    def assert_awaited_once_with(self, /, *args, **kwargs):
        """
        Assert that the mock was awaited exactly once and with the specified
        arguments.
        """
        if not self.await_count == 1:
            msg = (f"Expected {self._mock_name or 'mock'} to have been awaited once."
                   f" Awaited {self.await_count} times.")
            raise AssertionError(msg)
        return self.assert_awaited_with(*args, **kwargs)

    def assert_any_await(self, /, *args, **kwargs):
        """
        Assert the mock has ever been awaited with the specified arguments.
        """
        expected = self._call_matcher((args, kwargs))
        actual = [self._call_matcher(c) for c in self.await_args_list]
        if expected not in actual:
            cause = expected if isinstance(expected, Exception) else None
            expected_string = self._format_mock_call_signature(args, kwargs)
            raise AssertionError(
                '%s await not found' % expected_string
            ) from cause

    def assert_has_awaits(self, calls, any_order=False):
        """
        Assert the mock has been awaited with the specified calls.
        The :attr:`await_args_list` list is checked for the awaits.

        If `any_order` is False (the default) then the awaits must be
        sequential. There can be extra calls before or after the
        specified awaits.

        If `any_order` is True then the awaits can be in any order, but
        they must all appear in :attr:`await_args_list`.
        """
        expected = [self._call_matcher(c) for c in calls]
        cause = next((e for e in expected if isinstance(e, Exception)), None)
        all_awaits = _CallList(self._call_matcher(c) for c in self.await_args_list)
        if not any_order:
            if expected not in all_awaits:
                if cause is None:
                    problem = 'Awaits not found.'
                else:
                    problem = ('Error processing expected awaits.\n'
                               'Errors: {}').format(
                                   [e if isinstance(e, Exception) else None
                                    for e in expected])
                raise AssertionError(
                    f'{problem}\n'
                    f'Expected: {_CallList(calls)}\n'
                    f'Actual: {self.await_args_list}'
                ) from cause
            return

        all_awaits = list(all_awaits)

        not_found = []
        for kall in expected:
            try:
                all_awaits.remove(kall)
            except ValueError:
                not_found.append(kall)
        if not_found:
            raise AssertionError(
                '%r not all found in await list' % (tuple(not_found),)
            ) from cause

    def assert_not_awaited(self):
        """
        Assert that the mock was never awaited.
        """
        if self.await_count != 0:
            msg = (f"Expected {self._mock_name or 'mock'} to not have been awaited."
                   f" Awaited {self.await_count} times.")
            raise AssertionError(msg)

    def reset_mock(self, /, *args, **kwargs):
        """
        See :func:`.Mock.reset_mock()`
        """
        super().reset_mock(*args, **kwargs)
        self.await_count = 0
        self.await_args = None
        self.await_args_list = _CallList()


class AsyncMock(AsyncMockMixin, AsyncMagicMixin, Mock):
    """
    Enhance :class:`Mock` with features allowing to mock
    an async function.

    The :class:`AsyncMock` object will behave so the object is
    recognized as an async function, and the result of a call is an awaitable:

    >>> mock = AsyncMock()
    >>> asyncio.iscoroutinefunction(mock)
    True
    >>> inspect.isawaitable(mock())
    True


    The result of ``mock()`` is an async function which will have the outcome
    of ``side_effect`` or ``return_value``:

    - if ``side_effect`` is a function, the async function will return the
      result of that function,
    - if ``side_effect`` is an exception, the async function will raise the
      exception,
    - if ``side_effect`` is an iterable, the async function will return the
      next value of the iterable, however, if the sequence of result is
      exhausted, ``StopIteration`` is raised immediately,
    - if ``side_effect`` is not defined, the async function will return the
      value defined by ``return_value``, hence, by default, the async function
      returns a new :class:`AsyncMock` object.

    If the outcome of ``side_effect`` or ``return_value`` is an async function,
    the mock async function obtained when the mock object is called will be this
    async function itself (and not an async function returning an async
    function).

    The test author can also specify a wrapped object with ``wraps``. In this
    case, the :class:`Mock` object behavior is the same as with an
    :class:`.Mock` object: the wrapped object may have methods
    defined as async function functions.

    Based on Martin Richard's asynctest project.
    """


class _ANY(object):
    "A helper object that compares equal to everything."

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __repr__(self):
        return '<ANY>'

ANY = _ANY()


#######################################################################################################################
# _format_call_signature(name, args, kwargs)
# 该函数用户生成一个call_signature.
#
# _format_call_signature("hello", args=(), kwargs={"a": "one", "b": "two"})       生成 hello(a='one', b='two')
# _format_call_signature("mock", args=(), kwargs={"a": "one", "b": "two"})        生成 mock(a='one', b='two')
# _format_call_signature("hello", args=("3", 5), kwargs={"a": "one", "b": "two"}) 生成 hello('3', 5, a='one', b='two')
#######################################################################################################################
def _format_call_signature(name, args, kwargs):
    message = '%s(%%s)' % name
    formatted_args = ''
    args_string = ', '.join([repr(arg) for arg in args])

    # 重点:
    # %s 是将字符串渲染出来
    # %r 是将'字符串'渲染出来
    kwargs_string = ', '.join([
        '%s=%r' % (key, value) for key, value in kwargs.items()
    ])
    if args_string:
        formatted_args = args_string
    if kwargs_string:
        if formatted_args:
            formatted_args += ', '
        formatted_args += kwargs_string

    return message % formatted_args


#######################################################################################################################
# _Call(tuple)
# 该类对象用于存储mock调用时传递的参数.
# 如果仅仅是用于存储mock调用时传递的参数, 那没有必要花这般精力来写一个_Call对象, 直接保存在一个tuple或者list中即可;
# 它存在的意义是: 提供一个便捷的参数比较和历史版本匹配的功能, 以参数比较为例:
# _Call(('name', (), {})) == ('name',)               使用_Call来做==操作比较时, 可以省略掉那些空的冗余.
# _Call(('name', (1,), {})) == ('name', (1,))        使用_Call来做==操作比较时, 可以省略掉那些空的冗余.
# _Call(((), {'a': 'b'})) == ({'a': 'b'},)           使用_Call来做==操作比较时, 可以省略掉那些空的冗余.
#
# _Call继承了tuple对象, 所以_Call本身就是一个tuple: tuple是一个实例化后就不可变的集合.
#
# _Call在__new__中做了什么?
# 注释中有说明: 主要时围绕 value 参数进行预处理, 它要求 value 必须按照特定规范来提供,
# 要么是: (args, kwargs), 要么是: (name, args, kwargs); 其他形式的value参数可能会导致不可预期的错误.
#
# _Call为什么要把这些代码写在__new__中, 而不是写在 __init__ 中? (能不能不写__new__)?
# python中的构造函数是 __new__, 不是__init__, 所以参数预处理代码必须写在 __new__ 中, 举例说明:
# ss = _Call('name', (), {})             # __new__ 是在赋值之前触发的, 而 __init__ 是在赋值给ss之后触发的.
# 也就是说, 想要规范和统一 value 参数的规格, 就必须在__new__中完成.
#
# 如何证明 __new__ 是在赋值之前触发的, 而 __init__ 是在赋值之后触发的?
# 样例代码:
# class Hello(object):
#
#     def __new__(cls, desc=""):
#         ss = object.__new__(cls)
#         return ss
#
#     def __init__(self, desc=""):
#         print("desc: ", desc)
#         self.description = desc
#
# 测试1: __new__和__init__不是强关联
# 描述1: __new__中的参数通常要和 __init__中的参数保持一致, Python保证传递给了
#       __new__什么就会传递给__init__什么, 而不是交给__new__来控制.
# 备注1: 如果参数是 list 或者 dict 这种引用类型, 那么在 __new__ 中更改了它的值, 也会同步影响到__init__的值.
# zz = Hello(desc="good")
# print("zz.description: ", zz.description)
#
# output:
# desc:  good
# zz.description:  good
#
# 结论1:  __new__创建对象时并没有将desc传递给object.__new__,
#        而__init__可以收到desc参数, 这就表明 __new__ 并不掌控参数的分配.
#
#
#
# 测试2: __new__在赋值之前触发, 而__init__在赋值之后触发.
# 描述2: 在 __new__ 中的 ss = object.__new__(cls) 并不是执行 __init__ 的意思, 而是构造一个对象.
#       在 __new__ 中的 return ss , 返回给外部(外部可以用来赋值, 也可以直接当作临时变量使用, 使用完之后python将自动销毁).
# class Hello(object):
#
#     def __new__(cls, desc=""):
#         print("trigger __new__")
#         ss = object.__new__(cls)
#         # return ss                                   # 注释掉这段代码
#
#     def __init__(self, desc=""):
#         print("trigger __init__")
#         self.description = desc
#
#
# zz = Hello(desc="good")
# print("zz: ", zz)
#
# output:
# trigger __new__
# None
#
# 结论2: 虽然 __new__ 中仍然构建了一个对象, 但是并没有返回给外部, 所以外部 zz = 并没有完成赋值动作, 所以打印出来的是None.
#        同时也没有打印出来"trigger __init__", 所以可以证明, 没有完成赋值动作, 就没有触发 __init__.
#######################################################################################################################
class _Call(tuple):
    """
    A tuple for holding the results of a call to a mock, either in the form
    `(args, kwargs)` or `(name, args, kwargs)`.

    If args or kwargs are empty then a call tuple will compare equal to
    a tuple without those values. This makes comparisons less verbose::

        _Call(('name', (), {})) == ('name',)
        _Call(('name', (1,), {})) == ('name', (1,))
        _Call(((), {'a': 'b'})) == ({'a': 'b'},)

    The `_Call` object provides a useful shortcut for comparing with call::

        _Call(((1, 2), {'a': 3})) == call(1, 2, a=3)
        _Call(('foo', (1, 2), {'a': 3})) == call.foo(1, 2, a=3)

    If the _Call has no name then it will match any name.
    """
    def __new__(cls, value=(), name='', parent=None, two=False,
                from_kall=True):
        args = ()
        kwargs = {}
        _len = len(value)
        if _len == 3:
            name, args, kwargs = value                      # (name: str, args: tuple, kwargs: dict)
        elif _len == 2:
            first, second = value
            if isinstance(first, str):
                name = first
                if isinstance(second, tuple):
                    args = second                           # (name: str, args: tuple)
                else:
                    kwargs = second                         # (name: str, kwargs: dict)
            else:
                args, kwargs = first, second
        elif _len == 1:
            value, = value                                  # value, = value 等同于 value = value[0]
            if isinstance(value, str):
                name = value                                # (name: str, (), {})
            elif isinstance(value, tuple):
                args = value                                # ('', args: tuple, {})
            else:
                kwargs = value                              # ('', (), kwargs: dict)

        if two:
            return tuple.__new__(cls, (args, kwargs))       # ss = (args: tuple, kwargs: dict)

        return tuple.__new__(cls, (name, args, kwargs))     # ss = (name: str, args: tuple, kwargs: dict)

    def __init__(self, value=(), name=None, parent=None, two=False,
                 from_kall=True):
        self._mock_name = name
        self._mock_parent = parent
        self._mock_from_kall = from_kall


    def __eq__(self, other):
        if other is ANY:
            return True
        try:
            len_other = len(other)
        except TypeError:
            return False

        self_name = ''
        if len(self) == 2:
            self_args, self_kwargs = self
        else:
            self_name, self_args, self_kwargs = self

        if (getattr(self, '_mock_parent', None) and getattr(other, '_mock_parent', None)
                and self._mock_parent != other._mock_parent):
            return False

        other_name = ''
        if len_other == 0:
            other_args, other_kwargs = (), {}
        elif len_other == 3:
            other_name, other_args, other_kwargs = other
        elif len_other == 1:
            value, = other
            if isinstance(value, tuple):
                other_args = value
                other_kwargs = {}
            elif isinstance(value, str):
                other_name = value
                other_args, other_kwargs = (), {}
            else:
                other_args = ()
                other_kwargs = value
        elif len_other == 2:
            # could be (name, args) or (name, kwargs) or (args, kwargs)
            first, second = other
            if isinstance(first, str):
                other_name = first
                if isinstance(second, tuple):
                    other_args, other_kwargs = second, {}
                else:
                    other_args, other_kwargs = (), second
            else:
                other_args, other_kwargs = first, second
        else:
            return False

        if self_name and other_name != self_name:
            return False

        # this order is important for ANY to work!
        return (other_args, other_kwargs) == (self_args, self_kwargs)


    __ne__ = object.__ne__


    def __call__(self, /, *args, **kwargs):
        if self._mock_name is None:
            return _Call(('', args, kwargs), name='()')

        name = self._mock_name + '()'
        return _Call((self._mock_name, args, kwargs), name=name, parent=self)


    def __getattr__(self, attr):
        if self._mock_name is None:
            return _Call(name=attr, from_kall=False)
        name = '%s.%s' % (self._mock_name, attr)
        return _Call(name=name, parent=self, from_kall=False)


    def __getattribute__(self, attr):
        if attr in tuple.__dict__:
            raise AttributeError
        return tuple.__getattribute__(self, attr)


    def count(self, /, *args, **kwargs):
        return self.__getattr__('count')(*args, **kwargs)

    def index(self, /, *args, **kwargs):
        return self.__getattr__('index')(*args, **kwargs)

    def _get_call_arguments(self):
        if len(self) == 2:
            args, kwargs = self
        else:
            name, args, kwargs = self

        return args, kwargs

    @property
    def args(self):
        return self._get_call_arguments()[0]

    @property
    def kwargs(self):
        return self._get_call_arguments()[1]

    def __repr__(self):
        if not self._mock_from_kall:
            name = self._mock_name or 'call'
            if name.startswith('()'):
                name = 'call%s' % name
            return name

        if len(self) == 2:
            name = 'call'
            args, kwargs = self
        else:
            name, args, kwargs = self
            if not name:
                name = 'call'
            elif not name.startswith('()'):
                name = 'call.%s' % name
            else:
                name = 'call%s' % name
        return _format_call_signature(name, args, kwargs)


    def call_list(self):
        """For a call object that represents multiple calls, `call_list`
        returns a list of all the intermediate calls as well as the
        final call."""
        vals = []
        thing = self
        while thing is not None:
            if thing._mock_from_kall:
                vals.append(thing)
            thing = thing._mock_parent
        return _CallList(reversed(vals))


call = _Call(from_kall=False)


def create_autospec(spec, spec_set=False, instance=False, _parent=None,
                    _name=None, **kwargs):
    """Create a mock object using another object as a spec. Attributes on the
    mock will use the corresponding attribute on the `spec` object as their
    spec.

    Functions or methods being mocked will have their arguments checked
    to check that they are called with the correct signature.

    If `spec_set` is True then attempting to set attributes that don't exist
    on the spec object will raise an `AttributeError`.

    If a class is used as a spec then the return value of the mock (the
    instance of the class) will have the same spec. You can use a class as the
    spec for an instance object by passing `instance=True`. The returned mock
    will only be callable if instances of the mock are callable.

    `create_autospec` also takes arbitrary keyword arguments that are passed to
    the constructor of the created mock."""
    if _is_list(spec):
        # can't pass a list instance to the mock constructor as it will be
        # interpreted as a list of strings
        spec = type(spec)

    is_type = isinstance(spec, type)
    is_async_func = _is_async_func(spec)
    _kwargs = {'spec': spec}
    if spec_set:
        _kwargs = {'spec_set': spec}
    elif spec is None:
        # None we mock with a normal mock without a spec
        _kwargs = {}
    if _kwargs and instance:
        _kwargs['_spec_as_instance'] = True

    _kwargs.update(kwargs)

    Klass = MagicMock
    if inspect.isdatadescriptor(spec):
        # descriptors don't have a spec
        # because we don't know what type they return
        _kwargs = {}
    elif is_async_func:
        if instance:
            raise RuntimeError("Instance can not be True when create_autospec "
                               "is mocking an async function")
        Klass = AsyncMock
    elif not _callable(spec):
        Klass = NonCallableMagicMock
    elif is_type and instance and not _instance_callable(spec):
        Klass = NonCallableMagicMock

    _name = _kwargs.pop('name', _name)

    _new_name = _name
    if _parent is None:
        # for a top level object no _new_name should be set
        _new_name = ''

    mock = Klass(parent=_parent, _new_parent=_parent, _new_name=_new_name,
                 name=_name, **_kwargs)

    if isinstance(spec, FunctionTypes):
        # should only happen at the top level because we don't
        # recurse for functions
        mock = _set_signature(mock, spec)
        if is_async_func:
            _setup_async_mock(mock)
    else:
        _check_signature(spec, mock, is_type, instance)

    if _parent is not None and not instance:
        _parent._mock_children[_name] = mock

    if is_type and not instance and 'return_value' not in kwargs:
        mock.return_value = create_autospec(spec, spec_set, instance=True,
                                            _name='()', _parent=mock)

    for entry in dir(spec):
        if _is_magic(entry):
            # MagicMock already does the useful magic methods for us
            continue

        # XXXX do we need a better way of getting attributes without
        # triggering code execution (?) Probably not - we need the actual
        # object to mock it so we would rather trigger a property than mock
        # the property descriptor. Likewise we want to mock out dynamically
        # provided attributes.
        # XXXX what about attributes that raise exceptions other than
        # AttributeError on being fetched?
        # we could be resilient against it, or catch and propagate the
        # exception when the attribute is fetched from the mock
        try:
            original = getattr(spec, entry)
        except AttributeError:
            continue

        kwargs = {'spec': original}
        if spec_set:
            kwargs = {'spec_set': original}

        if not isinstance(original, FunctionTypes):
            new = _SpecState(original, spec_set, mock, entry, instance)
            mock._mock_children[entry] = new
        else:
            parent = mock
            if isinstance(spec, FunctionTypes):
                parent = mock.mock

            skipfirst = _must_skip(spec, entry, is_type)
            kwargs['_eat_self'] = skipfirst
            if asyncio.iscoroutinefunction(original):
                child_klass = AsyncMock
            else:
                child_klass = MagicMock
            new = child_klass(parent=parent, name=entry, _new_name=entry,
                              _new_parent=parent,
                              **kwargs)
            mock._mock_children[entry] = new
            _check_signature(original, new, skipfirst=skipfirst)

        # so functions created with _set_signature become instance attributes,
        # *plus* their underlying mock exists in _mock_children of the parent
        # mock. Adding to _mock_children may be unnecessary where we are also
        # setting as an instance attribute?
        if isinstance(new, FunctionTypes):
            setattr(mock, entry, new)

    return mock


def _must_skip(spec, entry, is_type):
    """
    Return whether we should skip the first argument on spec's `entry`
    attribute.
    """
    if not isinstance(spec, type):
        if entry in getattr(spec, '__dict__', {}):
            # instance attribute - shouldn't skip
            return False
        spec = spec.__class__

    for klass in spec.__mro__:
        result = klass.__dict__.get(entry, DEFAULT)
        if result is DEFAULT:
            continue
        if isinstance(result, (staticmethod, classmethod)):
            return False
        elif isinstance(getattr(result, '__get__', None), MethodWrapperTypes):
            # Normal method => skip if looked up on type
            # (if looked up on instance, self is already skipped)
            return is_type
        else:
            return False

    # function is a dynamically provided attribute
    return is_type


class _SpecState(object):

    def __init__(self, spec, spec_set=False, parent=None,
                 name=None, ids=None, instance=False):
        self.spec = spec
        self.ids = ids
        self.spec_set = spec_set
        self.parent = parent
        self.instance = instance
        self.name = name


FunctionTypes = (
    # python function
    type(create_autospec),
    # instance method
    type(ANY.__eq__),
)

MethodWrapperTypes = (
    type(ANY.__eq__.__get__),
)


file_spec = None


def _to_stream(read_data):
    if isinstance(read_data, bytes):
        return io.BytesIO(read_data)
    else:
        return io.StringIO(read_data)


def mock_open(mock=None, read_data=''):
    """
    A helper function to create a mock to replace the use of `open`. It works
    for `open` called directly or used as a context manager.

    The `mock` argument is the mock object to configure. If `None` (the
    default) then a `MagicMock` will be created for you, with the API limited
    to methods or attributes available on standard file handles.

    `read_data` is a string for the `read`, `readline` and `readlines` of the
    file handle to return.  This is an empty string by default.
    """
    _read_data = _to_stream(read_data)
    _state = [_read_data, None]

    def _readlines_side_effect(*args, **kwargs):
        if handle.readlines.return_value is not None:
            return handle.readlines.return_value
        return _state[0].readlines(*args, **kwargs)

    def _read_side_effect(*args, **kwargs):
        if handle.read.return_value is not None:
            return handle.read.return_value
        return _state[0].read(*args, **kwargs)

    def _readline_side_effect(*args, **kwargs):
        yield from _iter_side_effect()
        while True:
            yield _state[0].readline(*args, **kwargs)

    def _iter_side_effect():
        if handle.readline.return_value is not None:
            while True:
                yield handle.readline.return_value
        for line in _state[0]:
            yield line

    def _next_side_effect():
        if handle.readline.return_value is not None:
            return handle.readline.return_value
        return next(_state[0])

    global file_spec
    if file_spec is None:
        import _io
        file_spec = list(set(dir(_io.TextIOWrapper)).union(set(dir(_io.BytesIO))))

    if mock is None:
        mock = MagicMock(name='open', spec=open)

    handle = MagicMock(spec=file_spec)
    handle.__enter__.return_value = handle

    handle.write.return_value = None
    handle.read.return_value = None
    handle.readline.return_value = None
    handle.readlines.return_value = None

    handle.read.side_effect = _read_side_effect
    _state[1] = _readline_side_effect()
    handle.readline.side_effect = _state[1]
    handle.readlines.side_effect = _readlines_side_effect
    handle.__iter__.side_effect = _iter_side_effect
    handle.__next__.side_effect = _next_side_effect

    def reset_data(*args, **kwargs):
        _state[0] = _to_stream(read_data)
        if handle.readline.side_effect == _state[1]:
            # Only reset the side effect if the user hasn't overridden it.
            _state[1] = _readline_side_effect()
            handle.readline.side_effect = _state[1]
        return DEFAULT

    mock.side_effect = reset_data
    mock.return_value = handle
    return mock


class PropertyMock(Mock):
    """
    A mock intended to be used as a property, or other descriptor, on a class.
    `PropertyMock` provides `__get__` and `__set__` methods so you can specify
    a return value when it is fetched.

    Fetching a `PropertyMock` instance from an object calls the mock, with
    no args. Setting it calls the mock with the value being set.
    """
    def _get_child_mock(self, /, **kwargs):
        return MagicMock(**kwargs)

    def __get__(self, obj, obj_type=None):
        return self()
    def __set__(self, obj, val):
        self(val)


#######################################################################################################################
# seal(mock)
# 该函数用于关闭自动生成子mock对象(递归关闭所有子mock对象的自动生成子mock功能).
#
# 说明:
# 由于 mock 的 __getattr__ 机制 会在访问 mock 不存在的属性时, 创建一个子mock对象,
# 所以这里提供了 seal 方法, 用于关闭这个自动创建子mock对象的功能.
#######################################################################################################################
def seal(mock):
    """Disable the automatic generation of child mocks.

    Given an input Mock, seals it to ensure no further mocks will be generated
    when accessing an attribute that was not already defined.

    The operation recursively seals the mock passed in, meaning that
    the mock itself, any mocks generated by accessing one of its attributes,
    and all assigned mocks without a name or spec will be sealed.
    """
    mock._mock_sealed = True
    for attr in dir(mock):
        try:
            m = getattr(mock, attr)
        except AttributeError:
            continue
        if not isinstance(m, NonCallableMock):
            continue
        if m._mock_new_parent is mock:
            seal(m)


class _AsyncIterator:
    """
    Wraps an iterator in an asynchronous iterator.
    """
    def __init__(self, iterator):
        self.iterator = iterator
        code_mock = NonCallableMock(spec_set=CodeType)
        code_mock.co_flags = inspect.CO_ITERABLE_COROUTINE
        self.__dict__['__code__'] = code_mock

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iterator)
        except StopIteration:
            pass
        raise StopAsyncIteration
