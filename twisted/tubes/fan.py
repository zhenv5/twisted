# -*- test-case-name: twisted.tubes.test.test_fan -*-
from zope.interface import implementer

from .pauser import Pauser
from .itube import IDrain, IFount, IPause
from twisted.python.components import proxyForInterface


@implementer(IDrain)
class _InDrain(object):
    """
    
    """

    inputType = None

    fount = None

    def __init__(self, fanIn):
        """
        
        """
        self._in = fanIn
        self._pauseBecausePauseCalled = None
        self._pauseBecauseNoDrain = None


    def flowingFrom(self, fount):
        """
        
        """
        if self._pauseBecauseNoDrain is not None:
            self._pauseBecauseNoDrain.unpause()
            self._pauseBecauseNoDrain = None
        self.fount = fount


    def receive(self, item):
        """
        
        """
        drain = self._in.fount.drain
        if drain is not None:
            return drain.receive(item)
        else:
            self._pauseBecauseNoDrain = self.fount.pauseFlow()
            return 1.0


    def flowStopped(self, reason):
        """
        
        """
        return self._in.fount.drain.flowStopped(reason)



@implementer(IFount)
class _InFount(object):
    """
    
    """

    outputType = None

    drain = None

    def __init__(self, fanIn):
        """
        
        """
        self._in = fanIn


    def flowTo(self, drain):
        """
        
        """
        self.drain = drain
        return drain.flowingFrom(self)


    def pauseFlow(self):
        """
        
        """
        subPauses = []
        for drain in self._in._drains:
            # XXX wrong because drains could be added and removed
            subPauses.append(drain.fount.pauseFlow())
        return _AggregatePause(subPauses)



@implementer(IPause)
class _AggregatePause(object):
    """
    
    """

    def __init__(self, subPauses):
        """
        
        """
        self._subPauses = subPauses


    def unpause(self):
        """
        
        """
        for subPause in self._subPauses:
            subPause.unpause()



class In(object):
    """
    
    """
    def __init__(self):
        """
        
        """
        self._fount = _InFount(self)
        self._drains = []
        self._subdrain = None


    @property
    def fount(self):
        """
        
        """
        return self._fount


    def newDrain(self):
        """
        
        """
        it = _InDrain(self)
        self._drains.append(it)
        return it



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
        nextFount = drain.flowingFrom(self)
        return nextFount


    def pauseFlow(self):
        """
        
        """
        return self._pauser.pause()


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
        self._paused = None
        self._pauser = Pauser(self._actuallyPause,
                              self._actuallyResume)


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
        if self._paused is not None:
            raise NotImplementedError()
        self._paused = self.fount.pauseFlow()


    def _actuallyResume(self):
        """
        
        """
        self._paused.unpause()
        self._paused = None


    def flowStopped(self, reason):
        """
        
        """
        for fount in self._founts[:]:
            if fount.drain is not None:
                fount.drain.flowStopped(reason)




class Out(object):
    """
    
    """
    def __init__(self):
        """
        
        """
        self._founts = []
        self._drain = _OutDrain(self._founts)


    @property
    def drain(self):
        """
        
        """
        return self._drain


    def newFount(self):
        """
        
        """
        f = _OutFount(self._drain._pauser, self._founts.remove)
        self._founts.append(f)
        return f



class Thru(proxyForInterface(IDrain, "_outDrain")):
    """
    
    """

    def __init__(self, drains):
        """
        
        """
        self._drains = drains
        self._in = In()
        self._out = Out()
        self._outDrain = self._out.drain


    def flowingFrom(self, fount):
        """
        
        """
        super(Thru, self).flowingFrom(fount)
        for drain in self._drains:
            newFount = self._out.newFount()
            nextFount = newFount.flowTo(drain)
            if nextFount is not None:
                nextFount.flowTo(self._in.newDrain())
        return self._in.fount
