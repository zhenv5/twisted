# -*- test-case-name: twisted.tubes.test -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Utilities for testing L{twisted.tubes}.
"""

from zope.interface import Interface, implements, implementer
from zope.interface.verify import verifyClass

from twisted.test.proto_helpers import StringTransport
from twisted.internet.defer import succeed
from twisted.internet.interfaces import IStreamClientEndpoint

from ..itube import IDrain, IFount, IDivertable
from ..tube import tube
from ..pauser import Pauser


@implementer(IStreamClientEndpoint)
class StringEndpoint(object):
    """
    A client endpoint which connects to a L{StringTransport}.
    """
    def __init__(self):
        """
        Initialize the list of connected transports.
        """
        self.transports = []


    def connect(self, factory):
        """
        Connect the given L{IProtocolFactory} to a L{StringTransport} and
        return a fired L{Deferred}.

        @param factory: see L{IStreamClientEndpoint}

        @return: see L{IStreamClientEndpoint}
        """
        protocol = factory.buildProtocol(None)
        transport = StringTransport()
        transport.protocol = protocol
        protocol.makeConnection(transport)
        self.transports.append(transport)
        return succeed(protocol)



class IFakeOutput(Interface):
    """
    A sample interface to be used as an output marker for a fount.
    """



class IFakeInput(Interface):
    """
    A sample interface to be used as an input marker for a drain.
    """



@implementer(IDrain)
class FakeDrain(object):
    """
    Implements a fake IDrain for testing.

    @ivar received: All items that have thus far been received.
    @type received: L{list}

    @ivar stopped: All reasons that C{flowStopped} has been called with.
    @type stopped: L{list}
    """

    inputType = IFakeInput

    fount = None

    def __init__(self):
        self.received = []
        self.stopped = []


    def flowingFrom(self, fount):
        """
        Set the C{fount} attribute.

        @param fount: see L{IDrain}
        """
        self.fount = fount


    def receive(self, item):
        """
        Append an item to L{FakeDrain.received}.

        @param item: see L{IDrain}
        """
        if self.fount is None:
            raise RuntimeError(
                "Invalid state: can't call receive on a drain "
                "when it's got no fount.")
        self.received.append(item)


    def flowStopped(self, reason):
        """
        The flow was stopped, record C{reason} in L{FakeDrain.stopped}.

        @param reason: see L{IDrain}
        """
        self.stopped.append(reason)


verifyClass(IDrain, FakeDrain)



@implementer(IFount)
class FakeFount(object):
    """
    Fake fount implementation for testing.
    """

    outputType = IFakeOutput

    flowIsPaused = 0
    flowIsStopped = False
    def __init__(self):
        def _actuallyPause():
            self.flowIsPaused += 1
        def _actuallyResume():
            self.flowIsPaused -= 1

        self._pauser = Pauser(self._actuallyPause, self._actuallyResume)


    def flowTo(self, drain):
        """
        Record C{self.drain} and return its L{IDrain.flowingFrom} result.

        @param drain: see L{IFount}

        @return: see L{IFount}
        """
        self.drain = drain
        return self.drain.flowingFrom(self)


    def pauseFlow(self):
        """
        Record C{self.drain} and return its L{IDrain.flowingFrom} result.

        @param drain: see L{IFount}

        @return: see L{IFount}
        """
        return self._pauser.pause()


    def stopFlow(self):
        """
        Record that the flow was stopped by setting C{flowIsStopped}.
        """
        self.flowIsStopped = True

verifyClass(IFount, FakeFount)



@tube
class TesterTube(object):
    """
    Tube for testing that records its inputs.
    """

    def __init__(self):
        """
        Initialize structures for recording.
        """
        self.allReceivedItems = []


    def received(self, item):
        """
        Recieved an item, remember it.

        @param item: see L{ITube}
        """
        self.allReceivedItems.append(item)



@implementer(IDivertable)
class JustProvidesSwitchable(TesterTube):
    """
    A L{TesterTube} that just provides L{IDivertable} for tests that want
    to assert about interfaces (no implementation actually provided).
    """
