
from twisted.trial.unittest import SynchronousTestCase

from ..memory import IteratorFount

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
