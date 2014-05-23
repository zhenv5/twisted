
from twisted.tubes.protocol import factoryFromFlow
from twisted.tubes.tube import Tube

from twisted.internet.endpoints import serverFromString
from twisted.internet.defer import Deferred

class Calculator(object):
    def __init__(self):
        self.stack = []

    def push(self, number):
        self.stack.append(number)

    def do(self, operator):
        left = self.stack.pop()
        right = self.stack.pop()
        result = operator(left, right)
        self.push(result)
        return result

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

class CalculatingTube(Tube):
    def __init__(self, calculator):
        self.calculator = calculator

    def received(self, value):
        if isinstance(value, int):
            self.calculator.push(value)
        else:
            yield self.calculator.do(value)

class NumbersToLines(Tube):
    def received(self, value):
        yield u"{0}".format(value).encode("ascii")

def calculatorSeries():
    from twisted.tubes.tube import series
    from twisted.tubes.framing import bytesToLines, linesToBytes

    return series(
        bytesToLines(),
        LinesToNumbersOrOperators(),
        CalculatingTube(Calculator()),
        NumbersToLines(),
        linesToBytes()
    )

def mathFlow(fount, drain):
    processor = calculatorSeries()
    nextDrain = fount.flowTo(processor)
    nextDrain.flowTo(drain)

def main(reactor, port="stdio:"):
    endpoint = serverFromString(reactor, port)
    endpoint.listen(factoryFromFlow(mathFlow))
    return Deferred()

from twisted.internet.task import react
from sys import argv
react(main, argv[1:])
