#!/usr/bin/env python
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
"""
tls_alpn_npn_server
~~~~~~~~~~~~~~~~~~~

This test script demonstrates the usage of the nextProtocols API as a server
peer.

It performs next protocol negotiation using NPN and ALPN.

It will print what protocol was negotiated and exit.

To test this, use OpenSSL's s_client command, with either or both of the
-nextprotoneg and -alpn arguments. For example:

    openssl s_client -connect localhost:8080 -alpn h2,http/1.1
    openssl s_client -connect localhost:8080 -nextprotoneg h2,http/1.1
"""
import functools
import mimetypes
import os
import os.path
import sys

from OpenSSL import crypto
from twisted.internet.endpoints import SSL4ServerEndpoint
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor, ssl
from twisted.python.modules import getModule



# The list of protocols we'd be prepared to speak after the TLS negotiation is
# complete.
# The order of the protocols here is an order of preference. This indicates
# that we'd prefer to use HTTP/2 if possible (where HTTP/2 is using the token
# 'h2'), but would also accept HTTP/1.1.
# The bytes here are sent literally on the wire, and so there is no room for
# ambiguity about text encodings.
# Try changing this list by adding, removing, and reordering protocols to see
# how it affects the result.
NEXT_PROTOCOLS = [b'h2', b'http/1.1']



class BasicResponderProtocol(Protocol):
    def connectionMade(self):
        self.complete = False
        print("Connection made")


    def dataReceived(self, data):
        print(self.transport.nextProtocol)
        self.complete = True


    def connectionLost(self, reason):
        # If we haven't received any data, an error occurred. Otherwise,
        # we lost the connection on purpose.
        if self.complete:
            print("Connection closed cleanly")
        else:
            print("Connection lost due to error %s" % (reason,))



class ResponderFactory(Factory):
    def buildProtocol(self, addr):
        return BasicResponderProtocol()



certData = getModule(__name__).filePath.sibling('server.pem').getContent()
certificate = ssl.PrivateCertificate.loadPEM(certData)

options = ssl.CertificateOptions(
    privateKey=certificate.privateKey.original,
    certificate=certificate.original,
    nextProtocols=NEXT_PROTOCOLS,
)
endpoint = SSL4ServerEndpoint(reactor, 8080, options)
endpoint.listen(ResponderFactory())
reactor.run()
