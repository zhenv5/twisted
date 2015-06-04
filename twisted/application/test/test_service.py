# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
"""
Tests for L{twisted.application.service}.
"""

from zope.interface import implementer
from zope.interface.exceptions import BrokenImplementation
from zope.interface.verify import verifyObject

from twisted.application.service import Application, IProcess
from twisted.application.service import IService, IServiceCollection
from twisted.application.service import Service
from twisted.python.compat import _PY3
from twisted.trial.unittest import TestCase


@implementer(IService)
class AlmostService(object):

    def setName(self, name):
        pass

    def setServiceParent(self, parent):
        pass

    def disownServiceParent(self):
        pass

    def privilegedStartService(self):
        pass

    def startService(self):
        pass

    def stopService(self):
        pass


class ServiceInterfaceTests(TestCase):

    def setUp(self):
        self.almostService = AlmostService()
        self.almostService.parent = None
        self.almostService.running = False
        self.almostService.name = None

    def test_hasAll(self):
        verifyObject(IService, self.almostService)

    def test_noName(self):
        del self.almostService.name
        with self.assertRaises(BrokenImplementation):
            verifyObject(IService, self.almostService)

    def test_noParent(self):
        del self.almostService.parent
        with self.assertRaises(BrokenImplementation):
            verifyObject(IService, self.almostService)

    def test_noRunning(self):
        del self.almostService.running
        with self.assertRaises(BrokenImplementation):
            verifyObject(IService, self.almostService)

class ApplicationTests(TestCase):
    """
    Tests for L{twisted.application.service.Application}.
    """
    def test_applicationComponents(self):
        """
        Check L{twisted.application.service.Application} instantiation.
        """
        app = Application('app-name')

        self.assertTrue(verifyObject(IService, IService(app)))
        self.assertTrue(
            verifyObject(IServiceCollection, IServiceCollection(app)))
        self.assertTrue(verifyObject(IProcess, IProcess(app)))


    def test_applicationComponentsArePersistable(self):
        """
        L{twisted.application.service.Application} implements L{IPersistable}.
        """
        app = Application('app-name')

        from twisted.persisted.sob import IPersistable
        self.assertTrue(verifyObject(IPersistable, IPersistable(app)))

    if _PY3:
        # FIXME: https://twistedmatrix.com/trac/ticket/7827
        # twisted.persisted is not yet ported to Python 3
        test_applicationComponentsArePersistable.skip = (
            "twisted.persisted is not yet ported to Python 3.")
