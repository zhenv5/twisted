# -*- test-case-name: twisted.tubes.test.test_memory -*-

from zope.interface import implementer

from twisted.python.failure import Failure

from .itube import IFount, StopFlowCalled
from .pauser import Pauser

@implementer(IFount)
class IteratorFount(object):
    """
    An L{IteratorFount} delivers values from a python iterable.
    """

    drain = None

    def __init__(self, iterable, inputType=None, outputType=None):
        self._iterator = iter(iterable)
        self._paused = False
        self._stopped = False
        self._pauser = Pauser(self._actuallyPause,
                              self._actuallyResume)

        self.inputType = inputType
        self.outputType = outputType


    def _actuallyPause(self):
        """
        Set the paused state of this L{IteratorFount} to True.
        """
        self._paused = True


    def _actuallyResume(self):
        """
        Set the paused state of this L{IteratorFount} to True.
        """
        if not self._stopped:
            self._paused = False
            self._deliver()


    def _deliver(self):
        if not self._paused:
            for value in self._iterator:
                self.drain.receive(value)
                if self._paused:
                    break
            else:
                self._stopped = True
                self.drain.flowStopped(Failure(StopIteration()))


    def flowTo(self, drain):
        # TODO: oldDrain? flowingFrom(None)?
        self.drain = drain
        result = drain.flowingFrom(self)
        self._deliver()
        return result


    def pauseFlow(self):
        return self._pauser.pause()


    def stopFlow(self):
        if not self._stopped:
            self._stopped = True
            self._actuallyPause()
            self.drain.flowStopped(Failure(StopFlowCalled()))
