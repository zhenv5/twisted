
"""
Unhandled error in Deferred:
Unhandled Error
Traceback (most recent call last):
  File "docs/core/howto/listings/tubes/rpn.py", line 74, in <module>
    react(main, argv[1:])
  File "/Users/glyph/Projects/Twisted/twisted/internet/task.py", line 875, in react
    finished = main(_reactor, *argv)
  File "docs/core/howto/listings/tubes/rpn.py", line 69, in main
    endpoint.listen(factoryFromFlow(mathFlow))
  File "/Users/glyph/Projects/Twisted/twisted/internet/endpoints.py", line 264, in listen
    reactor=self._reactor)
--- <exception caught here> ---
  File "/Users/glyph/Projects/Twisted/twisted/internet/defer.py", line 111, in execute
    result = callable(*args, **kw)
  File "/Users/glyph/Projects/Twisted/twisted/internet/_posixstdio.py", line 41, in __init__
    self.protocol.makeConnection(self)
  File "/Users/glyph/Projects/Twisted/twisted/internet/protocol.py", line 481, in makeConnection
    self.connectionMade()
  File "/Users/glyph/Projects/Twisted/twisted/tubes/protocol.py", line 147, in connectionMade
    self._flow(self._fount, self._drain)
  File "docs/core/howto/listings/tubes/rpn.py", line 64, in mathFlow
    nextDrain = fount.flowTo(processor)
  File "/Users/glyph/Projects/Twisted/twisted/tubes/protocol.py", line 93, in flowTo
    result = self.drain.flowingFrom(self)
  File "/Users/glyph/Projects/Twisted/twisted/tubes/tube.py", line 200, in flowingFrom
    return nextFount.flowTo(nextDrain)
  File "/Users/glyph/Projects/Twisted/twisted/tubes/tube.py", line 109, in flowTo
    result = self.drain.flowingFrom(self)
  File "/Users/glyph/Projects/Twisted/twisted/tubes/tube.py", line 200, in flowingFrom
    return nextFount.flowTo(nextDrain)
  File "/Users/glyph/Projects/Twisted/twisted/tubes/tube.py", line 109, in flowTo
    result = self.drain.flowingFrom(self)
  File "/Users/glyph/Projects/Twisted/twisted/tubes/tube.py", line 200, in flowingFrom
    return nextFount.flowTo(nextDrain)
  File "/Users/glyph/Projects/Twisted/twisted/tubes/tube.py", line 109, in flowTo
    result = self.drain.flowingFrom(self)
  File "/Users/glyph/Projects/Twisted/twisted/tubes/tube.py", line 200, in flowingFrom
    return nextFount.flowTo(nextDrain)
  File "/Users/glyph/Projects/Twisted/twisted/tubes/tube.py", line 109, in flowTo
    result = self.drain.flowingFrom(self)
  File "/Users/glyph/Projects/Twisted/twisted/tubes/tube.py", line 195, in flowingFrom
    self._siphon._deliverFrom(self._tube.started)
  File "/Users/glyph/Projects/Twisted/twisted/tubes/tube.py", line 349, in _deliverFrom
    assert self._pendingIterator is None, list(self._pendingIterator)
exceptions.AssertionError: []
"""

from twisted.tubes.framing import bytesToLines, linesToBytes
from twisted.tubes.tube import Tube
from twisted.internet.endpoints import serverFromString
from twisted.tubes.protocol import factoryFromFlow


from twisted.internet.defer import Deferred


from twisted.tubes.tube import series


class LinesToNumbersOrOperators(Tube):
    def received(self, line):
        from operator import add, mul
        try:
            yield int(line)
        except ValueError:
            if line == '+':
                yield add
            elif line == '*':
                yield mul

class Calculator(Tube):
    def __init__(self):
        self.stack = []
        
    def push(self, number):
        self.stack.append(number)

    def pop2(self):
        a = self.stack.pop()
        b = self.stack.pop()
        return a, b

    def do(self, operator):
        values = self.pop2()
        result = operator(*values)
        self.push(result)
        return result

    def received(self, value):
        if isinstance(value, int):
            self.calculator.push(value)
        else:
            yield self.calculator.do(value)

class NumbersToLines(Tube):
    def received(self, value):
        yield u"{0}".format(value).encode("ascii")

def calculatorDrain():
    return series(
        bytesToLines(),
        LinesToNumbersOrOperators(),
        Calculator(),
        NumbersToLines(),
        linesToBytes()
    )

def mathFlow(fount, drain):
    processor = calculatorDrain()
    nextDrain = fount.flowTo(processor)
    nextDrain.flowTo(drain)

def main(reactor, port="stdio:"):
    endpoint = serverFromString(reactor, port)
    endpoint.listen(factoryFromFlow(mathFlow))
    return Deferred()

from twisted.internet.task import react
from sys import argv
react(main, argv[1:])
