# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
sendmsg(2) and recvmsg(2) support for Python.
"""

from twisted.python.compat import _PY3



__all__ = ["sendmsg", "recvmsg", "getSocketFamily", "SCM_RIGHTS"]

if not _PY3:
    from twisted.python._sendmsg import send1msg, recv1msg
    from twisted.python._sendmsg import getsockfam, SCM_RIGHTS
    __all__ += ["send1msg", "recv1msg", "getsockfam"]
else:
    from socket import SCM_RIGHTS



def sendmsg(socket, data, flags=0, ancillary=None):

    if _PY3:
        return socket.sendmsg([bytes([data])], flags, ancillary)
    else:
        return send1msg(socket.fileno(), data, flags, ancillary)



def recvmsg(socket, maxSize=8192, cmsg_size=4096, flags=0):
    """
    Recieve a message on a socket.

    @param socket: The socket to recieve the message on.
    @type socket: L{socket.socket}

    @param maxSize: The maximum number of bytes to receive from the socket using
        the datagram or stream mechanism. The default maximum is 8192.
    @type maxSize: L{int}

    @param cmsg_size: The maximum number of bytes to receive from the socket
        outside of the normal datagram or stream mechanism. The default maximum
        is 4096.
    @type cmsg_size: L{int}

    @param flags: Flags to affect how the message is sent.  See the C{MSG_}
        constants in the sendmsg(2) manual page. By default no flags are set.
    @type flags: L{int}

    @return: A 3-tuple of the bytes recieved using the datagram/stream
        mechanism, a L{list} of L{tuples} giving ancillary recieved data, and
        flags as an L{int} describing the data recieved.
    """

    if _PY3:
        # In Twisted's sendmsg.c, the csmg_space is defined as:
        #     int cmsg_size = 4096;
        #     cmsg_space = CMSG_SPACE(cmsg_size);
        # Since the default in Python 3's socket is 0, we need to define our own
        # default of 4096. -hawkie
        data, ancillary, flags = socket.recvmsg(
            maxSize, socket.CMSG_SPACE(csmg_size), flags)[0:3]
    else:
        data, flags, ancillary = recv1msg(
            socket.fileno(), flags, maxSize, csmg_size)

    return data, ancillary, flags




def getSocketFamily(socket):

    if _PY3:
        return socket.family
    else:
        return getsockfam(socket.fileno())
