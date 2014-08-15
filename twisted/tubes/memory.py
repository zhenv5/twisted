# -*- test-case-name: twisted.tubes.test.test_memory -*-

from zope.interface import implementer

from .itube import IFount

@implementer(IFount)
class IteratorFount(object):
    """
    An L{IteratorFount} delivers values from a python iterable.
    """

    def __init__(self, iterable):
        pass


    def flowTo(self, drain):
        self.drain = drain
        return drain.flowingFrom(self)
