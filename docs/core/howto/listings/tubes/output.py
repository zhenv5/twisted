from twisted.tubes.tube import Pump
class IntegersToLines(Pump):
    def received(self, item):
        yield "= " + str(item)
