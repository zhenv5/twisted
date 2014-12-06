
"""
Common functionality for implementing L{IFount} and L{IDrain}
"""

def beginFlowingTo(fount, drain):
    """
    to correctly implement fount.flowTo you need to do certain things; do those
    things here
    """
    oldDrain = fount.drain
    fount.drain = drain
    if ( (oldDrain is not None) and (oldDrain is not drain) and
         (oldDrain.fount is fount) ):
        oldDrain.flowingFrom(None)
    if drain is None:
        return
    return drain.flowingFrom(fount)



def beginFlowingFrom(drain, fount):
    """
    to correctly implement drain.flowingFrom you need to do certian things; do
    those things here
    """
    if fount is not None:
        outType = fount.outputType
        inType = drain.inputType
        if outType is not None and inType is not None:
            if not inType.isOrExtends(outType):
                raise TypeError()
    oldFount = drain.fount
    drain.fount = fount
    if ( (oldFount is not None) and (oldFount is not fount) and
         (oldFount.drain is drain) ):
        oldFount.flowTo(None)

