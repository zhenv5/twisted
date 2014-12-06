
from twisted.tubes.protocol import factoryFromFlow
from twisted.tubes.tube import tube

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

@tube
class LinesToNumbersOrOperators(object):
    def received(self, line):
        from operator import add, mul

        try:
            yield int(line)
        except ValueError:
            if line == '+':
                yield add
            elif line == '*':
                yield mul

@tube
class CalculatingTube(object):
    def __init__(self, calculator):
        self.calculator = calculator

    def received(self, value):
        if isinstance(value, int):
            self.calculator.push(value)
        else:
            yield self.calculator.do(value)

@tube
class NumbersToLines(object):
    def received(self, value):
        yield str(value).encode("ascii")


@tube
class Prompter(object):
    def started(self):
        yield "> "
    def received(self, item):
        yield "> "




from twisted.tubes.fan import Thru

def calculatorSeries():
    from twisted.tubes.tube import series
    from twisted.tubes.framing import bytesToLines, linesToBytes

    full = series(bytesToLines(),
                  Thru([
                      series(Prompter()),
                      series(LinesToNumbersOrOperators(),
                             CalculatingTube(Calculator()),
                             NumbersToLines()),
                  ]),
                  linesToBytes())
    print("created full", full)
    return full

def mathFlow(fount, drain):
    processor = calculatorSeries()
    nextFount = fount.flowTo(processor)
    print("nextFount?", nextFount)
    nextFount.flowTo(drain)

def main(reactor, port="stdio:"):
    # import sys
    # from twisted.python.log import startLogging
    # startLogging(sys.stdout)
    endpoint = serverFromString(reactor, port)
    endpoint.listen(factoryFromFlow(mathFlow))
    return Deferred()

from twisted.internet.task import react
from sys import argv
react(main, argv[1:])
