
from twisted.trial.unittest import SynchronousTestCase

from zope.interface.verify import verifyObject

from ..memory import IteratorFount

from twisted.tubes.itube import IFount
from twisted.tubes.itube import StopFlowCalled
from .util import FakeDrain, FakeFount

class IteratorFountTests(SynchronousTestCase):
    """
    Tests for L{twisted.tubes.memory.IteratorFount}.
    """

    def test_flowTo(self):
        """
        L{IteratorFount.flowTo} sets its drain and calls C{flowingFrom} on its
        argument, returning that value.
        """
        f = IteratorFount([])
        ff = FakeFount()
        class FakeDrainThatContinues(FakeDrain):
            def flowingFrom(self, fount):
                super(FakeDrainThatContinues, self).flowingFrom(fount)
                return ff
        fd = FakeDrainThatContinues()
        result = f.flowTo(fd)

        self.assertIdentical(fd.fount, f)
        self.assertIdentical(f.drain, fd)
        self.assertIdentical(result, ff)


    def test_flowToDeliversValues(self):
        """
        L{IteratorFount.flowTo} will deliver all of its values to the given
        drain.
        """
        f = IteratorFount([1, 2, 3])
        fd = FakeDrain()
        f.flowTo(fd)
        self.assertEqual(fd.received, [1, 2, 3])


    def test_pauseFlow(self):
        """
        L{IteratorFount.pauseFlow} will pause the delivery of items.
        """
        f = IteratorFount([1, 2, 3])
        class DrainThatPauses(FakeDrain):
            def receive(self, item):
                super(DrainThatPauses, self).receive(item)
                self.fount.pauseFlow()

        fd = DrainThatPauses()
        f.flowTo(fd)
        self.assertEqual(fd.received, [1])


    def test_unpauseFlow(self):
        """
        When all pauses returned by L{IteratorFount.pauseFlow} have been
        unpaused, the flow resumes.
        """
        f = IteratorFount([1, 2, 3])
        fd = FakeDrain()
        pauses = [f.pauseFlow(), f.pauseFlow()]
        f.flowTo(fd)
        self.assertEqual(fd.received, [])
        pauses.pop().unpause()
        self.assertEqual(fd.received, [])
        pauses.pop().unpause()
        self.assertEqual(fd.received, [1, 2, 3])


    def test_stopFlow(self):
        """
        L{IteratorFount.stopFlow} stops the flow, propagating a C{flowStopped}
        call to its drain and ceasing delivery immediately.
        """
        f = IteratorFount([1, 2, 3])
        class DrainThatStops(FakeDrain):
            def receive(self, item):
                super(DrainThatStops, self).receive(item)
                self.fount.stopFlow()

        fd = DrainThatStops()
        f.flowTo(fd)
        self.assertEqual(fd.received, [1])
        self.assertEqual(fd.stopped[0].type, StopFlowCalled)



    def test_provides(self):
        """
        An L{IteratorFount} provides L{IFount}.
        """
        verifyObject(IFount, IteratorFount([]))
