# -*- test-case-name: twisted.tubes.test.test_fan -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tools for turning L{founts <twisted.tubes.itube.IFount>} and L{drains
<twisted.tubes.itube.IDrain>} into multiple founts and drains.
"""

from itertools import count

from zope.interface import implementer

from twisted.python.components import proxyForInterface

from .pauser import Pauser
from .itube import IDrain, IFount, IPause
from .begin import beginFlowingTo, beginFlowingFrom


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
        beginFlowingFrom(self, fount)
        # Except the fount is having similar thoughts about us as a drain, and
        # this can only happen in one order or the other. right now siphon
        # takes care of it.
        self._checkNoDrainPause()
        return None


    def _checkNoDrainPause(self):
        """
        
        """
        pbnd = self._pauseBecauseNoDrain
        self._pauseBecauseNoDrain = None
        # Do this _before_ unpausing the old one; if it's a new fount, the
        # order doesn't matter, but if it's the old fount, then doing it in
        # this order ensures it never actually unpauses, we just hand off one
        # pause for the other.
        if self.fount is not None and self._in.fount.drain is None:
            self._pauseBecauseNoDrain = self.fount.pauseFlow()
        if pbnd is not None:
            pbnd.unpause()


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
        result = beginFlowingTo(self, drain)
        for drain in self._in._drains:
            drain._checkNoDrainPause()
        return result


    def pauseFlow(self):
        """
        
        """
        subPauses = []
        for drain in self._in._drains:
            # XXX wrong because drains could be added and removed
            subPauses.append(drain.fount.pauseFlow())
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
        for subPause in self._subPauses:
            subPause.unpause()



class In(object):
    r"""
    A fan.L{In} presents a single L{fount <twisted.tubes.itube.IFount>} that
    delivers the inputs from multiple L{drains <twisted.tubes.itube.IDrain>}::

        your fount ---> In.newDrain()--\
                                        \
        your fount ---> In.newDrain()----> In ---> In.fount ---> your drain
                                        /
        your fount ---> In.newDrain()--/

    @ivar fount: The fount which produces all new attributes.
    @type fount: L{twisted.tubes.itube.IFount}
    """
    def __init__(self):
        self.fount = _InFount(self)
        self._drains = []
        self._subdrain = None


    def newDrain(self):
        """
        Create a new L{drains <twisted.tubes.itube.IDrain>} which will send its
        inputs out via C{self.fount}.

        @return: a drain.
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
        return beginFlowingTo(self, drain)


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

    def __init__(self, founts, inputType, outputType):
        """
        
        """
        self._pause = None
        self._paused = False

        self._founts = founts

        def _actuallyPause():
            if self._paused:
                raise NotImplementedError()
            self._paused = True
            if self.fount is not None:
                self._pause = self.fount.pauseFlow()

        def _actuallyResume():
            p = self._pause
            self._pause = None
            self._paused = False
            if p is not None:
                p.unpause()

        self._pauser = Pauser(self._actuallyPause, self._actuallyResume)

        self.inputType = inputType
        self.outputType = outputType


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


    def flowStopped(self, reason):
        """
        
        """
        for fount in self._founts[:]:
            if fount.drain is not None:
                fount.drain.flowStopped(reason)



class Out(object):
    r"""
    A fan.L{Out} presents a single L{drain <twisted.tubes.itube.IDrain>} that
    delivers the inputs to multiple L{founts <twisted.tubes.itube.IFount>}::

                                           /--> Out.newFount() --> your drain
                                          /
        your fount --> Out.drain --> Out <----> Out.newFount() --> your drain
                                          \
                                           \--> Out.newFount() --> your drain

    @ivar drain: The fount which produces all new attributes.
    @type drain: L{twisted.tubes.itube.IDrain}
    """

    def __init__(self, inputType=None, outputType=None):
        """
        
        """
        self._founts = []
        self.drain = _OutDrain(self._founts, inputType=inputType,
                               outputType=outputType)


    def newFount(self):
        """
        
        """
        f = _OutFount(self._drain._pauser, self._founts.remove)
        self._founts.append(f)
        return f



class Thru(proxyForInterface(IDrain, "_outDrain")):
    r"""
    A fan.L{Thru} takes an input and fans it I{thru} multiple
    drains-which-produce-founts, such as L{tubes <twisted.tube.itube.ITube>}::

                Your Fount
             (producing "foo")
                    |
                    v
                  Thru
                    |
                  _/|\_
                _/  |  \_
               /    |    \
        foo2bar  foo2baz  foo2qux
               \_   |   _/
                 \_ | _/
                   \|/
                    |
                    v
                  Thru
                    |
                    v
                Your Drain
         (receiving a combination
             of foo, bar, baz)

    The way you would construct such a flow would be:
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
        for idx, appDrain, outFount, inDrain in zip(
                count(), self._drains, self._outFounts, self._inDrains):
            appFount = outFount.flowTo(appDrain)
            if appFount is None:
                appFount = self._founts[idx]
            else:
                self._founts[idx] = appFount
            appFount.flowTo(inDrain)
        nextFount = self._in.fount

        # Literally copy/pasted from _SiphonDrain.flowingFrom.  Hmm.
        nextDrain = nextFount.drain
        if nextDrain is None:
            return nextFount
        return nextFount.flowTo(nextDrain)

