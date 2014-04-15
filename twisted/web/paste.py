# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Integration with L{paste.deploy}
"""

def serverFactory(globalConfig, ports="tcp:8080", reactor=None):
    """
    Creates a WSGI server for use with L{paste.deploy}.

    @param globalConfig: Global configuration from paste.
    @type globalConfig: L{dict} of L{str}

    @param ports: Space seperate list of endpoint description to listen on.
    @type ports: L{str}

    @param reactor: Name of reactor to use.
    @type reactor: L{str}
    """
