from zope.interface import implementer
from twisted.internet.protocol import Protocol, Factory
from twisted.internet.task import react
from twisted.internet.defer import Deferred
from twisted.internet.endpoints import serverFromString
from twisted.internet.interfaces import IHalfCloseableProtocol

@implementer(IHalfCloseableProtocol)
class Echo(Protocol):
    def dataReceived(self, data):
        self.transport.write(data)
    def writeConnectionLost(self, reason):
        pass
    def readConnectionLost(self, reason):
        pass

def main(reactor):
    endpoint = serverFromString(reactor, 'stdio:')
    endpoint.listen(Factory.forProtocol(Echo))
    return Deferred()

react(main, [])
