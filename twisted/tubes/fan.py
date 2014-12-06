# -*- test-case-name: twisted.tubes.test.test_fan -*-
from itertools import count

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
        self._pauseBecauseNoDrain = None


    def flowingFrom(self, fount):
        """
        
        """
        # if our previous fount is paused because *we* didn't have a drain, we
        # need to unpause it so it can be happy with a potential new drain.
        # but we can't do that because our previous fount is still pointed at
        # us.  so we need to be sure our previous fount is pointed away from us
        # now.  except the previous fount... might also be *this* fount.

        # if fount is not self.fount and self.fount is not None:
        #     self.fount.flowTo(None)

        # except the fount is having similar thoughts about us as a drain, and
        # this can only happen in one order or the other. right now siphon
        # takes care of it.
        pbnd = self._pauseBecauseNoDrain
        self._pauseBecauseNoDrain = None
        # do this _before_ unpausing the old one; if it's a new fount, the
        # order doesn't matter, but if it's the old fount, then doing it in
        # this order ensures it never actually unpauses, we just hand off one
        # pause for the other.
        if fount is not None and self._in.fount.drain is None:
            self._pauseBecauseNoDrain = fount.pauseFlow()
            print("FAN:PBND", self._pauseBecauseNoDrain)
        if pbnd is not None:
            print("FAN:UN_PAUSE", pbnd)
            pbnd.unpause()
        self.fount = fount


    def receive(self, item):
        """
        
        """
        return self._in.fount.drain.receive(item)


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
        print("aggregate pause", subPauses)
        return _AggregatePause(subPauses)


    def stopFlow(self):
        """
        
        """
        for drain in self._in._drains:
            drain.fount.stopFlow()



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
        print("aggregate unpause")
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
        self._pause = None
        self._paused = False
        self._pauser = Pauser(self._actuallyPause,
                              self._actuallyResume)


    def flowingFrom(self, fount):
        """
        
        """
        if self._paused:
            p = self._pause
            if fount is not None:
                self._pause = fount.pauseFlow()
            else:
                self._pause = None
            if p is not None:
                p.unpause()
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
        print("actually pausing fanout")
        if self._paused:
            raise NotImplementedError()
        self._paused = True
        if self.fount is not None:
            self._pause = self.fount.pauseFlow()


    def _actuallyResume(self):
        """
        
        """
        print("actually resuming fanout")
        p = self._pause
        self._pause = None
        self._paused = False
        if p is not None:
            p.unpause()


    def flowStopped(self, reason):
        """
        
        """
        print("fanout flow stopped", reason)
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
        self._in = In()
        self._out = Out()

        self._drains = list(drains)
        self._founts = list(None for drain in self._drains)
        self._outFounts = list(self._out.newFount() for drain in self._drains)
        self._inDrains = list(self._in.newDrain() for drain in self._drains)
        self._outDrain = self._out.drain


    def flowingFrom(self, fount):
        """
        
        """
        super(Thru, self).flowingFrom(fount)
        print("Thru flowingFrom", fount)
        for idx, appDrain, outFount, inDrain in zip(
                count(), self._drains, self._outFounts, self._inDrains):
            appFount = outFount.flowTo(appDrain)
            if appFount is None:
                appFount = self._founts[idx]
            else:
                self._founts[idx] = appFount
            appFount.flowTo(inDrain)
            # print("reflow:", outFount, appDrain, appFount, inDrain)
        return self._in.fount
