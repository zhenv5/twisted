
from twisted.tubes.framing import bytesToLines, linesToBytes
from twisted.tubes.protocol import factoryFromFlow
from twisted.tubes.tube import series, Tube

from twisted.internet.endpoints import serverFromString
from twisted.internet.defer import Deferred

class LinesToNumbersOrOperators(Tube):
    def received(self, line):
        line = line.strip()
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
            self.push(value)
        else:
            yield self.do(value)

class NumbersToLines(Tube):
    def received(self, value):
        yield u"{0}".format(value).encode("ascii")

def calculatorDrain():
    return series(
        bytesToLines("\n"),
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
