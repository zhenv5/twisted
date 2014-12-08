# -*- test-case-name: twisted.tubes.test.test_fan -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
A L{Router} receives items with addressing information and dispatches them to
an appropriate output, stripping the addressing information off.

Use like so::

    from twisted.tubes.routing import Router, Routed, to

    aRouter = Router(int)

    evens, evenFount = aRouter.newRoute()
    odds, oddFount = aRouter.newRoute()

    @tube
    class EvenOdd(object):
        outputType = Routed(int)
        def received(self, item):
            if (item % 2) == 0:
                yield to(evens, item)
            else:
                yield to(odds, item)

    numbers.flowTo(aRouter)

This creates a fount in evenFount and oddFount, which each have an outputType
of "int".
"""

from .tube import tube
from .fan import Out


class Routed(object):
    """
    The inputType for routing.
    """

    def __init__(self, interface=None):
        """
        
        """
        self.interface = interface


    def isOrExtends(self, other):
        """
        Does the other router extend it?
        """
        if other is None:
            return True
        if not isinstance(other, Routed):
            return False
        if self.interface is None or other.interface is None:
            return True
        return self.interface.isOrExtends(other.interface)


    def providedBy(self, instance):
        """
        Is this L{Routed} provided by a particular value?
        """
        if not isinstance(instance, _To):
            return False
        if self.interface is None:
            return True
        return self.interface.proviedBy(instance._what)


class _To(object):
    """
    

    @ivar _who: 
    @type _who: 

    @ivar _what: 
    @type _what: 
    """

    def __init__(self, who, what):
        """
        

        @param _who: 
        @type _who: 

        @param _what: 
        @type _what: 
        """
        self._who = who
        self._what = what



def to(who, what):
    """
    
    """
    return _To(who, what)



@tube
class Router(object):
    """
    

    @ivar _out: 
    @type _out: 

    @ivar drain: 
    @type drain: 
    """

    def __init__(self, outputType=None):
        # This is a really inefficient implementation, but the use of 'Out' is
        # entirely an implementation detail.
        self._out = Out(inputType=Routed(outputType), outputType=outputType)
        self.drain = self._out.drain


    def newRoute(self):
        """
        Create a new route which the input may flow things to.
        """
        token = object()
        @tube
        class AddressedTo(object):
            if self.drain is not None:
                inputType = self.drain.inputType
                outputType = self.drain.inputType.interface
            def received(self, item):
                if isinstance(item, to):
                    if item._who is self._token:
                        yield item._what
        fount = self._out.newFount().flowTo(AddressedTo())
        return (token, fount)



