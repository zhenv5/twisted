# -*- test-case-name: twisted.tubes.test.test_tube -*-
# -*- test-case-name: twisted.tubes.test.test_tube.SeriesTest.test_diverterInYourDiverterSoYouCanDivertWhileYouDivert -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
See L{Tube}.
"""

from __future__ import print_function

from zope.interface import implementer
from zope.interface.verify import verifyClass

from twisted.python.components import proxyForInterface

from .itube import IDrain, ITube, IDivertable, IFount
from ._siphon import _tubeRegistry, _Siphon, _PlaceholderPause
from ._components import _registryActive



def tube(cls):
    """
    L{tube} is a class decorator which declares a given class to be an
    implementer of L{ITube} and fills out any methods or attributes which are
    not present on the decorated type with null-implementation methods (those
    which return None) and None attributes.

    @param cls: A class with some or all of the attributes or methods described
        by L{ITube}.
    @type cls: L{type}

    @return: C{cls}
    @rtype: L{type} which implements L{ITube}
    """

    # This is better than a superclass, because:

    # - you can't do a separate 'isinstance(Tube)' check instead of
    #   ITube.providedBy like you're supposed to

    # - you can't just instantiate Tube directly, that is pointless
    #   functionality so we're not providing it

    # - it avoids propagating a bad example that other codebases will copy to
    #   depth:infinity, rather than depth:1 where subclassing is actually sort
    #   of okay

    # - it provides a more straightforward and reliable mechanism for
    #   future-proofing code.  If you're inheriting from a superclass and you
    #   want it to do something to warn users, upgrade an interface, and so on,
    #   you have to try to cram a new meta-type into the user's hierarchy so a
    #   function gets invoked at the right time.  If you're invoking this class
    #   decorator, then it just gets invoked like a normal function, and we can
    #   put some code in here that examines the type and does whatever it wants
    #   to do, because the @ syntax simply called it as a function.

    # It still shares some issues with inheritance, such as:

    # - the direction of visibility within the hierarchy is still wrong.  you
    #   can still do 'self.someMethodIDidntImplement()' and get a result.

    # - it destructively modifies the original class, so what you see isn't
    #   quite what you get.  a cleaner compositional approach would simply wrap
    #   an object around another object (but that would mean inventing a new
    #   incompletely-specified type that floats around at runtime, rather than
    #   a utility to help you completely implement ITube at import time)

    def started(self):
        """
        A null implementation of started.
        """

    def stopped(self, reason):
        """
        A null implementation of stopped.
        """

    def received(self, item):
        """
        A null implementation of received
        """

    fillers = [('started', started),
               ('stopped', stopped),
               ('received', received),
               ('inputType', None),
               ('outputType', None)]

    notHere = object()

    for name, value in fillers:
        if getattr(cls, name, notHere) is notHere:
            setattr(cls, name, value)

    cls = implementer(ITube)(cls)
    verifyClass(ITube, cls)
    return cls



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
    @type start: an L{ITube}, or anything adaptable to L{IDrain}.

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
        currentFount = result.flowingFrom(None)
        drains = map(IDrain, tubes)
    for drain in drains:
        currentFount = currentFount.flowTo(drain)
    return result



@tube
class _DrainingTube(object):
    """
    A L{_DrainingTube} is an L{ITube} that unbuffers a list of items.  It is an
    implementation detail of the way that L{Diverter} works.
    """

    def __init__(self, items, eventualUpstream, eventualDownstream):
        """
        
        """
        self._items = list(items)
        self._eventualUpstream = eventualUpstream
        self._hangOn = self._eventualUpstream.pauseFlow()
        self._eventualDownstream = eventualDownstream


    def __repr__(self):
        """
        
        """
        return ("<Draining Tube {}>".format(repr(self._items)))


    def started(self):
        """
        
        """
        while self._items:
            item = self._items.pop(0)
            yield item
        self._eventualUpstream.flowTo(self._eventualDownstream)
        self._hangOn.unpause()



@implementer(IFount)
class _FakestFount(object):
    outputType = None
    drain = None

    def flowTo(self, drain):
        self.drain = drain
        return drain.flowingFrom(self)


    def pauseFlow(self):
        return _PlaceholderPause()


    def stopFlow(self):
        pass



class Diverter(proxyForInterface(IDrain, "_drain")):
    """
    
    """

    def __init__(self, divertable):
        """
        
        """
        assert IDivertable.providedBy(divertable)
        self._divertable = divertable
        self._friendSiphon = _Siphon(divertable)
        self._drain = self._friendSiphon._tdrain


    def __repr__(self):
        """
        Nice string representation for this Diverter which mentions what it is
        diverting.
        """
        return "<Diverter for {}>".format(self._divertable)


    def divert(self, drain):
        """
        Divert the flow from the fount which is flowing into this siphon's
        drain to the given drain, reassembling any buffered output from this
        siphon's tube first.
        """
        unpending = self._friendSiphon._pendingIterator

        pendingPending = self._divertable.reassemble(unpending) or []
        upstream = self._friendSiphon._tdrain.fount
        f = _FakestFount()
        dt = series(_DrainingTube(pendingPending, upstream, drain))
        again = f.flowTo(dt)
        again.flowTo(drain)
