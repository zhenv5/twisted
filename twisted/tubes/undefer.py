# -*- test-case-name: twisted.tubes.test.test_undefer -*-
from twisted.internet.defer import Deferred
from .tube import tube, series, skip


@tube
class PauseThenYield(object):
    def received(self, item):
        if isinstance(item, Deferred):
            pause = self._selfAsFount.pauseFlow()
            def gotResult(result):
                gotResult.ok = True
                gotResult.result = result
            def gotError(failure):
                gotResult.ok = False
                gotResult.result = failure
            def done(result):
                pause.unpause()
            item.addCallbacks(gotResult, gotError).addCallback(done)
            yield skip
            if gotResult.ok:
                yield gotResult.result
            else:
                gotResult.result.raiseException()



def deferredToResult():
    """
    
    """
    pty = PauseThenYield()
    drain = series(pty)
    aFount = drain.flowingFrom(None)
    pty._selfAsFount = aFount
    return drain



