# -*- test-case-name: twisted.tubes.test.test_memory -*-

from zope.interface import implementer

from .itube import IFount

@implementer(IFount)
class IteratorFount(object):
    """
    An L{IteratorFount} delivers values from a python iterable.
    """

    def __init__(self, iterable):
        self._iterator = iter(iterable)


    def flowTo(self, drain):
        self.drain = drain
        result = drain.flowingFrom(self)
        for value in self._iterator:
            drain.receive(value)
        return result
