# -*- test-case-name: twisted.tube.test.test_undefer -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.tubes.undefer}.
"""

from twisted.trial.unittest import SynchronousTestCase
from twisted.tubes.undefer import deferredToResult
from twisted.internet.defer import Deferred
from twisted.tubes.test.util import FakeDrain
from twisted.tubes.test.util import FakeFount
from twisted.tubes.tube import tube, series

class DeferredIntegrationTests(SynchronousTestCase):
    """
    Tests for L{deferredToResult}.
    """

    def test_deferredSupport(self):
        """
        
        """
        d1 = Deferred()
        d2 = Deferred()

        @tube
        class SomeDeferreds(object):
            """
            
            """
            def started(self):
                """
                
                """
                yield d1
                yield d2
                

        fd = FakeDrain()
        FakeFount().flowTo(series(SomeDeferreds(), deferredToResult())).flowTo(fd)
        self.assertEqual(fd.received, [])
        d1.callback(1)
        self.assertEqual(fd.received, [1])
        d2.callback(2)
        self.assertEqual(fd.received, [1, 2])
