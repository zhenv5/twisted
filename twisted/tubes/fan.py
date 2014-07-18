# -*- test-case-name: twisted.tubes.test.test_fan -*-
from zope.interface import implementer

from twisted.tubes.tube import _Pauser
from twisted.tubes.itube import IDrain, IFount


class _InDrain(object):
    """

    """



class _InFount(object):
    """

    """



class In(object):
    """

    """

    @property
    def fount(self):
        """

        """


    def newDrain(self):
        """

        """


@implementer(IFount)
class _OutFount(object):
    """

    """
    drain = None

    outputType = None

    def __init__(self, pauser, stopper):
        """
        
        """
        self._pauser = pauser
        self._stopper = stopper


    def flowTo(self, drain):
        """
        
        """
        self.drain = drain
        return drain.flowingFrom(self)


    def pauseFlow(self):
        """
        
        """
        return self._pauser.pauseFlow()


    def stopFlow(self):
        """
        
        """
        self._stopper(self)



@implementer(IDrain)
class _OutDrain(object):
    """

    """
    fount = None
    inputType = None

    def __init__(self, founts):
        """
        
        """
        self._founts = founts


    def flowingFrom(self, fount):
        """
        
        """
        self.fount = fount


    def receive(self, item):
        """
        
        """
        for fount in self._founts[:]:
            if fount.drain is not None:
                fount.drain.receive(item)


    def _actuallyPause(self):
        """
        
        """
        self._paused = self.fount.pauseFlow()


    def _actuallyResume(self):
        """
        
        """
        self._paused.unpause()


    def flowStopped(self, reason):
        """
        
        """
        



class Out(object):
    """

    """
    def __init__(self):
        """

        """
        self._founts = []
        self._drain = _OutDrain(self._founts)
        self._pauser = _Pauser(self._drain._actuallyPause,
                               self._drain._actuallyResume)
        
    @property
    def drain(self):
        """

        """
        return self._drain


    def newFount(self):
        """

        """
        f = _OutFount(self._pauser, self._founts.remove)
        self._founts.append(f)
        return f
