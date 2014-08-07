# -*- test-case-name: twisted.tubes.test.test_pauser -*-

"""
Implementation helper for pausing and resuming things.
"""

from zope.interface import implementer

from .itube import AlreadyUnpaused, IPause


@implementer(IPause)
class _Pause(object):
    def __init__(self, pauser):
        self._friendPauser = pauser
        self._alive = True


    def unpause(self):
        if self._alive:
            self._friendPauser._pauses -= 1
            if self._friendPauser._pauses == 0:
                self._friendPauser._actuallyResume()
            self._alive = False
        else:
            raise AlreadyUnpaused()



class Pauser(object):
    """
    Multiple parties may be interested in suppressing some ongoing concurrent
    activity, each for their own purposes.

    A L{Pauser} maintains the state associated with each of these independent
    pauses, providing an object for each one, making it straightforward for you
    to implement a high-level pause and resume API suitable for use from
    multiple clients, in terms of low-level state change operations.
    """
    def __init__(self, actuallyPause, actuallyResume):
        """
        @param actuallyPause: a callable to be invoked when the underlying
            system ought to transition from paused to unpaused.
        @type actuallyPause: 0-argument callable

        @param actuallyResume: a callable to be invoked when the underlying
            system ought to transition from unpaused to paused.
        @type actuallyPause: 0-argument callable
        """
        self._actuallyPause = actuallyPause
        self._actuallyResume = actuallyResume
        self._pauses = 0


    def pause(self):
        """
        Pause something, getting an L{IPause} provider which can be used to
        unpause it.

        @rtype: L{IPause}
        """
        if not self._pauses:
            self._actuallyPause()
        self._pauses += 1
        return _Pause(self)



