# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Send a HTTP request to Docker over a Unix socket.

May need to be run as root.
"""
from __future__ import print_function

from sys import argv

from zope.interface import implementer

from twisted.internet.endpoints import UNIXClientEndpoint
from twisted.internet.task import react
from twisted.web.iweb import IAgentEndpointFactory
from twisted.web.client import Agent, readBody


@implementer(IAgentEndpointFactory)
class DockerEndpointFactory(object):
    """
    Connect to Docker's Unix socket.
    """
    def __init__(self, reactor):
        self.reactor = reactor


    def endpointForURI(self, uri):
        return UNIXClientEndpoint(self.reactor, "/var/run/docker.sock")



def main(reactor, path=b"/containers/json?all=1"):
    agent = Agent.usingEndpointFactory(reactor, DockerEndpointFactory(reactor))
    d = agent.request(b'GET', b"unix://localhost" + path)
    d.addCallback(readBody)
    d.addCallback(print)
    return d

react(main, argv[1:])
