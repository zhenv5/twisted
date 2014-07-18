# -*- test-case-name: twisted.tubes.test.test_fan -*-
from zope.interface import implementer

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

    def flowTo(self, drain):
        """
        
        """
        self.drain = drain



@implementer(IDrain)
class _OutDrain(object):
    """

    """
    def __init__(self, founts):
        """
        
        """
        self._founts = founts


    def flowingFrom(self, fount):
        """
        
        """
        

    def receive(self, item):
        """
        
        """
        for fount in self._founts:
            fount.drain.receive(item)


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
        f = _OutFount()
        self._founts.append(f)
        return f
