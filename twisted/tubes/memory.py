# -*- test-case-name: twisted.tubes.test.test_memory -*-

from zope.interface import implementer

from .itube import IFount
from .pauser import Pauser

@implementer(IFount)
class IteratorFount(object):
    """
    An L{IteratorFount} delivers values from a python iterable.
    """

    def __init__(self, iterable):
        self._iterator = iter(iterable)
        self._paused = False
        self._pauser = Pauser(self._actuallyPause,
                              lambda: None)

    def _actuallyPause(self):
        """
        Set the paused state of this L{IteratorFount} to True.
        """
        self._paused = True


    def flowTo(self, drain):
        self.drain = drain
        result = drain.flowingFrom(self)
        for value in self._iterator:
            drain.receive(value)
            if self._paused:
                break
        return result


    def pauseFlow(self):
        return self._pauser.pause()
