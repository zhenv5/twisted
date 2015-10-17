#!/usr/bin/env python
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
"""
tls_alpn_npn
~~~~~~~~~~~~

It demonstrates the usage of the nextProtocols API as a client peer.

It performs next protocol negotiation using NPN and ALPN.

It will print what protocol was negotiated, and then exit.
The global variables are provided as input values.
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
# The bytes here are sent literally on the wire, and so there is no room for
# ambiguity about text encodings.
# Try changing this list by adding, removing, and reordering protocols to see
# how it affects the result.
NEXT_PROTOCOLS = [b'h2', b'http/1.1']

# ??? add some info about this data ??? 
TLS_TRIGER_DATA = b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'

def main(reactor):
    options = ssl.optionsForClientTLS(
        hostname=TARGET_HOST,
        # `nextProtocols` is the targetd option of this example.
        extraCertificateOptions={'nextProtocols': NEXT_PROTOCOLS}
    )

    class BasicH2Request(protocol.Protocol):
        def connectionMade(self):
            print("Connection made")
            # ??? Why do we need this deferred ???
            self.complete = defer.Deferred()
            # Write some data to trigger the TLS handshake.
            # ??? this does not make sense for me.
            # ??? how can we sent data without knowing the protocol?
            self.transport.write(TLS_TRIGER_DATA)

        def dataReceived(self, data):
            # We can only safely be sure what the next protocol is when we know
            # the TLS handshake is over. This is generally *not* in the call to
            # connectionMade, but instead only when we've received some data
            # back.
            print('Next protocol is: %s' % (self.transport.getNextProtocol(),))
            self.transport.loseConnection()

            # ?? what is this ????
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
