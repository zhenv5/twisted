# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
sendmsg(2) support for Python.
"""

from twisted.python.compat import _PY3

__all__ = ["sendmsg", "recvmsg", "getSocketFamily"]

if not _PY3:
    from twisted.python._sendmsg import send1msg, recv1msg, getsockfam
    __all__ += ["send1msg", "recv1msg", "getsockfam"]


def sendmsg(socket, data, flags=0, ancillary=None):

    if _PY3:
        return socket.sendmsg([bytes([data])], flags, ancillary)
    else:
        return send1msg(socket.fileno(), data, flags, ancillary)


def recvmsg(socket, maxsize=8192, cmsg_size=4096, flags=0):

    if _PY3:
        # In Twisted's sendmsg.c, the csmg_space is defined as:
        #     int cmsg_size = 4096;
        #     cmsg_space = CMSG_SPACE(cmsg_size);
        # Since the default in Python 3's socket is 0, we need to define
        # it ourselves, and since it worked for sendmsg.c, it probably
        # works fine here. -hawkie
        data, ancillary, flags = socket.recvmsg(
            maxsize, socket.CMSG_SPACE(csmg_size), flags)[0:3]
    else:
        data, flags, ancillary = recv1msg(
            socket.fileno(), flags, maxsize, csmg_size)

    return data, ancillary, flags


def getSocketFamily(socket):

    if _PY3:
        return socket.family
    else:
        return getsockfam(socket.fileno())
