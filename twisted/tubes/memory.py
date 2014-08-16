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
                              self._actuallyResume)


    def _actuallyPause(self):
        """
        Set the paused state of this L{IteratorFount} to True.
        """
        self._paused = True


    def _actuallyResume(self):
        """
        Set the paused state of this L{IteratorFount} to True.
        """
        self._paused = False
        self._deliver()


    def _deliver(self):
        if not self._paused:
            for value in self._iterator:
                self.drain.receive(value)
                if self._paused:
                    break


    def flowTo(self, drain):
        self.drain = drain
        result = drain.flowingFrom(self)
        self._deliver()
        return result


    def pauseFlow(self):
        return self._pauser.pause()
