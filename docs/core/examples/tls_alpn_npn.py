#!/usr/bin/env python
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
"""
tls_alpn_npn
~~~~~~~~~~~~

A test script that can be used to connect to a server on the internet and
perform next protocol negotiation using NPN and ALPN. Demonstrates the correct
usage of the nextProtocols API.

To use this, simple execute it from the command-line. It should print out what
protocol was negotiated, and then exit. You can tweak the global variables in
this file to vary certain aspects of the testing.
"""
from twisted.internet import ssl, protocol, defer, endpoints, task

# The hostname the remote server to contact.
TARGET_HOST = u'google.com'

# The port to contact.
TARGET_PORT = 443

# The list of protocols we'd be prepared to speak after the TLS negotiation is
# complete.
# The order of the protocols here is an order of preference: most servers will
# attempt to respect our preferences when doing the negotiation. This indicates
# that we'd prefer to use HTTP/2 if possible (where HTTP/2 is using the token
# 'h2'), but would also accept HTTP/1.1.
# Note that these are bytestrings: this is because the bytes here are sent
# literally on the wire, and so there is no room for ambiguity about text
# encodings.
# Try changing this list by adding, removing, and reordering protocols to see
# how it affects the result.
NEXT_PROTOCOLS = [b'h2', b'http/1.1']


def main(reactor):
    options = ssl.optionsForClientTLS(
        hostname=TARGET_HOST,
        extraCertificateOptions={'nextProtocols': NEXT_PROTOCOLS}
    )

    class BasicH2Request(protocol.Protocol):
        def connectionMade(self):
            print("Connection made")
            self.complete = defer.Deferred()
            # Write some data to trigger the SSL handshake.
            self.transport.write(b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n')

        def dataReceived(self, data):
            # We can only safely be sure what the next protocol is when we know
            # the TLS handshake is over. This is generally *not* in the call to
            # connectionMade, but instead only when we've received some data
            # back.
            print('Next protocol is: %s' % (self.transport.getNextProtocol(),))
            self.transport.loseConnection()
            if self.complete is not None:
                self.complete.callback(None)
                self.complete = None

        def connectionLost(self, reason):
            if self.complete is not None:
                print("Connection lost due to error %s" % (reason,))
                self.complete.callback(None)
            else:
                print("Connection closed cleanly")

    return endpoints.connectProtocol(
        endpoints.SSL4ClientEndpoint(
            reactor,
            TARGET_HOST,
            TARGET_PORT,
            options
        ),
        BasicH2Request()
    ).addCallback(lambda protocol: protocol.complete)

task.react(main)
