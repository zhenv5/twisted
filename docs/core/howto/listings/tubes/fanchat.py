
from collections import defaultdict
from json import loads
# from zope.interface import implementer
from twisted.internet.endpoints import serverFromString
from twisted.tubes.protocol import factoryFromFlow
from zope.interface.common import IMapping
from twisted.tubes.itube import IFrame

from twisted.internet.defer import Deferred


from twisted.tubes.tube import series, tube
# cut here

from twisted.tubes.framing import bytesToLines
from twisted.tubes.begin import beginFlowingFrom
from twisted.tubes.fan import Out
from twisted.tubes.fan import In

class Participant(object):
    """
    
    """

    def __init__(self, hub):
        """
        
        """
        self._hub = hub
        self._participation = {}
        self._in = In()
        # This drain is public, for messages from the wire.
        self.drain = self._in.newDrain()
        self._out = Out()
        (self._in.fount.flowTo(series(Participantube(self)))
         .flowTo(self._out.drain))
        self._participating = {}

    def participateIn(self, channel):
        """
        
        """
        fount, drain = (self._hub.channelNamed(channel)
                        .participate(self))
        self.participatingIn(channel, fount, drain)
        # fount -> messages from that channel
        fount.flowTo(self._in.newDrain())
        # drain -> messages to that channel - I need to tell it to send me
        # backpressure because I am going to send it messages in do_speak.
        self._out.newFount().flowTo(series(Discarder(), drain))
        self._participating[channel] = drain

    def sayInChannel(self, channel, message):
        """
        
        """
        # I need to look up the appropriate channel to call a method on.
        # However, if I call a method on it - e.g. "receive" - directly, the
        # channel won't be able to apply backpressure to us.  What do do?
        # backpressure is set up in participateIn, we discard all inputs there,
        # and then this is the thing that produces the actual input. this is OK
        # because it's only ever called *by* receive(). tricky constraint to
        # enforce though :-\
        
        self._participating[channel].receive(
            dict(channel=channel, message=message, type="spoke")
        )




def dispatch(self, item):
    """
    Dispatch a received item to a "do_" method.
    """
    return getattr(self, "do_" + item.pop("type"))(**item)



@tube
class Discarder(object):
    """
    Discard all my input.
    """



@tube
class Participantube(object):
    """
    
    """
    inputType = IMapping

    def __init__(self, participant):
        """
        
        """
        self._participant = participant

    received = dispatch

    def do_name(self, name):
        """
        
        """
        self._participant.name = name
        yield {"named": name}

    def do_join(self, channel):
        self._participant.participateIn(channel)
        yield {"joined": channel}

    def do_speak(self, channel, message):
        """
        I spoke (on a channel).
        """
        self._participant.sayInChannel(channel, message)
        return ()

    def do_spoke(self, channel, sender, message):
        """
        Someone spoke to me (on a channel).
        """
        yield dict(type="spoke", channel=channel, sender=sender.name,
                   message=message)



@tube
class LinesToCommands(object):
    """
    
    """
    inputType = IFrame
    outputType = IMapping

    def received(self, line):
        """
        
        """
        return loads(line)



class Channel(object):
    """
    
    """
    def __init__(self, hub, name):
        """
        
        """
        self._hub = hub
        self._name = name
        self._out = Out()
        self._in = In()
        self._in.fount.flowTo(self._out.drain)

    def participate(self, participant):
        """
        @return: a 2-tuple of (fount, drain) where the fount is messages that
            the given participant can observe and drain is an input for
            messages from that participant
        """
        @tube
        class AddSender(object):
            def received(self, item):
                item["sender"] = participant
                yield item

        fount = self._out.newFount()
        drain = self._in.newDrain()
        return fount, series(AddSender(), drain)


class Hub(object):
    def __init__(self):
        self.participants = []
        def newChannel(name):
            return Channel(self, name)
        self.channels = defaultdict(newChannel)

    def newParticipant(self, fount, drain):
        participant = Participant(self)
        @tube
        class RemoveOnStop(object):
            def received(stopper, item):
                yield item
            def stopped(stopper, reason):
                self.participants.remove(participant)

        self.participants.append(participant)
        fount.flowTo(bytesToLines(), LinesToCommands(),
                     participant.drain).flowTo(drain)

    def channelNamed(self, name):
        """
        
        """
        return self.channels[name]

def main(reactor, port="stdio:"):
    endpoint = serverFromString(reactor, port)
    hub = Hub()
    endpoint.listen(factoryFromFlow(hub.newParticipant))
    return Deferred()

from twisted.internet.task import react
from sys import argv
react(main, argv[1:])
