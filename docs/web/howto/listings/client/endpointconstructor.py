from __future__ import print_function

from sys import argv

from twisted.internet.endpoints import TCP4ClientEndpoint, SSL4ClientEndpoint
from twisted.internet.task import react
from twisted.web.client import Agent
from twisted.web.http_headers import Headers



class EndpointConstructor(object):
    def __init__(self, reactor):
        self.reactor = reactor


    def constructEndpoint(
            self, scheme, host, port, httpsConnectionCreator):
        print('Creating an endpoint:',
              scheme, host, port, httpsConnectionCreator)
        if scheme == b'http':
            return TCP4ClientEndpoint(self.reactor, host, port)
        elif scheme == b'https':
            if httpsConnectionCreator is None:
                raise NotImplementedError('TLS support unavailable')
            return SSL4ClientEndpoint(
                self.reactor, host, port, httpsConnectionCreator)
        else:
            raise ValueError("Unsupported scheme: %r" % (scheme,))



def main(reactor, url=b"http://example.com/"):
    agent = Agent(reactor, endpointConstructor=EndpointConstructor(reactor))
    d = agent.request(
        'GET', url,
        Headers({'User-Agent': ['Twisted Web Client Example']}))
    d.addCallback(print, 'Response received')
    return d



react(main, argv[1:])
