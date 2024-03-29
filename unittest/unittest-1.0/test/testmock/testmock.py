import copy
import re
import sys
import tempfile

import unittest
from unittest.test.testmock.support import is_instance
from unittest import mock
from unittest.mock import (
    call, DEFAULT, patch, sentinel,
    MagicMock, Mock, NonCallableMock,
    NonCallableMagicMock, AsyncMock, _Call, _CallList,
    create_autospec
)


class Iter(object):
    def __init__(self):
        self.thing = iter(['this', 'is', 'an', 'iter'])

    def __iter__(self):
        return self

    def next(self):
        return next(self.thing)

    __next__ = next


class Something(object):
    def meth(self, a, b, c, d=None): pass

    @classmethod
    def cmeth(cls, a, b, c, d=None): pass

    @staticmethod
    def smeth(a, b, c, d=None): pass


def something(a): pass


class MockTest(unittest.TestCase):

    ###################################################################################################################
    # 在python3中, 不可以在函数内使用 import * 语法.
    # def hello():
    #     from unittest.mock import *
    #     m = Mock()
    # hello()                                    报错: SyntaxError: import * only allowed at module level
    #
    # 使用 from unittest.mock import * 语法可以测试 __all__ 集合中定义的变量是否存在于unittest.mock文件中.
    # 如果 __all__ 中定义了 unittest.mock 不存在的对象, 那么就会抛出异常.
    #
    # 还有另外一种情况:
    # 当程序文件中没有定义 __all__ 时, 使用 from xxx import * 则会导入全部对象(含变量,函数,类).
    # 当程序文件中定义了 __all__ 时, 使用 from xxx import * 则仅导入__all__中声明的对象,
    # 没有声明在__all__集合中的对象, 不会被导入, 这相当于是启动了一层保护作用.
    #
    # 所以这里想要测试的是 __all__ 集合中声明的对象都存在于 unittest.mock 模块中.
    ###################################################################################################################
    def test_all(self):
        # if __all__ is badly defined then import * will raise an error
        # We have to exec it because you can't import * inside a method
        # in Python 3
        exec("from unittest.mock import *")

    ###################################################################################################################
    # 测试Mock构造函数(实例化)完成之后的Mock对象的内部初始值是否符合预期.
    #
    # 下面这些 _delegating_property 都会从 mock.__dict__ 中提取对象的键值,
    # 提取规则: "_mock_%s" % called/call_count/call_args/call_args_list/mock_calls...
    # mock.called               _delegating_property('called')
    # mock.call_count           _delegating_property('call_count')
    # mock.call_args            _delegating_property('call_args')
    # mock.call_args_list       _delegating_property('call_args_list')
    # mock.mock_calls           _delegating_property('mock_calls')
    #
    # 下面这些 property(__xx, __xx) 的get和set都会触发对应的函数, 而不是直接返回一个具体值.
    # mock.side_effect          property(__get_side_effect, __set_side_effect)
    # mock.return_value         property(__get_return_value, __set_return_value, __return_value_doc)
    #
    # 所以:
    # mock.called = False        等于访问 mock._mock_called, 它初始化(在NonCallableMock.__init__中)的值是 False.
    # mock.call_count = 0        等于访问 mock._mock_call_count, 它初始化(在NonCallableMock.__init__中)的值是 0.
    # mock.call_args = None      等于访问 mock._mock_call_args, 它初始化(在NonCallableMock.__init__中)的值是 None.
    # mock.call_args_list = []   等于访问 mock._mock_call_args_list, 它初始化(在NonCallableMock.__init__中)的值是 [].
    # mock.method_calls = []     等于访问 mock._mock_method_calls, 它初始化(在NonCallableMock.__init__中)的值是 _CallList().
    #
    # mock.return_value          等于访问 NonCallableMock.__get_return_value,
    #                            1. 如果初始化Mock时提供了return_value参数,
    #                               那么初始化过程中 CallableMixin.__init__ 内部会将其赋值给 mock._mock_return_value;
    #                               NonCallableMock.__get_return_value内部会判断,
    #                               如果 mock._mock_return_value 有值那么就返回该值.
    #                            2. 如果初始化Mock时没有提供return_value参数,
    #                               那么初始化过程中 CallableMixin.__init__ 内部
    #                               会将 Sentinel.DEFAULT 赋值给 mock._mock_return_value;
    #
    # mock._mock_parent = parent 当前实例没有提供参数, mock采用默认参数: None;
    # mock._mock_methods = spec  当前实例没有提供参数, mock采用默认参数: None;
    # mock._mock_children = {}   Mock没有定义mock_children的形式参数,
    #                           它在NonCallableMock.__init__中直接定义了一个空的_mock_children字典属性,
    #                            也就是说这个属性不可配置, 它是一个内部对象(供内部机制运作使用).
    ###################################################################################################################
    def test_constructor(self):
        mock = Mock()

        self.assertFalse(mock.called, "called not initialised correctly")
        self.assertEqual(mock.call_count, 0,
                         "call_count not initialised correctly")
        self.assertTrue(is_instance(mock.return_value, Mock),
                        "return_value not initialised correctly")

        self.assertEqual(mock.call_args, None,
                         "call_args not initialised correctly")
        self.assertEqual(mock.call_args_list, [],
                         "call_args_list not initialised correctly")
        self.assertEqual(mock.method_calls, [],
                          "method_calls not initialised correctly")

        # Can't use hasattr for this test as it always returns True on a mock
        # 不能使用 hasattr(mock, '_items'), 因为它会触发 mock.__getattr__ 方法, 然后其内部会返回一个新的(子)mock对象.
        # 但是可以使用 '_items' in mock.__dict__ 和 hasattr(mock.__dict__, '_items'),
        # 因为他们触发的是 __dict__ (字典)的__getitem__/__getattr__方法, 而不是mock的.
        self.assertNotIn('_items', mock.__dict__,
                         "default mock should not have '_items' attribute")

        self.assertIsNone(mock._mock_parent,
                          "parent not initialised correctly")
        self.assertIsNone(mock._mock_methods,
                          "methods not initialised correctly")
        self.assertEqual(mock._mock_children, {},
                         "children not initialised incorrectly")

    ###################################################################################################################
    # Mock的return_value的默认值是 Sentinels.DEFAULT, 所以当初始化Mock时提供了实参(则会覆盖掉Sentinels.DEFAULT),
    # 那么后续访问 mock.return_value 都会返回那个实参值.
    ###################################################################################################################
    def test_return_value_in_constructor(self):
        mock = Mock(return_value=None)
        self.assertIsNone(mock.return_value,
                          "return value in constructor not honoured")

    ###################################################################################################################
    # create_autospec 返回的是一个 <function f at 0x00001B57DFE2340 > 对象, 该对象是一个未被执行过的函数对象, 不是Mock对象.
    # create_autospec 的参数是 f 函数, 用于声明 f 是一个 spec 限定对象.
    # create_autospec 虽然返回的不是一个mock对象, 但是它内部还是有创建mock对象的,
    #                 并将其挂到 <function f at 0x00001B57DFE2340 > 的属性中,
    #                 像下面的代码, 当执行 mock() 时, 其实是在执行  <function f at 0x00001B57DFE2340 > 对象,
    #                 内部会先做 参数签名检查 是否与 f 限定对象的参数签名一致, 如果不一直则会报错.
    #                 内部然后再执行 <function f at 0x00001B57DFE2340 >.mock(),
    #                 从而触发 mock.__call__ 来获取 mock.return_value 的值.
    #
    # 补充:
    # 当函数 f 定义了形式参数时, 例如: def f(first_thing): pass
    # 那么下面的 mock() 就会报错, 必须要 mock(first_thing="brush_teeth") 才符合参数签名检查.
    # 也就是说 f 这个限定对象, 在这里就是那个要被模拟(MOCK)的对象.
    ###################################################################################################################
    def test_change_return_value_via_delegate(self):
        def f(): pass
        mock = create_autospec(f)
        mock.mock.return_value = 1
        self.assertEqual(mock(), 1)

    ###################################################################################################################
    # 一般情况下 self.assertTrue(实际运行结果值, 预期返回值, 错误信息);
    # 但是对报错的预期不能这么写, 因为这样写并不能捕获异常, 也不能对异常设定预期.
    #
    # self.assertRaises 返回一个 _AssertRaisesContext 对象, 它在实例化时期望形式参数是 Exception 类型(暂存于self.expected).
    # 关键字 with 作用于 _AssertRaisesContext.__enter__ 和 _AssertRaisesContext.__exit__,
    # 其中 __enter__ 仅返回self; 异常匹配的环节留在 __exit__ 中进行匹配;
    # 异常信息和预期异常匹配命中则返回True, 匹配不命中则会将异常抛给unittest.case.TestCase, 它会在退出程序时统一打印出异常信息.
    ###################################################################################################################
    def test_change_side_effect_via_delegate(self):
        def f(): pass
        mock = create_autospec(f)
        mock.mock.side_effect = TypeError()
        with self.assertRaises(TypeError):
            mock()

    ###################################################################################################################
    # repr在 _extract_mock_name 中采用了递归提取所有parent的name, 纳入一个集合然后再将其反转, 得出一个正向的调用路径.
    # 这个代码主要时测试repr能不能正确的将调用路径打印出来, 举例:
    # self.assertIn('%s()().foo.bar.baz().bing' % name, repr(mock()().foo.bar.baz().bing))
    # mock = Mock(name='foo')   实例化一个mock对象
    # mock()                    触发 __call__ 方法, 由于没有提供return_value, 也没有提供side_effect,
    #                           所以会进入这个方法 mock.__get_return_value 试图返回一个新的子mock对象,
    #                           该子mock对象的name参数是'()', 表示执行了一次mock.
    #
    # ()                        触发 __call__ 方法, 同样会进入 mock.__get_return_value, 同样会返回一个新的子mock对象.
    #                           该子mock对象的name参数也是'()', 表示执行了一次mock.
    #
    # .foo                      触发 __getattr__ 方法, 在该方法中创建一个子mock对象(name='foo', _new_name='foo'),
    #                           并返回该mock对象, 当使用print或repr()触发 __repr__ 时, 会递归parent去提取所有的_mock_new_name,
    #                           存储在一个列表中, 然后再使用reverse将列表反转过来.
    #
    # .bar                      触发 __getattr__ 方法, 描述与 .foo 一样
    #
    # .baz()                    先触发 __getattr__ 方法, 然后再触发 __call__ 方法.
    #
    # .bing                     触发 __getattr__ 方法, 描述与 .foo 一样
    ###################################################################################################################
    def test_repr(self):
        mock = Mock(name='foo')
        self.assertIn('foo', repr(mock))
        self.assertIn("'%s'" % id(mock), repr(mock))

        mocks = [(Mock(), 'mock'), (Mock(name='bar'), 'bar')]
        for mock, name in mocks:
            self.assertIn('%s.bar' % name, repr(mock.bar))
            self.assertIn('%s.foo()' % name, repr(mock.foo()))
            self.assertIn('%s.foo().bing' % name, repr(mock.foo().bing))
            self.assertIn('%s()' % name, repr(mock()))
            self.assertIn('%s()()' % name, repr(mock()()))
            self.assertIn('%s()().foo.bar.baz().bing' % name,
                          repr(mock()().foo.bar.baz().bing))


    def test_repr_with_spec(self):
        class X(object):
            pass

        mock = Mock(spec=X)
        self.assertIn(" spec='X' ", repr(mock))

        mock = Mock(spec=X())
        self.assertIn(" spec='X' ", repr(mock))

        mock = Mock(spec_set=X)
        self.assertIn(" spec_set='X' ", repr(mock))

        mock = Mock(spec_set=X())
        self.assertIn(" spec_set='X' ", repr(mock))

        mock = Mock(spec=X, name='foo')
        self.assertIn(" spec='X' ", repr(mock))
        self.assertIn(" name='foo' ", repr(mock))

        mock = Mock(name='foo')
        self.assertNotIn("spec", repr(mock))

        mock = Mock()
        self.assertNotIn("spec", repr(mock))

        # 对 Mock/NonCallableMock 类对象来说, 当 spec 是一个列表/元组时, 不将其作为限定对象.
        #
        # 备注:
        # 对 create_autospec 函数来说, 当 spec 是一个列表/元组时,
        # 另有他用(将其视为是一个list限定对象), 参考: mock.py#4367: if _is_list(spec): spec = type(spec)
        mock = Mock(spec=['foo'])
        self.assertNotIn("spec", repr(mock))


    def test_side_effect(self):
        mock = Mock()

        # 这里测试 side_effect 报错是否符合预期, 同时也再测试参数签名是否准确.
        def effect(*args, **kwargs):
            raise SystemError('kablooie')

        mock.side_effect = effect
        self.assertRaises(SystemError, mock, 1, 2, fish=3)
        mock.assert_called_with(1, 2, fish=3)

        # 这里测试 side_effect 的函数执行功能, 同时也是测试 effect 函数对外部变量(results)的处理.
        results = [1, 2, 3]
        def effect():
            return results.pop()
        mock.side_effect = effect

        self.assertEqual([mock(), mock(), mock()], [3, 2, 1],
                          "side effect not used correctly")

        # 这里测试 side_effect 赋值是否有效.
        mock = Mock(side_effect=sentinel.SideEffect)
        self.assertEqual(mock.side_effect, sentinel.SideEffect,
                          "side effect in constructor not used")

        # 这里测试 side_effect 和 return_value 返回的优先级, 因该有限返回 return_value.
        def side_effect():
            return DEFAULT
        mock = Mock(side_effect=side_effect, return_value=sentinel.RETURN)
        self.assertEqual(mock(), sentinel.RETURN)

    def test_autospec_side_effect(self):
        # Test for issue17826
        results = [1, 2, 3]
        def effect():
            return results.pop()
        def f(): pass

        # mock 是一个 <function xx at 0x0001e> 未执行函数,
        # 对 <function xx at 0x0001e>.side_effect = [1,2,3]
        # 等同于 <function xx at 0x0001e>.mock.side_effect 操作;
        # 参考: mock.py#690 funcopy.side_effect = mock.side_effect
        #
        # 当 side_effect 是一个iterable对象时(列表/元组/generator), 每次 __call__ 触发都会提取一个元素.
        mock = create_autospec(f)
        mock.side_effect = [1, 2, 3]
        self.assertEqual([mock(), mock(), mock()], [1, 2, 3],
                          "side effect not used correctly in create_autospec")

        # 测试side_effect执行函数的结果.
        # Test where side effect is a callable
        results = [1, 2, 3]
        mock = create_autospec(f)
        mock.side_effect = effect
        self.assertEqual([mock(), mock(), mock()], [3, 2, 1],
                          "callable side effect not used correctly")

    def test_autospec_side_effect_exception(self):
        # Test for issue 23661
        def f(): pass

        mock = create_autospec(f)
        mock.side_effect = ValueError('Bazinga!')

        # assertRaisesRegex 会执行 mock 函数,
        # _AssertRaisesContext.__exit__ 会将报错信息 和 'Bazinga!' 做正则匹配,
        # 匹配成功则不会报错,
        # 匹配失败则会将失败信息暂存在unittest.runner.TextTestRunner的failures中, 所有case执行完成之后, 统一打印错误信息.
        #
        # 备注:
        # 报错处理优先级(顺序):
        # 1. 先进入 with 关键字的 __exit__
        # 2. 再进入 try except 的 Exception 条件块.
        self.assertRaisesRegex(ValueError, 'Bazinga!', mock)


    def test_reset_mock(self):
        parent = Mock()

        # spec 如果是一个对象, 那么它将被用来充当限定对象(它有那些属性, 那么就只能访问或者赋值给这些属性, 否则报错).
        # spec 如果是一个列表, 那么这个列表就是一个限定集合(只能访问或赋值给这个限定结合, 否则报错).
        spec = ["something"]
        mock = Mock(name="child", parent=parent, spec=spec)

        # 调用mock(触发mock.__call__), 内部: 保存调用参数签名, 追加统计信息.
        mock(sentinel.Something, something=sentinel.SomethingElse)

        # something不存在于mock属性中, 在 __getattr__ 中尝试创建一个新的mock返回并赋值给something变量.
        something = mock.something

        # 调用一次mock.something, 那么mock.something._mock_called == True
        mock.something()

        # 更改 mock.side_effect 的值
        mock.side_effect = sentinel.SideEffect

        # 由于上面初始化时没有提供return_value参数, 这里回返回一个mock对象.
        # 对应的, return_value() 等同于 mock._mock_return_value(),
        # mock._mock_return_value.called = True
        return_value = mock.return_value
        return_value()

        # 这里除了重置mock对象, 也会递归的去执行子mock的reset_mock().
        # mock.something 是子mock
        # mock.return_value 不是子mock
        # 因为 mock.something 触发的是 __getattr__ , 在创建mock之后会将其纳入到 mock._mock_children 中.
        # 而 mock.return_value 触发的是 __get_return_value, 该方法只创建mock不纳入 mock._mock_children 中.
        # 虽然 mock._mock_return_value 不是子mock, 但是 reset_mock 最后一段代码还是单独处理(reset)了 _mock_return_value.
        mock.reset_mock()

        # 重置mock不更改name, 所以这里期望的是实例化时提供的参数值.
        self.assertEqual(mock._mock_name, "child",
                         "name incorrectly reset")
        # 重置mock不更改parent, 所以这里期望的是实例化时提供的参数值.
        self.assertEqual(mock._mock_parent, parent,
                         "parent incorrectly reset")
        # 重置mock不更改spec, 所以这里期望的是实例化时提供的参数值.
        self.assertEqual(mock._mock_methods, spec,
                         "methods incorrectly reset")

        self.assertFalse(mock.called, "called not reset")
        self.assertEqual(mock.call_count, 0, "call_count not reset")
        self.assertEqual(mock.call_args, None, "call_args not reset")
        self.assertEqual(mock.call_args_list, [], "call_args_list not reset")
        self.assertEqual(mock.method_calls, [],
                        "method_calls not initialised correctly: %r != %r" %
                        (mock.method_calls, []))
        self.assertEqual(mock.mock_calls, [])

        self.assertEqual(mock.side_effect, sentinel.SideEffect,
                          "side_effect incorrectly reset")

        # reset_mock()
        # 参数return_value默认值是False(意思是: 不要重置mock._mock_return_value的值)
        # 参数return_valuem如果是True(意思是: 重置mock._mock_return_value的值为 sentinel.DETAULT)
        # 这里的选择是不重置return_value, 所以这里期望的是 mock.return_value == mock == return_value;
        self.assertEqual(mock.return_value, return_value,
                          "return_value incorrectly reset")

        # mock._mock_return_value 已重置, 所以这里预期是 False.
        self.assertFalse(return_value.called, "return value mock not reset")

        # reset_mock 不重置 _mock_children 集合, 所以这里预期不变.
        self.assertEqual(mock._mock_children, {'something': something},
                          "children reset incorrectly")
        self.assertEqual(mock.something, something,
                          "children incorrectly cleared")

        # reset_mock 充值了子mock, 所以这里期望的是False.
        self.assertFalse(mock.something.called, "child not reset")


    def test_reset_mock_recursion(self):
        mock = Mock()
        mock.return_value = mock

        # used to cause recursion
        mock.reset_mock()

    def test_reset_mock_on_mock_open_issue_18622(self):
        a = mock.mock_open()
        a.reset_mock()

    def test_call(self):
        mock = Mock()

        # 空参数实例化mock的情况下(return_value为sentinel.DEFAULT),
        # mock.return_value 触发 __get_return_value,
        # 返回一个子mock对象, _new_name='()'.
        # 子mock是 Mock对象, 所以这里是True
        self.assertTrue(is_instance(mock.return_value, Mock),
                        "Default return_value should be a Mock")

        # 前面调用 mock.return_value, 导致 mock.return_value 从 sentinel.DEFAULT 变成了子mock对象.
        # 又因为 __call__ 里面判断说: 当 self._mock_return_value 不是 sentinel.DEFAULT 时, 返回 self.return_value.
        # 所以这里直接执行 mock() 返回的是 mock.return_value 的值(也就是那个子mock对象).
        # 因此这里测试的就是这个条件句.
        result = mock()
        self.assertEqual(mock(), result,
                         "different result from consecutive calls")

        # 重置mock
        # return_value默认是False, 表示不重置 mock._mock_return_value,
        # 所以这里 mock._mock_return_value 是一个子mock对象.
        mock.reset_mock()

        # 执行一次mock, 传递的参数是 sentinel.Arg;
        # 期望:
        # mock.called           == True
        # mock.call_count       == 1
        # mock.call_args        == ((sentinel.Arg,), {}) == (args, kwargs)
        # mock.call_args.args   == (sentinel.Arg, )
        # mock.call_args.kwargs == {}
        # mock.call_args_list   == [((sentinel.Arg, ), {}) ]
        ret_val = mock(sentinel.Arg)
        self.assertTrue(mock.called, "called not set")
        self.assertEqual(mock.call_count, 1, "call_count incoreect")
        self.assertEqual(mock.call_args, ((sentinel.Arg,), {}),
                         "call_args not set")
        self.assertEqual(mock.call_args.args, (sentinel.Arg,),
                         "call_args not set")
        self.assertEqual(mock.call_args.kwargs, {},
                         "call_args not set")
        self.assertEqual(mock.call_args_list, [((sentinel.Arg,), {})],
                         "call_args_list not initialised correctly")

        # 更改 mock.return_value 的值, 触发 __set_return_value 方法完成赋值.
        mock.return_value = sentinel.ReturnValue
        # 验证返回值 ret_val 是 sentinel.ReturnValue
        # 并期望:
        # mock.call_count == 2
        # mock.call_args == ((sentinel.Arg, {'key': sentinel.KeyArg}))
        # mock.call_args_list == [ ((sentinel.Arg, ), {}), ((sentinel.Arg, ), {'key': sentinel.KeyArg}) ]
        ret_val = mock(sentinel.Arg, key=sentinel.KeyArg)
        self.assertEqual(ret_val, sentinel.ReturnValue,
                         "incorrect return value")

        self.assertEqual(mock.call_count, 2, "call_count incorrect")
        self.assertEqual(mock.call_args,
                         ((sentinel.Arg,), {'key': sentinel.KeyArg}),
                         "call_args not set")
        self.assertEqual(mock.call_args_list, [
            ((sentinel.Arg,), {}),
            ((sentinel.Arg,), {'key': sentinel.KeyArg})
        ],
            "call_args_list not set")


    ###################################################################################################################
    # 从现在开始看函数名字, 自己通过分析源码来写测试, 然后再与实际测试相比较; 锻炼自己写测试用例的能力.
    ###################################################################################################################


    def test_call_args_comparison_bymyself(self):
        """
        背景介绍
        call_args 是 mock 对象中的一个 property 对象,
        当通过执行 mock.call_args 指令时, 实际上是再访问 mock._mock_call_args .

        mock = Mock() 初始化时 _mock_call_args 属性的默认值是 None,
        mock() 调用mock时, 会在 NonCallableMock._increment_mock_call 中为 _mock_call_Args 赋值:
            _call = _Call((args, kwargs), two=True)
            self.call_args = _call


        明确测试目标
        call_args 的类型是 _Call 对象, 所以实际上是测试 _Call 对象的比较机制.

        测试范围
        围绕 _Call.__eq__ 中的每个条件句进行测试.
        1. 测试 ANY 对象: 如果 other 是 ANY, 那么就返回True表示它们是相同的.
        2. 测试 _mock_parent: 如果两个 _mock_parent 不一样, 那么就返回False表示不一样.
        3. 测试 多种参数组合 比较.
        """
        ss = _Call((['a', 'b', 'c'], {'d': 1, 'e': 2}))
        self.assertEqual(ss, mock.ANY, "_Call 与 ANY 对象比较时, 应该总是返回True.")

        m = Mock()
        bb = _Call((['a', 'b', 'c'], {'d': 1, 'e': 2}), parent=m)
        self.assertEqual(ss, bb, "只有当两个 _Call 同时拥有parent的时候, 才做比较.")

        cc = _Call((['a', 'b', 'c'], {'d': 1, 'e': 2}), parent=m)
        self.assertEqual(bb, cc, "两个 _Call 对象的 parent 不一致.")

        m2 = Mock()
        dd = _Call((['a', 'b', 'c'], {'d': 1, 'e': 2}), parent=m2)
        self.assertNotEqual(cc, dd, "两个 _Call 对象的 parent 不一致.")

        mock_comp = Mock()
        mock_comp()
        mock_comp("ok")
        mock_comp("good", "morning")
        mock_comp("good", "morning", oooo="xxxx")
        self.assertEqual(mock_comp.call_args_list, [((), {}),
                                                    (("ok",), {}),
                                                    (("good", "morning"), {}),
                                                    (("good", "morning"), {"oooo":"xxxx"})])
        """
        总结: 
        测试范围列出了三个测试case, 
        这里将三个测试case写在了一起, 
        虽然都是参数比较, 但官方的测试case时将它们分开来.
        
        官方是尽量使用 sentinel 来配合测试, 而我是采用字符串测试.
        """

    def test_call_args_comparison(self):
        mock = Mock()
        mock()
        mock(sentinel.Arg)
        mock(kw=sentinel.Kwarg)
        mock(sentinel.Arg, kw=sentinel.Kwarg)
        self.assertEqual(mock.call_args_list, [
            (),
            ((sentinel.Arg,),),
            ({"kw": sentinel.Kwarg},),
            ((sentinel.Arg,), {"kw": sentinel.Kwarg})
        ])
        self.assertEqual(mock.call_args,
                         ((sentinel.Arg,), {"kw": sentinel.Kwarg}))
        self.assertEqual(mock.call_args.args, (sentinel.Arg,))
        self.assertEqual(mock.call_args.kwargs, {"kw": sentinel.Kwarg})

        # Comparing call_args to a long sequence should not raise
        # an exception. See issue 24857.
        self.assertFalse(mock.call_args == "a long sequence")


    def test_calls_equal_with_any(self):
        # Check that equality and non-equality is consistent even when
        # comparing with mock.ANY
        mm = mock.MagicMock()
        self.assertTrue(mm == mm)
        self.assertFalse(mm != mm)
        self.assertFalse(mm == mock.MagicMock())
        self.assertTrue(mm != mock.MagicMock())
        self.assertTrue(mm == mock.ANY)
        self.assertFalse(mm != mock.ANY)
        self.assertTrue(mock.ANY == mm)
        self.assertFalse(mock.ANY != mm)

        call1 = mock.call(mock.MagicMock())
        call2 = mock.call(mock.ANY)
        self.assertTrue(call1 == call2)
        self.assertFalse(call1 != call2)
        self.assertTrue(call2 == call1)
        self.assertFalse(call2 != call1)


    def test_assert_called_with(self):
        mock = Mock()
        mock()

        # Will raise an exception if it fails
        mock.assert_called_with()
        self.assertRaises(AssertionError, mock.assert_called_with, 1)

        mock.reset_mock()
        self.assertRaises(AssertionError, mock.assert_called_with)

        mock(1, 2, 3, a='fish', b='nothing')
        mock.assert_called_with(1, 2, 3, a='fish', b='nothing')


    def test_assert_called_with_any(self):
        m = MagicMock()
        m(MagicMock())
        m.assert_called_with(mock.ANY)


    def test_assert_called_with_function_spec(self):
        def f(a, b, c, d=None): pass

        mock = Mock(spec=f)

        mock(1, b=2, c=3)
        mock.assert_called_with(1, 2, 3)
        mock.assert_called_with(a=1, b=2, c=3)
        self.assertRaises(AssertionError, mock.assert_called_with,
                          1, b=3, c=2)
        # Expected call doesn't match the spec's signature
        with self.assertRaises(AssertionError) as cm:
            mock.assert_called_with(e=8)
        self.assertIsInstance(cm.exception.__cause__, TypeError)


    def test_assert_called_with_method_spec(self):
        def _check(mock):
            mock(1, b=2, c=3)
            mock.assert_called_with(1, 2, 3)
            mock.assert_called_with(a=1, b=2, c=3)
            self.assertRaises(AssertionError, mock.assert_called_with,
                              1, b=3, c=2)

        mock = Mock(spec=Something().meth)
        _check(mock)
        mock = Mock(spec=Something.cmeth)
        _check(mock)
        mock = Mock(spec=Something().cmeth)
        _check(mock)
        mock = Mock(spec=Something.smeth)
        _check(mock)
        mock = Mock(spec=Something().smeth)
        _check(mock)


    def test_assert_called_exception_message(self):
        msg = "Expected '{0}' to have been called"
        with self.assertRaisesRegex(AssertionError, msg.format('mock')):
            Mock().assert_called()
        with self.assertRaisesRegex(AssertionError, msg.format('test_name')):
            Mock(name="test_name").assert_called()


    def test_assert_called_once_with(self):
        mock = Mock()
        mock()

        # Will raise an exception if it fails
        mock.assert_called_once_with()

        mock()
        self.assertRaises(AssertionError, mock.assert_called_once_with)

        mock.reset_mock()
        self.assertRaises(AssertionError, mock.assert_called_once_with)

        mock('foo', 'bar', baz=2)
        mock.assert_called_once_with('foo', 'bar', baz=2)

        mock.reset_mock()
        mock('foo', 'bar', baz=2)
        self.assertRaises(
            AssertionError,
            lambda: mock.assert_called_once_with('bob', 'bar', baz=2)
        )

    def test_assert_called_once_with_call_list(self):
        m = Mock()
        m(1)
        m(2)
        self.assertRaisesRegex(AssertionError,
            re.escape("Calls: [call(1), call(2)]"),
            lambda: m.assert_called_once_with(2))


    def test_assert_called_once_with_function_spec(self):
        def f(a, b, c, d=None): pass

        mock = Mock(spec=f)

        mock(1, b=2, c=3)
        mock.assert_called_once_with(1, 2, 3)
        mock.assert_called_once_with(a=1, b=2, c=3)
        self.assertRaises(AssertionError, mock.assert_called_once_with,
                          1, b=3, c=2)
        # Expected call doesn't match the spec's signature
        with self.assertRaises(AssertionError) as cm:
            mock.assert_called_once_with(e=8)
        self.assertIsInstance(cm.exception.__cause__, TypeError)
        # Mock called more than once => always fails
        mock(4, 5, 6)
        self.assertRaises(AssertionError, mock.assert_called_once_with,
                          1, 2, 3)
        self.assertRaises(AssertionError, mock.assert_called_once_with,
                          4, 5, 6)


    def test_attribute_access_returns_mocks(self):
        mock = Mock()
        something = mock.something
        self.assertTrue(is_instance(something, Mock), "attribute isn't a mock")
        self.assertEqual(mock.something, something,
                         "different attributes returned for same name")

        # Usage example
        mock = Mock()
        mock.something.return_value = 3

        self.assertEqual(mock.something(), 3, "method returned wrong value")
        self.assertTrue(mock.something.called,
                        "method didn't record being called")


    def test_attributes_have_name_and_parent_set(self):
        mock = Mock()
        something = mock.something

        self.assertEqual(something._mock_name, "something",
                         "attribute name not set correctly")
        self.assertEqual(something._mock_parent, mock,
                         "attribute parent not set correctly")


    def test_method_calls_recorded(self):
        mock = Mock()
        mock.something(3, fish=None)
        mock.something_else.something(6, cake=sentinel.Cake)

        self.assertEqual(mock.something_else.method_calls,
                          [("something", (6,), {'cake': sentinel.Cake})],
                          "method calls not recorded correctly")
        self.assertEqual(mock.method_calls, [
            ("something", (3,), {'fish': None}),
            ("something_else.something", (6,), {'cake': sentinel.Cake})
        ],
            "method calls not recorded correctly")


    def test_method_calls_compare_easily(self):
        mock = Mock()
        mock.something()
        self.assertEqual(mock.method_calls, [('something',)])
        self.assertEqual(mock.method_calls, [('something', (), {})])

        mock = Mock()
        mock.something('different')
        self.assertEqual(mock.method_calls, [('something', ('different',))])
        self.assertEqual(mock.method_calls,
                         [('something', ('different',), {})])

        mock = Mock()
        mock.something(x=1)
        self.assertEqual(mock.method_calls, [('something', {'x': 1})])
        self.assertEqual(mock.method_calls, [('something', (), {'x': 1})])

        mock = Mock()
        mock.something('different', some='more')
        self.assertEqual(mock.method_calls, [
            ('something', ('different',), {'some': 'more'})
        ])


    def test_only_allowed_methods_exist(self):
        for spec in ['something'], ('something',):
            for arg in 'spec', 'spec_set':
                mock = Mock(**{arg: spec})

                # this should be allowed
                mock.something
                self.assertRaisesRegex(
                    AttributeError,
                    "Mock object has no attribute 'something_else'",
                    getattr, mock, 'something_else'
                )


    def test_from_spec(self):
        class Something(object):
            x = 3
            __something__ = None
            def y(self): pass

        def test_attributes(mock):
            # should work
            mock.x
            mock.y
            mock.__something__
            self.assertRaisesRegex(
                AttributeError,
                "Mock object has no attribute 'z'",
                getattr, mock, 'z'
            )
            self.assertRaisesRegex(
                AttributeError,
                "Mock object has no attribute '__foobar__'",
                getattr, mock, '__foobar__'
            )

        test_attributes(Mock(spec=Something))
        test_attributes(Mock(spec=Something()))


    def test_wraps_calls(self):
        real = Mock()

        mock = Mock(wraps=real)
        self.assertEqual(mock(), real())

        real.reset_mock()

        mock(1, 2, fish=3)
        real.assert_called_with(1, 2, fish=3)


    def test_wraps_prevents_automatic_creation_of_mocks(self):
        class Real(object):
            pass

        real = Real()
        mock = Mock(wraps=real)

        self.assertRaises(AttributeError, lambda: mock.new_attr())


    def test_wraps_call_with_nondefault_return_value(self):
        real = Mock()

        mock = Mock(wraps=real)
        mock.return_value = 3

        self.assertEqual(mock(), 3)
        self.assertFalse(real.called)


    def test_wraps_attributes(self):
        class Real(object):
            attribute = Mock()

        real = Real()

        mock = Mock(wraps=real)
        self.assertEqual(mock.attribute(), real.attribute())
        self.assertRaises(AttributeError, lambda: mock.fish)

        self.assertNotEqual(mock.attribute, real.attribute)
        result = mock.attribute.frog(1, 2, fish=3)
        Real.attribute.frog.assert_called_with(1, 2, fish=3)
        self.assertEqual(result, Real.attribute.frog())


    def test_customize_wrapped_object_with_side_effect_iterable_with_default(self):
        class Real(object):
            def method(self):
                return sentinel.ORIGINAL_VALUE

        real = Real()
        mock = Mock(wraps=real)
        mock.method.side_effect = [sentinel.VALUE1, DEFAULT]

        self.assertEqual(mock.method(), sentinel.VALUE1)
        self.assertEqual(mock.method(), sentinel.ORIGINAL_VALUE)
        self.assertRaises(StopIteration, mock.method)


    def test_customize_wrapped_object_with_side_effect_iterable(self):
        class Real(object):
            def method(self): pass

        real = Real()
        mock = Mock(wraps=real)
        mock.method.side_effect = [sentinel.VALUE1, sentinel.VALUE2]

        self.assertEqual(mock.method(), sentinel.VALUE1)
        self.assertEqual(mock.method(), sentinel.VALUE2)
        self.assertRaises(StopIteration, mock.method)


    def test_customize_wrapped_object_with_side_effect_exception(self):
        class Real(object):
            def method(self): pass

        real = Real()
        mock = Mock(wraps=real)
        mock.method.side_effect = RuntimeError

        self.assertRaises(RuntimeError, mock.method)


    def test_customize_wrapped_object_with_side_effect_function(self):
        class Real(object):
            def method(self): pass
        def side_effect():
            return sentinel.VALUE

        real = Real()
        mock = Mock(wraps=real)
        mock.method.side_effect = side_effect

        self.assertEqual(mock.method(), sentinel.VALUE)


    def test_customize_wrapped_object_with_return_value(self):
        class Real(object):
            def method(self): pass

        real = Real()
        mock = Mock(wraps=real)
        mock.method.return_value = sentinel.VALUE

        self.assertEqual(mock.method(), sentinel.VALUE)


    def test_customize_wrapped_object_with_return_value_and_side_effect(self):
        # side_effect should always take precedence over return_value.
        class Real(object):
            def method(self): pass

        real = Real()
        mock = Mock(wraps=real)
        mock.method.side_effect = [sentinel.VALUE1, sentinel.VALUE2]
        mock.method.return_value = sentinel.WRONG_VALUE

        self.assertEqual(mock.method(), sentinel.VALUE1)
        self.assertEqual(mock.method(), sentinel.VALUE2)
        self.assertRaises(StopIteration, mock.method)


    def test_customize_wrapped_object_with_return_value_and_side_effect2(self):
        # side_effect can return DEFAULT to default to return_value
        class Real(object):
            def method(self): pass

        real = Real()
        mock = Mock(wraps=real)
        mock.method.side_effect = lambda: DEFAULT
        mock.method.return_value = sentinel.VALUE

        self.assertEqual(mock.method(), sentinel.VALUE)


    def test_customize_wrapped_object_with_return_value_and_side_effect_default(self):
        class Real(object):
            def method(self): pass

        real = Real()
        mock = Mock(wraps=real)
        mock.method.side_effect = [sentinel.VALUE1, DEFAULT]
        mock.method.return_value = sentinel.RETURN

        self.assertEqual(mock.method(), sentinel.VALUE1)
        self.assertEqual(mock.method(), sentinel.RETURN)
        self.assertRaises(StopIteration, mock.method)


    def test_exceptional_side_effect(self):
        mock = Mock(side_effect=AttributeError)
        self.assertRaises(AttributeError, mock)

        mock = Mock(side_effect=AttributeError('foo'))
        self.assertRaises(AttributeError, mock)


    def test_baseexceptional_side_effect(self):
        mock = Mock(side_effect=KeyboardInterrupt)
        self.assertRaises(KeyboardInterrupt, mock)

        mock = Mock(side_effect=KeyboardInterrupt('foo'))
        self.assertRaises(KeyboardInterrupt, mock)


    def test_assert_called_with_message(self):
        mock = Mock()
        self.assertRaisesRegex(AssertionError, 'not called',
                                mock.assert_called_with)


    def test_assert_called_once_with_message(self):
        mock = Mock(name='geoffrey')
        self.assertRaisesRegex(AssertionError,
                     r"Expected 'geoffrey' to be called once\.",
                     mock.assert_called_once_with)


    def test__name__(self):
        mock = Mock()
        self.assertRaises(AttributeError, lambda: mock.__name__)

        mock.__name__ = 'foo'
        self.assertEqual(mock.__name__, 'foo')


    def test_spec_list_subclass(self):
        class Sub(list):
            pass
        mock = Mock(spec=Sub(['foo']))

        mock.append(3)
        mock.append.assert_called_with(3)
        self.assertRaises(AttributeError, getattr, mock, 'foo')


    def test_spec_class(self):
        class X(object):
            pass

        mock = Mock(spec=X)
        self.assertIsInstance(mock, X)

        mock = Mock(spec=X())
        self.assertIsInstance(mock, X)

        self.assertIs(mock.__class__, X)
        self.assertEqual(Mock().__class__.__name__, 'Mock')

        mock = Mock(spec_set=X)
        self.assertIsInstance(mock, X)

        mock = Mock(spec_set=X())
        self.assertIsInstance(mock, X)


    def test_spec_class_no_object_base(self):
        class X:
            pass

        mock = Mock(spec=X)
        self.assertIsInstance(mock, X)

        mock = Mock(spec=X())
        self.assertIsInstance(mock, X)

        self.assertIs(mock.__class__, X)
        self.assertEqual(Mock().__class__.__name__, 'Mock')

        mock = Mock(spec_set=X)
        self.assertIsInstance(mock, X)

        mock = Mock(spec_set=X())
        self.assertIsInstance(mock, X)


    def test_setting_attribute_with_spec_set(self):
        class X(object):
            y = 3

        mock = Mock(spec=X)
        mock.x = 'foo'

        mock = Mock(spec_set=X)
        def set_attr():
            mock.x = 'foo'

        mock.y = 'foo'
        self.assertRaises(AttributeError, set_attr)


    def test_copy(self):
        current = sys.getrecursionlimit()
        self.addCleanup(sys.setrecursionlimit, current)

        # can't use sys.maxint as this doesn't exist in Python 3
        sys.setrecursionlimit(int(10e8))
        # this segfaults without the fix in place
        copy.copy(Mock())


    def test_subclass_with_properties(self):
        class SubClass(Mock):
            def _get(self):
                return 3
            def _set(self, value):
                raise NameError('strange error')
            some_attribute = property(_get, _set)

        s = SubClass(spec_set=SubClass)
        self.assertEqual(s.some_attribute, 3)

        def test():
            s.some_attribute = 3
        self.assertRaises(NameError, test)

        def test():
            s.foo = 'bar'
        self.assertRaises(AttributeError, test)


    def test_setting_call(self):
        mock = Mock()
        def __call__(self, a):
            self._increment_mock_call(a)
            return self._mock_call(a)

        type(mock).__call__ = __call__
        mock('one')
        mock.assert_called_with('one')

        self.assertRaises(TypeError, mock, 'one', 'two')


    def test_dir(self):
        mock = Mock()
        attrs = set(dir(mock))
        type_attrs = set([m for m in dir(Mock) if not m.startswith('_')])

        # all public attributes from the type are included
        self.assertEqual(set(), type_attrs - attrs)

        # creates these attributes
        mock.a, mock.b
        self.assertIn('a', dir(mock))
        self.assertIn('b', dir(mock))

        # instance attributes
        mock.c = mock.d = None
        self.assertIn('c', dir(mock))
        self.assertIn('d', dir(mock))

        # magic methods
        mock.__iter__ = lambda s: iter([])
        self.assertIn('__iter__', dir(mock))


    def test_dir_from_spec(self):
        mock = Mock(spec=unittest.TestCase)
        testcase_attrs = set(dir(unittest.TestCase))
        attrs = set(dir(mock))

        # all attributes from the spec are included
        self.assertEqual(set(), testcase_attrs - attrs)

        # shadow a sys attribute
        mock.version = 3
        self.assertEqual(dir(mock).count('version'), 1)


    def test_filter_dir(self):
        patcher = patch.object(mock, 'FILTER_DIR', False)
        patcher.start()
        try:
            attrs = set(dir(Mock()))
            type_attrs = set(dir(Mock))

            # ALL attributes from the type are included
            self.assertEqual(set(), type_attrs - attrs)
        finally:
            patcher.stop()


    def test_dir_does_not_include_deleted_attributes(self):
        mock = Mock()
        mock.child.return_value = 1

        self.assertIn('child', dir(mock))
        del mock.child
        self.assertNotIn('child', dir(mock))


    def test_configure_mock(self):
        mock = Mock(foo='bar')
        self.assertEqual(mock.foo, 'bar')

        mock = MagicMock(foo='bar')
        self.assertEqual(mock.foo, 'bar')

        kwargs = {'side_effect': KeyError, 'foo.bar.return_value': 33,
                  'foo': MagicMock()}
        mock = Mock(**kwargs)
        self.assertRaises(KeyError, mock)
        self.assertEqual(mock.foo.bar(), 33)
        self.assertIsInstance(mock.foo, MagicMock)

        mock = Mock()
        mock.configure_mock(**kwargs)
        self.assertRaises(KeyError, mock)
        self.assertEqual(mock.foo.bar(), 33)
        self.assertIsInstance(mock.foo, MagicMock)


    def assertRaisesWithMsg(self, exception, message, func, *args, **kwargs):
        # needed because assertRaisesRegex doesn't work easily with newlines
        with self.assertRaises(exception) as context:
            func(*args, **kwargs)
        msg = str(context.exception)
        self.assertEqual(msg, message)


    def test_assert_called_with_failure_message(self):
        mock = NonCallableMock()

        actual = 'not called.'
        expected = "mock(1, '2', 3, bar='foo')"
        message = 'expected call not found.\nExpected: %s\nActual: %s'
        self.assertRaisesWithMsg(
            AssertionError, message % (expected, actual),
            mock.assert_called_with, 1, '2', 3, bar='foo'
        )

        mock.foo(1, '2', 3, foo='foo')


        asserters = [
            mock.foo.assert_called_with, mock.foo.assert_called_once_with
        ]
        for meth in asserters:
            actual = "foo(1, '2', 3, foo='foo')"
            expected = "foo(1, '2', 3, bar='foo')"
            message = 'expected call not found.\nExpected: %s\nActual: %s'
            self.assertRaisesWithMsg(
                AssertionError, message % (expected, actual),
                meth, 1, '2', 3, bar='foo'
            )

        # just kwargs
        for meth in asserters:
            actual = "foo(1, '2', 3, foo='foo')"
            expected = "foo(bar='foo')"
            message = 'expected call not found.\nExpected: %s\nActual: %s'
            self.assertRaisesWithMsg(
                AssertionError, message % (expected, actual),
                meth, bar='foo'
            )

        # just args
        for meth in asserters:
            actual = "foo(1, '2', 3, foo='foo')"
            expected = "foo(1, 2, 3)"
            message = 'expected call not found.\nExpected: %s\nActual: %s'
            self.assertRaisesWithMsg(
                AssertionError, message % (expected, actual),
                meth, 1, 2, 3
            )

        # empty
        for meth in asserters:
            actual = "foo(1, '2', 3, foo='foo')"
            expected = "foo()"
            message = 'expected call not found.\nExpected: %s\nActual: %s'
            self.assertRaisesWithMsg(
                AssertionError, message % (expected, actual), meth
            )


    def test_mock_calls(self):
        mock = MagicMock()

        # need to do this because MagicMock.mock_calls used to just return
        # a MagicMock which also returned a MagicMock when __eq__ was called
        self.assertIs(mock.mock_calls == [], True)

        mock = MagicMock()
        mock()
        expected = [('', (), {})]
        self.assertEqual(mock.mock_calls, expected)

        mock.foo()
        expected.append(call.foo())
        self.assertEqual(mock.mock_calls, expected)
        # intermediate mock_calls work too
        self.assertEqual(mock.foo.mock_calls, [('', (), {})])

        mock = MagicMock()
        mock().foo(1, 2, 3, a=4, b=5)
        expected = [
            ('', (), {}), ('().foo', (1, 2, 3), dict(a=4, b=5))
        ]
        self.assertEqual(mock.mock_calls, expected)
        self.assertEqual(mock.return_value.foo.mock_calls,
                         [('', (1, 2, 3), dict(a=4, b=5))])
        self.assertEqual(mock.return_value.mock_calls,
                         [('foo', (1, 2, 3), dict(a=4, b=5))])

        mock = MagicMock()
        mock().foo.bar().baz()
        expected = [
            ('', (), {}), ('().foo.bar', (), {}),
            ('().foo.bar().baz', (), {})
        ]
        self.assertEqual(mock.mock_calls, expected)
        self.assertEqual(mock().mock_calls,
                         call.foo.bar().baz().call_list())

        for kwargs in dict(), dict(name='bar'):
            mock = MagicMock(**kwargs)
            int(mock.foo)
            expected = [('foo.__int__', (), {})]
            self.assertEqual(mock.mock_calls, expected)

            mock = MagicMock(**kwargs)
            mock.a()()
            expected = [('a', (), {}), ('a()', (), {})]
            self.assertEqual(mock.mock_calls, expected)
            self.assertEqual(mock.a().mock_calls, [call()])

            mock = MagicMock(**kwargs)
            mock(1)(2)(3)
            self.assertEqual(mock.mock_calls, call(1)(2)(3).call_list())
            self.assertEqual(mock().mock_calls, call(2)(3).call_list())
            self.assertEqual(mock()().mock_calls, call(3).call_list())

            mock = MagicMock(**kwargs)
            mock(1)(2)(3).a.b.c(4)
            self.assertEqual(mock.mock_calls,
                             call(1)(2)(3).a.b.c(4).call_list())
            self.assertEqual(mock().mock_calls,
                             call(2)(3).a.b.c(4).call_list())
            self.assertEqual(mock()().mock_calls,
                             call(3).a.b.c(4).call_list())

            mock = MagicMock(**kwargs)
            int(mock().foo.bar().baz())
            last_call = ('().foo.bar().baz().__int__', (), {})
            self.assertEqual(mock.mock_calls[-1], last_call)
            self.assertEqual(mock().mock_calls,
                             call.foo.bar().baz().__int__().call_list())
            self.assertEqual(mock().foo.bar().mock_calls,
                             call.baz().__int__().call_list())
            self.assertEqual(mock().foo.bar().baz.mock_calls,
                             call().__int__().call_list())


    def test_child_mock_call_equal(self):
        m = Mock()
        result = m()
        result.wibble()
        # parent looks like this:
        self.assertEqual(m.mock_calls, [call(), call().wibble()])
        # but child should look like this:
        self.assertEqual(result.mock_calls, [call.wibble()])


    def test_mock_call_not_equal_leaf(self):
        m = Mock()
        m.foo().something()
        self.assertNotEqual(m.mock_calls[1], call.foo().different())
        self.assertEqual(m.mock_calls[0], call.foo())


    def test_mock_call_not_equal_non_leaf(self):
        m = Mock()
        m.foo().bar()
        self.assertNotEqual(m.mock_calls[1], call.baz().bar())
        self.assertNotEqual(m.mock_calls[0], call.baz())


    def test_mock_call_not_equal_non_leaf_params_different(self):
        m = Mock()
        m.foo(x=1).bar()
        # This isn't ideal, but there's no way to fix it without breaking backwards compatibility:
        self.assertEqual(m.mock_calls[1], call.foo(x=2).bar())


    def test_mock_call_not_equal_non_leaf_attr(self):
        m = Mock()
        m.foo.bar()
        self.assertNotEqual(m.mock_calls[0], call.baz.bar())


    def test_mock_call_not_equal_non_leaf_call_versus_attr(self):
        m = Mock()
        m.foo.bar()
        self.assertNotEqual(m.mock_calls[0], call.foo().bar())


    def test_mock_call_repr(self):
        m = Mock()
        m.foo().bar().baz.bob()
        self.assertEqual(repr(m.mock_calls[0]), 'call.foo()')
        self.assertEqual(repr(m.mock_calls[1]), 'call.foo().bar()')
        self.assertEqual(repr(m.mock_calls[2]), 'call.foo().bar().baz.bob()')


    def test_mock_call_repr_loop(self):
        m = Mock()
        m.foo = m
        repr(m.foo())
        self.assertRegex(repr(m.foo()), r"<Mock name='mock\(\)' id='\d+'>")


    def test_mock_calls_contains(self):
        m = Mock()
        self.assertFalse([call()] in m.mock_calls)


    def test_subclassing(self):
        class Subclass(Mock):
            pass

        mock = Subclass()
        self.assertIsInstance(mock.foo, Subclass)
        self.assertIsInstance(mock(), Subclass)

        class Subclass(Mock):
            def _get_child_mock(self, **kwargs):
                return Mock(**kwargs)

        mock = Subclass()
        self.assertNotIsInstance(mock.foo, Subclass)
        self.assertNotIsInstance(mock(), Subclass)


    def test_arg_lists(self):
        mocks = [
            Mock(),
            MagicMock(),
            NonCallableMock(),
            NonCallableMagicMock()
        ]

        def assert_attrs(mock):
            names = 'call_args_list', 'method_calls', 'mock_calls'
            for name in names:
                attr = getattr(mock, name)
                self.assertIsInstance(attr, _CallList)
                self.assertIsInstance(attr, list)
                self.assertEqual(attr, [])

        for mock in mocks:
            assert_attrs(mock)

            if callable(mock):
                mock()
                mock(1, 2)
                mock(a=3)

                mock.reset_mock()
                assert_attrs(mock)

            mock.foo()
            mock.foo.bar(1, a=3)
            mock.foo(1).bar().baz(3)

            mock.reset_mock()
            assert_attrs(mock)


    def test_call_args_two_tuple(self):
        mock = Mock()
        mock(1, a=3)
        mock(2, b=4)

        self.assertEqual(len(mock.call_args), 2)
        self.assertEqual(mock.call_args.args, (2,))
        self.assertEqual(mock.call_args.kwargs, dict(b=4))

        expected_list = [((1,), dict(a=3)), ((2,), dict(b=4))]
        for expected, call_args in zip(expected_list, mock.call_args_list):
            self.assertEqual(len(call_args), 2)
            self.assertEqual(expected[0], call_args[0])
            self.assertEqual(expected[1], call_args[1])


    def test_side_effect_iterator(self):
        mock = Mock(side_effect=iter([1, 2, 3]))
        self.assertEqual([mock(), mock(), mock()], [1, 2, 3])
        self.assertRaises(StopIteration, mock)

        mock = MagicMock(side_effect=['a', 'b', 'c'])
        self.assertEqual([mock(), mock(), mock()], ['a', 'b', 'c'])
        self.assertRaises(StopIteration, mock)

        mock = Mock(side_effect='ghi')
        self.assertEqual([mock(), mock(), mock()], ['g', 'h', 'i'])
        self.assertRaises(StopIteration, mock)

        class Foo(object):
            pass
        mock = MagicMock(side_effect=Foo)
        self.assertIsInstance(mock(), Foo)

        mock = Mock(side_effect=Iter())
        self.assertEqual([mock(), mock(), mock(), mock()],
                         ['this', 'is', 'an', 'iter'])
        self.assertRaises(StopIteration, mock)


    def test_side_effect_iterator_exceptions(self):
        for Klass in Mock, MagicMock:
            iterable = (ValueError, 3, KeyError, 6)
            m = Klass(side_effect=iterable)
            self.assertRaises(ValueError, m)
            self.assertEqual(m(), 3)
            self.assertRaises(KeyError, m)
            self.assertEqual(m(), 6)


    def test_side_effect_setting_iterator(self):
        mock = Mock()
        mock.side_effect = iter([1, 2, 3])
        self.assertEqual([mock(), mock(), mock()], [1, 2, 3])
        self.assertRaises(StopIteration, mock)
        side_effect = mock.side_effect
        self.assertIsInstance(side_effect, type(iter([])))

        mock.side_effect = ['a', 'b', 'c']
        self.assertEqual([mock(), mock(), mock()], ['a', 'b', 'c'])
        self.assertRaises(StopIteration, mock)
        side_effect = mock.side_effect
        self.assertIsInstance(side_effect, type(iter([])))

        this_iter = Iter()
        mock.side_effect = this_iter
        self.assertEqual([mock(), mock(), mock(), mock()],
                         ['this', 'is', 'an', 'iter'])
        self.assertRaises(StopIteration, mock)
        self.assertIs(mock.side_effect, this_iter)

    def test_side_effect_iterator_default(self):
        mock = Mock(return_value=2)
        mock.side_effect = iter([1, DEFAULT])
        self.assertEqual([mock(), mock()], [1, 2])

    def test_assert_has_calls_any_order(self):
        mock = Mock()
        mock(1, 2)
        mock(a=3)
        mock(3, 4)
        mock(b=6)
        mock(b=6)

        kalls = [
            call(1, 2), ({'a': 3},),
            ((3, 4),), ((), {'a': 3}),
            ('', (1, 2)), ('', {'a': 3}),
            ('', (1, 2), {}), ('', (), {'a': 3})
        ]
        for kall in kalls:
            mock.assert_has_calls([kall], any_order=True)

        for kall in call(1, '2'), call(b=3), call(), 3, None, 'foo':
            self.assertRaises(
                AssertionError, mock.assert_has_calls,
                [kall], any_order=True
            )

        kall_lists = [
            [call(1, 2), call(b=6)],
            [call(3, 4), call(1, 2)],
            [call(b=6), call(b=6)],
        ]

        for kall_list in kall_lists:
            mock.assert_has_calls(kall_list, any_order=True)

        kall_lists = [
            [call(b=6), call(b=6), call(b=6)],
            [call(1, 2), call(1, 2)],
            [call(3, 4), call(1, 2), call(5, 7)],
            [call(b=6), call(3, 4), call(b=6), call(1, 2), call(b=6)],
        ]
        for kall_list in kall_lists:
            self.assertRaises(
                AssertionError, mock.assert_has_calls,
                kall_list, any_order=True
            )

    def test_assert_has_calls(self):
        kalls1 = [
                call(1, 2), ({'a': 3},),
                ((3, 4),), call(b=6),
                ('', (1,), {'b': 6}),
        ]
        kalls2 = [call.foo(), call.bar(1)]
        kalls2.extend(call.spam().baz(a=3).call_list())
        kalls2.extend(call.bam(set(), foo={}).fish([1]).call_list())

        mocks = []
        for mock in Mock(), MagicMock():
            mock(1, 2)
            mock(a=3)
            mock(3, 4)
            mock(b=6)
            mock(1, b=6)
            mocks.append((mock, kalls1))

        mock = Mock()
        mock.foo()
        mock.bar(1)
        mock.spam().baz(a=3)
        mock.bam(set(), foo={}).fish([1])
        mocks.append((mock, kalls2))

        for mock, kalls in mocks:
            for i in range(len(kalls)):
                for step in 1, 2, 3:
                    these = kalls[i:i+step]
                    mock.assert_has_calls(these)

                    if len(these) > 1:
                        self.assertRaises(
                            AssertionError,
                            mock.assert_has_calls,
                            list(reversed(these))
                        )


    def test_assert_has_calls_nested_spec(self):
        class Something:

            def __init__(self): pass
            def meth(self, a, b, c, d=None): pass

            class Foo:

                def __init__(self, a): pass
                def meth1(self, a, b): pass

        mock_class = create_autospec(Something)

        for m in [mock_class, mock_class()]:
            m.meth(1, 2, 3, d=1)
            m.assert_has_calls([call.meth(1, 2, 3, d=1)])
            m.assert_has_calls([call.meth(1, 2, 3, 1)])

        mock_class.reset_mock()

        for m in [mock_class, mock_class()]:
            self.assertRaises(AssertionError, m.assert_has_calls, [call.Foo()])
            m.Foo(1).meth1(1, 2)
            m.assert_has_calls([call.Foo(1), call.Foo(1).meth1(1, 2)])
            m.Foo.assert_has_calls([call(1), call().meth1(1, 2)])

        mock_class.reset_mock()

        invalid_calls = [call.meth(1),
                         call.non_existent(1),
                         call.Foo().non_existent(1),
                         call.Foo().meth(1, 2, 3, 4)]

        for kall in invalid_calls:
            self.assertRaises(AssertionError,
                              mock_class.assert_has_calls,
                              [kall]
            )


    def test_assert_has_calls_nested_without_spec(self):
        m = MagicMock()
        m().foo().bar().baz()
        m.one().two().three()
        calls = call.one().two().three().call_list()
        m.assert_has_calls(calls)


    def test_assert_has_calls_with_function_spec(self):
        def f(a, b, c, d=None): pass

        mock = Mock(spec=f)

        mock(1, b=2, c=3)
        mock(4, 5, c=6, d=7)
        mock(10, 11, c=12)
        calls = [
            ('', (1, 2, 3), {}),
            ('', (4, 5, 6), {'d': 7}),
            ((10, 11, 12), {}),
            ]
        mock.assert_has_calls(calls)
        mock.assert_has_calls(calls, any_order=True)
        mock.assert_has_calls(calls[1:])
        mock.assert_has_calls(calls[1:], any_order=True)
        mock.assert_has_calls(calls[:-1])
        mock.assert_has_calls(calls[:-1], any_order=True)
        # Reversed order
        calls = list(reversed(calls))
        with self.assertRaises(AssertionError):
            mock.assert_has_calls(calls)
        mock.assert_has_calls(calls, any_order=True)
        with self.assertRaises(AssertionError):
            mock.assert_has_calls(calls[1:])
        mock.assert_has_calls(calls[1:], any_order=True)
        with self.assertRaises(AssertionError):
            mock.assert_has_calls(calls[:-1])
        mock.assert_has_calls(calls[:-1], any_order=True)

    def test_assert_has_calls_not_matching_spec_error(self):
        def f(x=None): pass

        mock = Mock(spec=f)
        mock(1)

        with self.assertRaisesRegex(
                AssertionError,
                '^{}$'.format(
                    re.escape('Calls not found.\n'
                              'Expected: [call()]\n'
                              'Actual: [call(1)]'))) as cm:
            mock.assert_has_calls([call()])
        self.assertIsNone(cm.exception.__cause__)


        with self.assertRaisesRegex(
                AssertionError,
                '^{}$'.format(
                    re.escape(
                        'Error processing expected calls.\n'
                        "Errors: [None, TypeError('too many positional arguments')]\n"
                        "Expected: [call(), call(1, 2)]\n"
                        'Actual: [call(1)]'))) as cm:
            mock.assert_has_calls([call(), call(1, 2)])
        self.assertIsInstance(cm.exception.__cause__, TypeError)

    def test_assert_any_call(self):
        mock = Mock()
        mock(1, 2)
        mock(a=3)
        mock(1, b=6)

        mock.assert_any_call(1, 2)
        mock.assert_any_call(a=3)
        mock.assert_any_call(1, b=6)

        self.assertRaises(
            AssertionError,
            mock.assert_any_call
        )
        self.assertRaises(
            AssertionError,
            mock.assert_any_call,
            1, 3
        )
        self.assertRaises(
            AssertionError,
            mock.assert_any_call,
            a=4
        )


    def test_assert_any_call_with_function_spec(self):
        def f(a, b, c, d=None): pass

        mock = Mock(spec=f)

        mock(1, b=2, c=3)
        mock(4, 5, c=6, d=7)
        mock.assert_any_call(1, 2, 3)
        mock.assert_any_call(a=1, b=2, c=3)
        mock.assert_any_call(4, 5, 6, 7)
        mock.assert_any_call(a=4, b=5, c=6, d=7)
        self.assertRaises(AssertionError, mock.assert_any_call,
                          1, b=3, c=2)
        # Expected call doesn't match the spec's signature
        with self.assertRaises(AssertionError) as cm:
            mock.assert_any_call(e=8)
        self.assertIsInstance(cm.exception.__cause__, TypeError)


    def test_mock_calls_create_autospec(self):
        def f(a, b): pass
        obj = Iter()
        obj.f = f

        funcs = [
            create_autospec(f),
            create_autospec(obj).f
        ]
        for func in funcs:
            func(1, 2)
            func(3, 4)

            self.assertEqual(
                func.mock_calls, [call(1, 2), call(3, 4)]
            )

    #Issue21222
    def test_create_autospec_with_name(self):
        m = mock.create_autospec(object(), name='sweet_func')
        self.assertIn('sweet_func', repr(m))

    #Issue23078
    def test_create_autospec_classmethod_and_staticmethod(self):
        class TestClass:
            @classmethod
            def class_method(cls): pass

            @staticmethod
            def static_method(): pass
        for method in ('class_method', 'static_method'):
            with self.subTest(method=method):
                mock_method = mock.create_autospec(getattr(TestClass, method))
                mock_method()
                mock_method.assert_called_once_with()
                self.assertRaises(TypeError, mock_method, 'extra_arg')

    #Issue21238
    def test_mock_unsafe(self):
        m = Mock()
        msg = "Attributes cannot start with 'assert' or 'assret'"
        with self.assertRaisesRegex(AttributeError, msg):
            m.assert_foo_call()
        with self.assertRaisesRegex(AttributeError, msg):
            m.assret_foo_call()
        m = Mock(unsafe=True)
        m.assert_foo_call()
        m.assret_foo_call()

    #Issue21262
    def test_assert_not_called(self):
        m = Mock()
        m.hello.assert_not_called()
        m.hello()
        with self.assertRaises(AssertionError):
            m.hello.assert_not_called()

    def test_assert_not_called_message(self):
        m = Mock()
        m(1, 2)
        self.assertRaisesRegex(AssertionError,
            re.escape("Calls: [call(1, 2)]"),
            m.assert_not_called)

    def test_assert_called(self):
        m = Mock()
        with self.assertRaises(AssertionError):
            m.hello.assert_called()
        m.hello()
        m.hello.assert_called()

        m.hello()
        m.hello.assert_called()

    def test_assert_called_once(self):
        m = Mock()
        with self.assertRaises(AssertionError):
            m.hello.assert_called_once()
        m.hello()
        m.hello.assert_called_once()

        m.hello()
        with self.assertRaises(AssertionError):
            m.hello.assert_called_once()

    def test_assert_called_once_message(self):
        m = Mock()
        m(1, 2)
        m(3)
        self.assertRaisesRegex(AssertionError,
            re.escape("Calls: [call(1, 2), call(3)]"),
            m.assert_called_once)

    def test_assert_called_once_message_not_called(self):
        m = Mock()
        with self.assertRaises(AssertionError) as e:
            m.assert_called_once()
        self.assertNotIn("Calls:", str(e.exception))

    #Issue37212 printout of keyword args now preserves the original order
    def test_ordered_call_signature(self):
        m = Mock()
        m.hello(name='hello', daddy='hero')
        text = "call(name='hello', daddy='hero')"
        self.assertEqual(repr(m.hello.call_args), text)

    #Issue21270 overrides tuple methods for mock.call objects
    def test_override_tuple_methods(self):
        c = call.count()
        i = call.index(132,'hello')
        m = Mock()
        m.count()
        m.index(132,"hello")
        self.assertEqual(m.method_calls[0], c)
        self.assertEqual(m.method_calls[1], i)

    def test_reset_return_sideeffect(self):
        m = Mock(return_value=10, side_effect=[2,3])
        m.reset_mock(return_value=True, side_effect=True)
        self.assertIsInstance(m.return_value, Mock)
        self.assertEqual(m.side_effect, None)

    def test_reset_return(self):
        m = Mock(return_value=10, side_effect=[2,3])
        m.reset_mock(return_value=True)
        self.assertIsInstance(m.return_value, Mock)
        self.assertNotEqual(m.side_effect, None)

    def test_reset_sideeffect(self):
        m = Mock(return_value=10, side_effect=[2,3])
        m.reset_mock(side_effect=True)
        self.assertEqual(m.return_value, 10)
        self.assertEqual(m.side_effect, None)

    def test_mock_add_spec(self):
        class _One(object):
            one = 1
        class _Two(object):
            two = 2
        class Anything(object):
            one = two = three = 'four'

        klasses = [
            Mock, MagicMock, NonCallableMock, NonCallableMagicMock
        ]
        for Klass in list(klasses):
            klasses.append(lambda K=Klass: K(spec=Anything))
            klasses.append(lambda K=Klass: K(spec_set=Anything))

        for Klass in klasses:
            for kwargs in dict(), dict(spec_set=True):
                mock = Klass()
                #no error
                mock.one, mock.two, mock.three

                for One, Two in [(_One, _Two), (['one'], ['two'])]:
                    for kwargs in dict(), dict(spec_set=True):
                        mock.mock_add_spec(One, **kwargs)

                        mock.one
                        self.assertRaises(
                            AttributeError, getattr, mock, 'two'
                        )
                        self.assertRaises(
                            AttributeError, getattr, mock, 'three'
                        )
                        if 'spec_set' in kwargs:
                            self.assertRaises(
                                AttributeError, setattr, mock, 'three', None
                            )

                        mock.mock_add_spec(Two, **kwargs)
                        self.assertRaises(
                            AttributeError, getattr, mock, 'one'
                        )
                        mock.two
                        self.assertRaises(
                            AttributeError, getattr, mock, 'three'
                        )
                        if 'spec_set' in kwargs:
                            self.assertRaises(
                                AttributeError, setattr, mock, 'three', None
                            )
            # note that creating a mock, setting an instance attribute, and
            # *then* setting a spec doesn't work. Not the intended use case


    def test_mock_add_spec_magic_methods(self):
        for Klass in MagicMock, NonCallableMagicMock:
            mock = Klass()
            int(mock)

            mock.mock_add_spec(object)
            self.assertRaises(TypeError, int, mock)

            mock = Klass()
            mock['foo']
            mock.__int__.return_value =4

            mock.mock_add_spec(int)
            self.assertEqual(int(mock), 4)
            self.assertRaises(TypeError, lambda: mock['foo'])


    def test_adding_child_mock(self):
        for Klass in (NonCallableMock, Mock, MagicMock, NonCallableMagicMock,
                      AsyncMock):
            mock = Klass()

            mock.foo = Mock()
            mock.foo()

            self.assertEqual(mock.method_calls, [call.foo()])
            self.assertEqual(mock.mock_calls, [call.foo()])

            mock = Klass()
            mock.bar = Mock(name='name')
            mock.bar()
            self.assertEqual(mock.method_calls, [])
            self.assertEqual(mock.mock_calls, [])

            # mock with an existing _new_parent but no name
            mock = Klass()
            mock.baz = MagicMock()()
            mock.baz()
            self.assertEqual(mock.method_calls, [])
            self.assertEqual(mock.mock_calls, [])


    def test_adding_return_value_mock(self):
        for Klass in Mock, MagicMock:
            mock = Klass()
            mock.return_value = MagicMock()

            mock()()
            self.assertEqual(mock.mock_calls, [call(), call()()])


    def test_manager_mock(self):
        class Foo(object):
            one = 'one'
            two = 'two'
        manager = Mock()
        p1 = patch.object(Foo, 'one')
        p2 = patch.object(Foo, 'two')

        mock_one = p1.start()
        self.addCleanup(p1.stop)
        mock_two = p2.start()
        self.addCleanup(p2.stop)

        manager.attach_mock(mock_one, 'one')
        manager.attach_mock(mock_two, 'two')

        Foo.two()
        Foo.one()

        self.assertEqual(manager.mock_calls, [call.two(), call.one()])


    def test_magic_methods_mock_calls(self):
        for Klass in Mock, MagicMock:
            m = Klass()
            m.__int__ = Mock(return_value=3)
            m.__float__ = MagicMock(return_value=3.0)
            int(m)
            float(m)

            self.assertEqual(m.mock_calls, [call.__int__(), call.__float__()])
            self.assertEqual(m.method_calls, [])

    def test_mock_open_reuse_issue_21750(self):
        mocked_open = mock.mock_open(read_data='data')
        f1 = mocked_open('a-name')
        f1_data = f1.read()
        f2 = mocked_open('another-name')
        f2_data = f2.read()
        self.assertEqual(f1_data, f2_data)

    def test_mock_open_dunder_iter_issue(self):
        # Test dunder_iter method generates the expected result and
        # consumes the iterator.
        mocked_open = mock.mock_open(read_data='Remarkable\nNorwegian Blue')
        f1 = mocked_open('a-name')
        lines = [line for line in f1]
        self.assertEqual(lines[0], 'Remarkable\n')
        self.assertEqual(lines[1], 'Norwegian Blue')
        self.assertEqual(list(f1), [])

    def test_mock_open_using_next(self):
        mocked_open = mock.mock_open(read_data='1st line\n2nd line\n3rd line')
        f1 = mocked_open('a-name')
        line1 = next(f1)
        line2 = f1.__next__()
        lines = [line for line in f1]
        self.assertEqual(line1, '1st line\n')
        self.assertEqual(line2, '2nd line\n')
        self.assertEqual(lines[0], '3rd line')
        self.assertEqual(list(f1), [])
        with self.assertRaises(StopIteration):
            next(f1)

    def test_mock_open_write(self):
        # Test exception in file writing write()
        mock_namedtemp = mock.mock_open(mock.MagicMock(name='JLV'))
        with mock.patch('tempfile.NamedTemporaryFile', mock_namedtemp):
            mock_filehandle = mock_namedtemp.return_value
            mock_write = mock_filehandle.write
            mock_write.side_effect = OSError('Test 2 Error')
            def attempt():
                tempfile.NamedTemporaryFile().write('asd')
            self.assertRaises(OSError, attempt)

    def test_mock_open_alter_readline(self):
        mopen = mock.mock_open(read_data='foo\nbarn')
        mopen.return_value.readline.side_effect = lambda *args:'abc'
        first = mopen().readline()
        second = mopen().readline()
        self.assertEqual('abc', first)
        self.assertEqual('abc', second)

    def test_mock_open_after_eof(self):
        # read, readline and readlines should work after end of file.
        _open = mock.mock_open(read_data='foo')
        h = _open('bar')
        h.read()
        self.assertEqual('', h.read())
        self.assertEqual('', h.read())
        self.assertEqual('', h.readline())
        self.assertEqual('', h.readline())
        self.assertEqual([], h.readlines())
        self.assertEqual([], h.readlines())

    def test_mock_parents(self):
        for Klass in Mock, MagicMock:
            m = Klass()
            original_repr = repr(m)
            m.return_value = m
            self.assertIs(m(), m)
            self.assertEqual(repr(m), original_repr)

            m.reset_mock()
            self.assertIs(m(), m)
            self.assertEqual(repr(m), original_repr)

            m = Klass()
            m.b = m.a
            self.assertIn("name='mock.a'", repr(m.b))
            self.assertIn("name='mock.a'", repr(m.a))
            m.reset_mock()
            self.assertIn("name='mock.a'", repr(m.b))
            self.assertIn("name='mock.a'", repr(m.a))

            m = Klass()
            original_repr = repr(m)
            m.a = m()
            m.a.return_value = m

            self.assertEqual(repr(m), original_repr)
            self.assertEqual(repr(m.a()), original_repr)


    def test_attach_mock(self):
        classes = Mock, MagicMock, NonCallableMagicMock, NonCallableMock
        for Klass in classes:
            for Klass2 in classes:
                m = Klass()

                m2 = Klass2(name='foo')
                m.attach_mock(m2, 'bar')

                self.assertIs(m.bar, m2)
                self.assertIn("name='mock.bar'", repr(m2))

                m.bar.baz(1)
                self.assertEqual(m.mock_calls, [call.bar.baz(1)])
                self.assertEqual(m.method_calls, [call.bar.baz(1)])


    def test_attach_mock_return_value(self):
        classes = Mock, MagicMock, NonCallableMagicMock, NonCallableMock
        for Klass in Mock, MagicMock:
            for Klass2 in classes:
                m = Klass()

                m2 = Klass2(name='foo')
                m.attach_mock(m2, 'return_value')

                self.assertIs(m(), m2)
                self.assertIn("name='mock()'", repr(m2))

                m2.foo()
                self.assertEqual(m.mock_calls, call().foo().call_list())


    def test_attach_mock_patch_autospec(self):
        parent = Mock()

        with mock.patch(f'{__name__}.something', autospec=True) as mock_func:
            self.assertEqual(mock_func.mock._extract_mock_name(), 'something')
            parent.attach_mock(mock_func, 'child')
            parent.child(1)
            something(2)
            mock_func(3)

            parent_calls = [call.child(1), call.child(2), call.child(3)]
            child_calls = [call(1), call(2), call(3)]
            self.assertEqual(parent.mock_calls, parent_calls)
            self.assertEqual(parent.child.mock_calls, child_calls)
            self.assertEqual(something.mock_calls, child_calls)
            self.assertEqual(mock_func.mock_calls, child_calls)
            self.assertIn('mock.child', repr(parent.child.mock))
            self.assertEqual(mock_func.mock._extract_mock_name(), 'mock.child')


    def test_attribute_deletion(self):
        for mock in (Mock(), MagicMock(), NonCallableMagicMock(),
                     NonCallableMock()):
            self.assertTrue(hasattr(mock, 'm'))

            del mock.m
            self.assertFalse(hasattr(mock, 'm'))

            del mock.f
            self.assertFalse(hasattr(mock, 'f'))
            self.assertRaises(AttributeError, getattr, mock, 'f')


    def test_mock_does_not_raise_on_repeated_attribute_deletion(self):
        # bpo-20239: Assigning and deleting twice an attribute raises.
        for mock in (Mock(), MagicMock(), NonCallableMagicMock(),
                     NonCallableMock()):
            mock.foo = 3
            self.assertTrue(hasattr(mock, 'foo'))
            self.assertEqual(mock.foo, 3)

            del mock.foo
            self.assertFalse(hasattr(mock, 'foo'))

            mock.foo = 4
            self.assertTrue(hasattr(mock, 'foo'))
            self.assertEqual(mock.foo, 4)

            del mock.foo
            self.assertFalse(hasattr(mock, 'foo'))


    def test_mock_raises_when_deleting_nonexistent_attribute(self):
        for mock in (Mock(), MagicMock(), NonCallableMagicMock(),
                     NonCallableMock()):
            del mock.foo
            with self.assertRaises(AttributeError):
                del mock.foo


    def test_reset_mock_does_not_raise_on_attr_deletion(self):
        # bpo-31177: reset_mock should not raise AttributeError when attributes
        # were deleted in a mock instance
        mock = Mock()
        mock.child = True
        del mock.child
        mock.reset_mock()
        self.assertFalse(hasattr(mock, 'child'))


    def test_class_assignable(self):
        for mock in Mock(), MagicMock():
            self.assertNotIsInstance(mock, int)

            mock.__class__ = int
            self.assertIsInstance(mock, int)
            mock.foo

    def test_name_attribute_of_call(self):
        # bpo-35357: _Call should not disclose any attributes whose names
        # may clash with popular ones (such as ".name")
        self.assertIsNotNone(call.name)
        self.assertEqual(type(call.name), _Call)
        self.assertEqual(type(call.name().name), _Call)

    def test_parent_attribute_of_call(self):
        # bpo-35357: _Call should not disclose any attributes whose names
        # may clash with popular ones (such as ".parent")
        self.assertIsNotNone(call.parent)
        self.assertEqual(type(call.parent), _Call)
        self.assertEqual(type(call.parent().parent), _Call)


    def test_parent_propagation_with_create_autospec(self):

        def foo(a, b): pass

        mock = Mock()
        mock.child = create_autospec(foo)
        mock.child(1, 2)

        self.assertRaises(TypeError, mock.child, 1)
        self.assertEqual(mock.mock_calls, [call.child(1, 2)])
        self.assertIn('mock.child', repr(mock.child.mock))

    def test_parent_propagation_with_autospec_attach_mock(self):

        def foo(a, b): pass

        parent = Mock()
        parent.attach_mock(create_autospec(foo, name='bar'), 'child')
        parent.child(1, 2)

        self.assertRaises(TypeError, parent.child, 1)
        self.assertEqual(parent.child.mock_calls, [call.child(1, 2)])
        self.assertIn('mock.child', repr(parent.child.mock))


    def test_isinstance_under_settrace(self):
        # bpo-36593 : __class__ is not set for a class that has __class__
        # property defined when it's used with sys.settrace(trace) set.
        # Delete the module to force reimport with tracing function set
        # restore the old reference later since there are other tests that are
        # dependent on unittest.mock.patch. In testpatch.PatchTest
        # test_patch_dict_test_prefix and test_patch_test_prefix not restoring
        # causes the objects patched to go out of sync

        old_patch = unittest.mock.patch

        # Directly using __setattr__ on unittest.mock causes current imported
        # reference to be updated. Use a lambda so that during cleanup the
        # re-imported new reference is updated.
        self.addCleanup(lambda patch: setattr(unittest.mock, 'patch', patch),
                        old_patch)

        with patch.dict('sys.modules'):
            del sys.modules['unittest.mock']

            # This trace will stop coverage being measured ;-)
            def trace(frame, event, arg):  # pragma: no cover
                return trace

            self.addCleanup(sys.settrace, sys.gettrace())
            sys.settrace(trace)

            from unittest.mock import (
                Mock, MagicMock, NonCallableMock, NonCallableMagicMock
            )

            mocks = [
                Mock, MagicMock, NonCallableMock, NonCallableMagicMock, AsyncMock
            ]

            for mock in mocks:
                obj = mock(spec=Something)
                self.assertIsInstance(obj, Something)


if __name__ == '__main__':
    unittest.main()
