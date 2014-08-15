
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
