### local
`local`对象是一个大胖子, 它存储着每个线程的变量(主线程, 非主线程).  
`local`对象需要定义在全局, 这样每个线程看到它都会认为它是一个全局变量.   

`local`对象存储变量的方式是按照`id(threading.get_ident())`方式来分区存储,   
&nbsp;&nbsp;&nbsp; &nbsp; &nbsp; &nbsp; &nbsp;即: 为每个线程单独开辟一个字典来保存线程定义的变量.  

`local`对象被线程访问时, 总是通过线程的`id`来找到对应的区域, 然后再取对应的变量值返还给线程.  
 
 ```python
import _threading_local
import threading


# 创建全局ThreadLocal对象:
local = _threading_local.local()
local.hello = "good"


def process():
    # 3.获取当前线程关联的resource:
    res = local.resource
    print(res + "http://c.biancheng.net/python/")


def process_thread(res):
    # 1.为当前线程绑定ThreadLocal的resource:
    local.resource = res
    # 2.线程的调用函数不需要传递res了，可以通过全局变量local访问
    process()


t1 = threading.Thread(target=process_thread, args=('t1线程: ',))
t2 = threading.Thread(target=process_thread, args=('t2线程: ',))
t1.start()
t2.start()

t1.join()
t2.join()


# 输出
# t1线程: http://c.biancheng.net/python/
# t2线程: http://c.biancheng.net/python/

```

> 核心要点
> 1. 每个线程入口访问到的`local`变量都是一个空的字典对象,  
>    如果线程没有为`local`定义一些变量, 那么整个线程声明周期(从开始到结束), 读取到的`local`都是一个空字典.  
>    只有线程为`local`定义了变量, 线程中后续的代码(后续的嵌套调用方法)访问`local`时才能访问到对应的变量.  
>     
> 2. 对于线程来说, 只要在线程入口处定义好`local`变量, 后续不论调用多少层方法,   
>    这些方法访问`local`变量时, 只会拿到当前线程已定义的变量.   


&nbsp;  
&nbsp;  
### Lock
`Lock`是一个互斥锁.   
一个对象通过`acquire()`加锁成功后, 此时锁状态变成`True`.    
其他对象无法再次通过`acquire()`加锁, 想要操作该锁有两种途径: 
1. 循环检查`locked()`锁状态, 为`False`时可以使用;   
2. 强制解锁`release()`后, 可以使用;  

```python
from threading import Lock
import unittest


class TestLock(unittest.TestCase):

    def test_lock(self):
        # 实例化一个锁对象.
        lock = Lock()

        # 通过返回值可以得知加锁操作是否成功.
        lock_success = lock.acquire()
        self.assertTrue(lock_success)

        # 也可以通过lock.locked()获得锁状态.
        self.assertTrue(lock.locked())

        # 用完了, 别忘了解锁, 否则会导致其他对象堵塞.
        lock.release()
        self.assertFalse(lock.locked())

    def test_lock_twice(self):
        """
        lock加锁后, lock状态为True.
        当lock状态为True时, 无法再次完成加锁操作.
        """

        lock = Lock()
        lock.acquire()

        # 如果不提供blocking=False参数, 那么这里将会造成死锁,
        # 后续的代码和后续的任务都将因为死锁而无法执行.
        lock_success = lock.acquire(blocking=False)
        self.assertFalse(lock_success)

        # 用完了, 别忘了解锁, 否则会导致其他对象堵塞.
        lock.release()
        self.assertFalse(lock.locked())

    def test_release_lock(self):
        lock = Lock()
        lock.acquire()

        # 加锁失败
        lock_success = lock.acquire(blocking=False)
        self.assertFalse(lock_success)

        # 解锁
        lock.release()
        self.assertFalse(lock.locked())

        # 再次加锁
        lock_success = lock.acquire()
        self.assertTrue(lock_success)

        # 用完了, 别忘了解锁, 否则会导致其他对象堵塞.
        lock.release()
        self.assertFalse(lock.locked())

    def test_auto_release_lock(self):
        lock = Lock()

        with lock:                                  # 加锁
            self.assertTrue(lock.locked())          # 加锁状态.

        self.assertFalse(lock.locked())             # 已解锁


if __name__ == '__main__':
    unittest.main()
```

> 核心要点:  
> 1. 一次只能被一个对象加锁.  
> 2. 任何对象, 任何线程中, 都可以使用`release()`来完成解锁动作(某种程度上来说, 存在安全隐患).     
> 3. 锁的消费者别忘了使用完之后解锁, 否则其他线程中的对象可能就因为等待锁而造成程序假死现象.


&nbsp;  
&nbsp;  
### RLock
`RLock`的全称是`Reentrant Lock`, 中文直译是重入锁.   
`RLock`从接口上来看, 跟`Lock`差不多, 有`acquire()`和`release()`.   
`RLock`从功能成面上来看, 它因为内部维护了一个基于线程的`owner`和`count`属性, 所以它和`Lock`还不一样.  
`RLock`的`owner`是一个标记(存储一个线程`id`), 用于限定使用对象, 只允许与`owner`相同的线程`id`才能使用这个锁.     
`RLock`的`count`是一个计数器, 它允许同一个线程多次加锁, 每次加锁`count`都会递增`1`.   
`RLock`的使用者必须在使用完锁之后, 自觉解锁; 若count无法回到0, 其他线程无法使用.

其他线程如果想使用`RLock`则必须等待`RLock`的`owner=None`且`count=0`.   
其他线程不可以直接`release`正在被其他线程使用的`RLock`对象.  
```python
import time
import unittest
import threading


class TestRLock(unittest.TestCase):

    def test_rlock_can_acquire_multi_times(self):
        lock = threading._RLock()

        # 同一个线程, 加锁三次.
        lock.acquire()
        lock.acquire()
        lock.acquire()

        # 主线程-id
        master_thread_id = threading.get_ident()
        self.assertEqual(lock._owner, master_thread_id)
        self.assertEqual(lock._count, 3)

    # 定义一个函数, 用于在其他线程中运行, 尝试加锁.
    def acquire_by_other_thread(self, the_lock, the_lifetime):
        the_lock.acquire()
        the_lifetime.update({"status": "Done"})

    def test_rlock_multithread_acquire(self):
        lock = threading.RLock()

        # 在主线程中 acquire
        lock.acquire()

        # 定义一个变量, 尝试让其他线程修改.
        lifetime = {"status": "init"}

        # 启动一个线程
        t = threading.Thread(target=self.acquire_by_other_thread,
                             args=(lock, lifetime))
        t.daemon = True
        t.start()

        # 断言: lifetime的值没有发生变化
        time.sleep(2)
        self.assertEqual(lifetime["status"], "init")

        # 解锁
        lock.release()

        # 断言: lifetime的值被其他线程改了.
        time.sleep(2)
        self.assertEqual(lifetime["status"], "Done")


if __name__ == '__main__':
    unittest.main()

```

> 核心要点  
> 1. `RLock`是一个面向线程的锁.   
> 2. `RLock`允许同一个线程加锁多次, 同时也需要线程自觉解锁多次, 直到锁`count=0`.   
> 3. `RLock`处于已加锁状态时, 不允许其他线程使用, 也不允许其他线程解锁(相比较于`Lock`, 有了相对安全的保障).   


&nbsp;  
&nbsp;  
### Condition  
`Condition` 是一个条件锁.  

`Condition` 不能直接使用, 必须先加锁(获得锁), 才可以执行 wait 或 notify 操作.   

`Condition` 执行 wait 操作之后, 执行 wait 的线程就会一直处于堵塞状态, 必须等待其他线程 notify 才会激活 wait 线程.

`Condition` 执行 wait 操作之后, 会自动解锁Condition; 主要是因为不解锁的话, 其他线程无法加锁从而无法执行notify.

`Condition` 由于执行 wait 操作之后, 会自动解锁Condition; 所以假设多个线程都执行 wait 操作, 那么Condition内部就有很多 waiters; 通知线程可以使用 notify 挨个挨个激活这些waiters, 也可以使用 notify_all 一次性激活全部waiters.   

`Condition` 还支持 wait_for 操作, 即当其他线程使用 notify 通知到 wait_for 这个 waiter 时, 它并不会立马就激活程序, 而是依赖于外部的`predicate`回调函数返回的值(返回值为True时才会激活).

基于上述描述, Condition就像是一个标准的发布订阅模型, 即:
1. 多个worker都在订阅相同的频道, 发布者可以说激活一个worker去做一件事情, 也可以说激活全部worker去做多件事情.    
2. 多个worker可以订阅不同的频道(每个Condition锁变量是一个频道), 等等的场景.

[源码分析](./pythonlibs/threading.py#L210)  

```python
import logging
import unittest
import threading


class TestCondition(unittest.TestCase):

    def test_acquire(self):
        """ 默认Condition的基础锁是RLock, 这意味着同一个线程的情况下, 可以多次获得锁. """
        cond = threading.Condition(lock=threading._RLock())

        # 获得锁(加锁)
        cond.acquire()
        # 断言
        master_thread_id = threading.get_ident()
        self.assertEqual(cond._lock._owner, master_thread_id)
        self.assertEqual(cond._lock._count, 1)

        # 再次获得锁(加锁)
        cond.acquire()
        # 断言
        self.assertEqual(cond._lock._owner, master_thread_id)
        self.assertEqual(cond._lock._count, 2)

        # 解锁
        cond.release()
        cond.release()
        self.assertEqual(cond._lock._owner, None)
        self.assertEqual(cond._lock._count, 0)

    def test_acquire_and_release_not_delete_waiters(self):
        """ 多worker订阅一个频道, 发布者一个一个激活worker. """
        logging.basicConfig(level=logging.INFO)
        cond = threading.Condition(lock=threading._RLock())

        def worker(the_cond):
            tid = threading.get_ident()
            logging.info("worker-%s: subsribe..." % tid)
            with the_cond:
                the_cond.wait()
                logging.info("worker-%s: start to work." % tid)

        # 启动 10 个 worker, 让它们一起订阅 cond 频道
        for i in range(10):
            t = threading.Thread(target=worker, args=(cond, ))
            t.daemon = True
            t.start()

        # 断言: 有 10 个worker在一个频道里面.
        with cond:
            self.assertEqual(len(cond._waiters), 10)

        # 激活一个worker
        with cond:
            cond.notify()

        # 断言: 还剩 9 个worker在一个频道里面.
        with cond:
            self.assertEqual(len(cond._waiters), 9)

        # 激活剩余的worker
        with cond:
            cond.notify_all()

        # 断言: 还剩 0 个worker在一个频道里面.
        with cond:
            self.assertEqual(len(cond._waiters), 0)




if __name__ == '__main__':
    unittest.main()

```

> 核心要点  
> 1. `Condition` 就像是一个发布订阅模型.   
> 2. `Condition` 支持多个worker订阅(wait)一个频道(condition variable).  
> 3. `Condition` 支持条件(`predicate`)激活.     
