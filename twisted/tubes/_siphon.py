# -*- test-case-name: twisted.tubes.test.test_tube.SeriesTest -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Adapters for converting L{ITube} to L{IDrain} and L{IFount}.
"""

import itertools

from zope.interface import implementer

from .itube import IPause, IDrain, IFount, ITube
from .kit import Pauser, beginFlowingFrom, beginFlowingTo
from ._components import _registryAdapting

from twisted.python.failure import Failure
from twisted.internet.defer import Deferred

from twisted.python import log

class _SiphonPiece(object):
    """
    Shared functionality between L{_SiphonFount} and L{_SiphonDrain}
    """
    def __init__(self, siphon):
        self._siphon = siphon


    @property
    def _tube(self):
        """
        Expose the siphon's C{_tube} directly since many things will want to
        manipulate it.

        @return: L{ITube}
        """
        return self._siphon._tube



@implementer(IFount)
class _SiphonFount(_SiphonPiece):
    """
    Implementation of L{IFount} for L{_Siphon}.

    @ivar fount: the implementation of the L{IDrain.fount} attribute.  The
        L{IFount} which is flowing to this L{_Siphon}'s L{IDrain}
        implementation.

    @ivar drain: the implementation of the L{IFount.drain} attribute.  The
        L{IDrain} to which this L{_Siphon}'s L{IFount} implementation is
        flowing.
    """
    drain = None

    def __init__(self, siphon):
        super(_SiphonFount, self).__init__(siphon)

        def _actuallyPause():
            fount = self._siphon._tdrain.fount
            self._siphon._currentlyPaused = True
            if fount is None:
                return
            if self._siphon._pauseBecausePauseCalled is None:
                self._siphon._pauseBecausePauseCalled = fount.pauseFlow()

        def _actuallyResume():
            self._siphon._currentlyPaused = False

            self._siphon._unbufferIterator()
            if self._siphon._currentlyPaused:
                return

            if self._siphon._pauseBecausePauseCalled:
                # TODO: validate that the siphon's fount is always set
                # consisetntly with _pauseBecausePauseCalled.
                fp = self._siphon._pauseBecausePauseCalled
                self._siphon._pauseBecausePauseCalled = None
                fp.unpause()

        self._pauser = Pauser(_actuallyPause, _actuallyResume)


    def __repr__(self):
        """
        Nice string representation.
        """
        return "<Fount for {0}>".format(repr(self._siphon._tube))


    @property
    def outputType(self):
        """
        Relay the C{outputType} declared by the tube.

        @return: see L{IFount.outputType}
        """
        return self._tube.outputType


    def flowTo(self, drain):
        """
        Flow data from this L{_Siphon} to the given drain.

        @param drain: see L{IFount.flowTo}

        @return: an L{IFount} that emits items of the output-type of this
            siphon's tube.
        """
        result = beginFlowingTo(self, drain)
        if self._siphon._pauseBecauseNoDrain:
            pbnd = self._siphon._pauseBecauseNoDrain
            self._siphon._pauseBecauseNoDrain = None
            pbnd.unpause()
        self._siphon._unbufferIterator()
        return result


    def pauseFlow(self):
        """
        Pause the flow from the fount, or remember to do that when the fount is
        attached, if it isn't yet.

        @return: L{IPause}
        """
        return self._pauser.pause()


    def stopFlow(self):
        """
        Stop the flow from the fount to this L{_Siphon}, and stop delivering
        buffered items.
        """
        self._siphon._flowWasStopped = True
        fount = self._siphon._tdrain.fount
        self._siphon._pendingIterator = None
        if fount is None:
            return
        fount.stopFlow()



@implementer(IPause)
class _PlaceholderPause(object):
    """
    L{IPause} provider that does nothing.
    """

    def unpause(self):
        """
        No-op.
        """



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
        """
        Relay the tube's declared inputType.

        @return: see L{IDrain.inputType}
        """
        return self._tube.inputType


    def flowingFrom(self, fount):
        """
        This siphon will now have 'receive' called on it by the given fount.

        @param fount: see L{IDrain.flowingFrom}

        @return: see L{IDrain.flowingFrom}
        """
        beginFlowingFrom(self, fount)
        if self._siphon._pauseBecausePauseCalled:
            pbpc = self._siphon._pauseBecausePauseCalled
            self._siphon._pauseBecausePauseCalled = None
            if fount is None:
                pauseFlow = _PlaceholderPause
            else:
                pauseFlow = fount.pauseFlow
            self._siphon._pauseBecausePauseCalled = pauseFlow()
            pbpc.unpause()
        if fount is not None:
            if self._siphon._flowWasStopped:
                fount.stopFlow()
            # Is this the right place, or does this need to come after
            # _pauseBecausePauseCalled's check?
            if not self._siphon._everStarted:
                self._siphon._everStarted = True
                self._siphon._deliverFrom(self._tube.started)
        nextFount = self._siphon._tfount
        nextDrain = nextFount.drain
        if nextDrain is None:
            return nextFount
        return nextFount.flowTo(nextDrain)


    def receive(self, item):
        """
        An item was received.  Pass it on to the tube for processing.

        @param item: an item to deliver to the tube.
        """
        def tubeReceivedItem():
            return self._tube.received(item)
        self._siphon._deliverFrom(tubeReceivedItem)


    def flowStopped(self, reason):
        """
        This siphon has now stopped.

        @param reason: the reason why our fount stopped the flow.
        """
        self._siphon._flowStoppingReason = reason
        def tubeStopped():
            return self._tube.stopped(reason)
        self._siphon._deliverFrom(tubeStopped)



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

    @ivar _everStarted: Has this L{_Siphon} ever called C{started} on its
        L{Tube}?
    @type _everStarted: L{bool}
    """

    _currentlyPaused = False
    _pauseBecausePauseCalled = None
    _tube = None
    _pendingIterator = None
    _flowWasStopped = False
    _everStarted = False
    _unbuffering = False
    _flowStoppingReason = None
    _pauseBecauseNoDrain = None

    def __init__(self, tube):
        """
        Initialize this L{_Siphon} with the given L{Tube} to control its
        behavior.
        """
        self._tfount = _SiphonFount(self)
        self._tdrain = _SiphonDrain(self)
        self._tube = tube


    def __repr__(self):
        """
        Nice string representation.
        """
        return '<_Siphon for {0}>'.format(repr(self._tube))


    def _deliverFrom(self, deliverySource):
        """
        Deliver some items from a callable that will produce an iterator.

        @param deliverySource: a 0-argument callable that will return an
            iterable.
        """
        assert self._pendingIterator is None, \
            repr(list(self._pendingIterator)) + " " + \
            repr(deliverySource) + " " + \
            repr(self._pauseBecauseNoDrain)
        try:
            iterableOrNot = deliverySource()
        except:
            f = Failure()
            log.err(f, "Exception raised when delivering from {0!r}"
                    .format(deliverySource))
            self._tdrain.fount.stopFlow()
            downstream = self._tfount.drain
            if downstream is not None:
                downstream.flowStopped(f)
            return
        if iterableOrNot is None:
            return
        self._pendingIterator = iter(iterableOrNot)
        if self._tfount.drain is None:
            if self._pauseBecauseNoDrain is None:
                self._pauseBecauseNoDrain = self._tfount.pauseFlow()

        self._unbufferIterator()


    def _unbufferIterator(self):
        """
        Un-buffer some items buffered in C{self._pendingIterator} and actually
        deliver them, as long as we're not paused.
        """
        if self._unbuffering:
            return
        if self._pendingIterator is None:
            return
        whatever = object()
        self._unbuffering = True
        def whenUnclogged(result, somePause):
            pending = self._pendingIterator
            self._pendingIterator = itertools.chain(iter([result]), pending)
            somePause.unpause()
        while not self._currentlyPaused:
            if self._pendingIterator is not None:
                value = next(self._pendingIterator, whatever)
            else:
                value = whatever
            if value is whatever:
                self._pendingIterator = None
                if self._flowStoppingReason is not None:
                    self._tfount.drain.flowStopped(self._flowStoppingReason)
                break
            if isinstance(value, Deferred):
                anPause = self._tfount.pauseFlow()
                (value.addCallback(whenUnclogged, somePause=anPause)
                 .addErrback(log.err, "WHAT"))
            else:
                self._tfount.drain.receive(value)
        self._unbuffering = False



def _tube2drain(tube):
    """
    An adapter that can convert an L{ITube} to an L{IDrain} by wrapping it in a
    L{_Siphon}.

    @param tube: L{ITube}

    @return: L{IDrain}
    """
    return _Siphon(tube)._tdrain



_tubeRegistry = _registryAdapting(
    (ITube, IDrain, _tube2drain),
)



