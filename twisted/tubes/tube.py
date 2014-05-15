# -*- test-case-name: twisted.tubes.test.test_tube -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
See L{_Siphon}.
"""
import itertools

from zope.interface import implementer, implementedBy

from twisted.internet.defer import Deferred

from twisted.python import log
from twisted.python.failure import Failure

from twisted.tubes.itube import (IDrain, ITube, IFount, IPause, IDivertable,
                                 AlreadyUnpaused)


class _SiphonPiece(object):
    """
    Shared functionality between L{_SiphonFount} and L{_SiphonDrain}
    """
    def __init__(self, siphon):
        self._siphon = siphon


    @property
    def _tube(self):
        return self._siphon._tube



@implementer(IPause)
class _Pause(object):
    def __init__(self, pauser):
        self.pauser = pauser
        self.alive = True


    def unpause(self):
        if self.alive:
            self.pauser.pauses -= 1
            if self.pauser.pauses == 0:
                self.pauser.actuallyResume()
            self.alive = False
        else:
            raise AlreadyUnpaused()



class _Pauser(object):

    def __init__(self, actuallyPause, actuallyResume):
        self.actuallyPause = actuallyPause
        self.actuallyResume = actuallyResume
        self.pauses = 0


    def pauseFlow(self):
        """
        @see: L{IFount.pauseFlow}
        """
        if not self.pauses:
            self.actuallyPause()
        self.pauses += 1
        return _Pause(self)



@implementer(IFount)
class _SiphonFount(_SiphonPiece):
    """
    Implementation of L{IFount} for L{_Siphon}.

    @ivar fount: the implementation of the L{IDrain.fount} attribute.  The
        L{IFount} which is flowing to this L{_Siphon}'s L{IDrain} implementation.

    @ivar drain: the implementation of the L{IFount.drain} attribute.  The
        L{IDrain} to which this L{_Siphon}'s L{IFount} implementation is flowing.
    """
    drain = None

    def __init__(self, siphon):
        super(_SiphonFount, self).__init__(siphon)
        self._pauser = _Pauser(self._actuallyPause, self._actuallyResume)


    def __repr__(self):
        """
        Nice string representation.
        """
        return "<Fount for {0}>".format(repr(self._siphon._tube))


    @property
    def outputType(self):
        return self._tube.outputType


    def flowTo(self, drain):
        """
        Flow data from this siphon to the given drain.
        """
        self.drain = drain
        if drain is None:
            return
        result = self.drain.flowingFrom(self)
        if self._siphon._pauseBecauseNoDrain:
            pbnd = self._siphon._pauseBecauseNoDrain
            self._siphon._pauseBecauseNoDrain = None
            pbnd.unpause()
        return result


    def pauseFlow(self):
        """
        Pause the flow from the fount, or remember to do that when the
        fount is attached, if it isn't yet.
        """
        return self._pauser.pauseFlow()


    def _actuallyPause(self):
        fount = self._siphon._tdrain.fount
        self._siphon._currentlyPaused = True
        if fount is not None and self._siphon._pauseBecausePauseCalled is None:
            self._siphon._pauseBecausePauseCalled = fount.pauseFlow()


    def _actuallyResume(self):
        """
        Resume the flow from the fount to this L{_Siphon}.
        """
        fount = self._siphon._tdrain.fount
        self._siphon._currentlyPaused = False

        if self._siphon._pendingIterator is not None:
            self._siphon._unbufferIterator()

        if fount is not None and self._siphon._pauseBecausePauseCalled:
            fp = self._siphon._pauseBecausePauseCalled
            self._siphon._pauseBecausePauseCalled = None
            fp.unpause()


    def stopFlow(self):
        """
        Stop the flow from the fount to this L{_Siphon}.
        """
        self._siphon._flowWasStopped = True
        fount = self._siphon._tdrain.fount
        if fount is None:
            return
        fount.stopFlow()



@implementer(IDrain)
class _SiphonDrain(_SiphonPiece):
    """
    Implementation of L{IDrain} for L{_Siphon}.
    """
    fount = None

    def __repr__(self):
        """
        Nice string representation.
        """
        return '<Drain for {0}>'.format(self._siphon._tube)


    @property
    def inputType(self):
        return self._tube.inputType


    def flowingFrom(self, fount):
        """
        This siphon will now have 'receive' called.
        """
        out = fount.outputType
        in_ = self.inputType
        if out is not None and in_ is not None and not in_.isOrExtends(out):
            raise TypeError()
        self.fount = fount
        if self._siphon._flowWasStopped:
            fount.stopFlow()
        if self._siphon._pauseBecausePauseCalled:
            pbpc = self._siphon._pauseBecausePauseCalled
            self._siphon._pauseBecausePauseCalled = None
            pbpc.unpause()
            self._siphon._pauseBecausePauseCalled = fount.pauseFlow()
        self._siphon._deliverFrom(self._tube.started)
        nextFount = self._siphon._tfount
        nextDrain = nextFount.drain
        if nextDrain is None:
            return nextFount
        return nextFount.flowTo(nextDrain)


    def progress(self, amount=None):
        """
        Progress was made.
        """
        self._tube.progressed(amount)


    def receive(self, item):
        """
        An item was received.  Pass it on to the tube for processing.
        """
        def thingToDeliverFrom():
            return self._tube.received(item)
        delivered = self._siphon._deliverFrom(thingToDeliverFrom)
        drain = self._siphon._tfount.drain
        if drain is not None and delivered == 0:
            drain.progress()


    def flowStopped(self, reason):
        """
        This siphon has now stopped.
        """
        self._siphon._flowStoppingReason = reason
        self._siphon._deliverFrom(lambda: self._tube.stopped(reason))



def series(start, *tubes):
    """
    Connect up a series of objects capable of transforming inputs to outputs;
    convert a sequence of L{ITube} objects into a sequence of connected
    L{IFount} and L{IDrain} objects.  This is necessary to be able to C{flowTo}
    an object implementing L{ITube}.

    This function can best be understood by understanding that::

        x = a
        a.flowTo(b).flowTo(c)

    is roughly analagous to::

        x = series(a, b, c)

    with the additional feature that C{series} will convert C{a}, C{b}, and
    C{c} to the requisite L{IDrain} objects first.

    @param start: The initial element in the chain; the object that will
        consume inputs passed to the result of this call to C{series}.
    @type start: an L{ITube}, or anything adaptable to L{IFount}, as well as
        L{IDrain}.

    @param tubes: Each element of C{plumbing}.
    @type tubes: a L{tuple} of L{ITube}s or objects adaptable to L{IDrain}.

    @return: An L{IDrain} that can consume inputs of C{start}'s C{inputType},
        and whose C{flowingFrom} will return an L{IFount} that will produce
        outputs of C{plumbing[-1]} (or C{start}, if plumbing is empty).
    @rtype: L{IDrain}

    @raise TypeError: if C{start}, or any element of C{plumbing} is not
        adaptable to L{IDrain}.
    """
    with _registryActive(_tubeRegistry):
        result = IDrain(start)
        currentFount = IFount(result)
        drains = map(IDrain, tubes)
    for drain in drains:
        currentFount = currentFount.flowTo(drain)
    return result



from zope.interface.adapter import AdapterRegistry
from twisted.python.components import _addHook, _removeHook
from contextlib import contextmanager

@contextmanager
def _registryActive(registry):
    """
    A context manager that activates and deactivates a zope adapter registry
    for the duration of the call.

    For example, if you wanted to have a function that could adapt L{IFoo} to
    L{IBar}, but doesn't expose that adapter outside of itself::

        def convertToBar(maybeFoo):
            with _registryActive(_registryAdapting((IFoo, IBar, fooToBar))):
                return IBar(maybeFoo)

    @note: This isn't thread safe, so other threads will be affected as well.

    @param registry: The registry to activate.
    @type registry: L{AdapterRegistry}

    @rtype:
    """
    hook = _addHook(registry)
    yield
    _removeHook(hook)



class _Siphon(object):
    """
    A L{_Siphon} is an L{IDrain} and possibly also an L{IFount}, and provides
    lots of conveniences to make it easy to implement something that does fancy
    flow control with just a few methods.

    @ivar _tube: the L{Tube} which will receive values from this siphon and
        call C{deliver} to deliver output to it.  (When set, this will
        automatically set the C{siphon} attribute of said L{Tube} as well, as
        well as un-setting the C{siphon} attribute of the old tube.)

    @ivar _currentlyPaused: is this L{_Siphon} currently paused?  Boolean:
        C{True} if paused, C{False} if not.

    @ivar _pauseBecausePauseCalled: an L{IPause} from the upstream fount,
        present because pauseFlow has been called.

    @ivar _flowStoppingReason: If this is not C{None}, then call C{flowStopped}
        on the downstream L{IDrain} at the next opportunity, where "the next
        opportunity" is when the last L{Deferred} yielded from L{ITube.stopped}
        has fired.
    """

    _currentlyPaused = False
    _pauseBecausePauseCalled = None
    _tube = None
    _pendingIterator = None
    _flowWasStopped = False

    def __init__(self, tube):
        """
        Initialize this L{_Siphon} with the given L{Tube} to control its
        behavior.
        """
        self._tfount = _SiphonFount(self)
        self._tdrain = _SiphonDrain(self)
        assert not getattr(tube, "__marked__", False)
        tube.__marked__ = True
        self._tube = tube
        if IDivertable.providedBy(tube):
            tube.divert = self._divert


    def __repr__(self):
        """
        Nice string representation.
        """
        return '<_Siphon for {0}>'.format(repr(self._tube))


    _pauseBecauseNoDrain = None

    def _deliverFrom(self, deliverySource):
        assert self._pendingIterator is None
        try:
            iterableOrNot = deliverySource()
        except:
            f = Failure()
            log.err(f, "Exception raised when delivering from {0!r}".format(deliverySource))
            self._tdrain.fount.stopFlow()
            downstream = self._tfount.drain
            if downstream is not None:
                downstream.flowStopped(f)
            return
            
        if iterableOrNot is None:
            return 0
        self._pendingIterator = iter(iterableOrNot)
        if self._tfount.drain is None:
            self._pauseBecauseNoDrain = self._tfount.pauseFlow()

        return self._unbufferIterator()

    _unbuffering = False
    _flowStoppingReason = None

    def _unbufferIterator(self):
        if self._unbuffering:
            return
        whatever = object()
        i = 0
        self._unbuffering = True
        while not self._currentlyPaused:
            value = next(self._pendingIterator, whatever)
            if value is whatever:
                self._pendingIterator = None
                if self._flowStoppingReason is not None:
                    self._tfount.drain.flowStopped(self._flowStoppingReason)
                break
            if isinstance(value, Deferred):
                anPause = self._tfount.pauseFlow()

                def whenUnclogged(result):
                    pending = self._pendingIterator
                    self._pendingIterator = itertools.chain(iter([result]),
                                                            pending)
                    anPause.unpause()

                from twisted.python import log
                value.addCallback(whenUnclogged).addErrback(log.err, "WHAT")
            else:
                self._tfount.drain.receive(value)
            i += 1
        self._unbuffering = False
        return i


    def _divert(self, drain):
        """
        Divert the flow to the 
        """
        upstream = self._tdrain.fount
        anPause = upstream.pauseFlow()
        upstream.flowTo(drain)
        anPause.unpause()
        if self._pendingIterator is not None:
            for element in self._tube.reassemble(self._pendingIterator):
                drain.receive(element)


def _registryAdapting(*fromToAdapterTuples):
    """
    Construct a Zope Interface adapter registry.

    For example, if you want to construct an adapter registry that can convert
    C{IFoo} to C{IBar} with C{fooToBar}.

    @param fromToAdapterTuples: A sequence of tuples of C{(fromInterface,
        toInterface, adapterCallable)}, where C{fromInterface} and
        C{toInterface} are L{Interface}s, and C{adapterCallable} is a callable
        that takes one argument which provides C{fromInterface} and returns an
        object providing C{toInterface}.
    @type fromToAdapterTuples: C{tuple} of 3-C{tuple}s of C{(Interface,
        Interface, callable)}

    @rtype: L{AdapterRegistry}
    """
    result = AdapterRegistry()
    for From, to, adapter in fromToAdapterTuples:
        result.register([From], to, '', adapter)
    return result



def _tube2drain(tube):
    return _Siphon(tube)._tdrain



def _siphonDrain2Fount(siphonDrain):
    return siphonDrain._siphon._tfount



_tubeRegistry = _registryAdapting(
    (ITube, IDrain, _tube2drain),
    (implementedBy(_SiphonDrain), IFount, _siphonDrain2Fount),
)



@implementer(ITube)
class Tube(object):
    """
    Null implementation for L{ITube}.  You can inherit from this to get no-op
    implementation of all of L{ITube}'s required implementation so you can just
    just implement the parts you're interested in.

    @ivar inputType: The type of data expected to be received by C{receive}.

    @ivar outputType: The type of data expected to be emitted by C{receive}.
    """

    inputType = None
    outputType = None

    def started(self):
        """
        @see: L{ITube.started}
        """


    def received(self, item):
        """
        @see: L{ITube.received}
        """


    def progressed(self, amount=None):
        """
        @see: L{ITube.progressed}
        """


    def stopped(self, reason):
        """
        @see: L{ITube.stopped}
        """
