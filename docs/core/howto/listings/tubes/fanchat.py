
from collections import defaultdict
from json import loads, dumps

from zope.interface import Interface, implementer
from zope.interface.common import IMapping

from twisted.internet.endpoints import serverFromString
from twisted.internet.defer import Deferred
from twisted.tubes.protocol import factoryFromFlow
from twisted.tubes.itube import IFrame
from twisted.tubes.tube import series, tube
from twisted.tubes.framing import bytesToLines, linesToBytes
from twisted.tubes.fan import Out, In

class Participant(object):
    """
    
    """

    def __init__(self, hub, bytesFount, bytesDrain):
        """
        
        """
        self._hub = hub
        self._participation = {}
        self._in = In()
        self._router = Router()
        self._tube = Participantube(self)
        self._participating = {}
        self.client, toClientFount = self._router.newRoute()

        # thought: what if the Participant were persistent server-side? it
        # wouldn't be much work: Participantube is already basically stateless
        # itself; it just needs to grow a "preauthenticated" state which would
        # be useful for other reasons anyway.  the only change here would be
        # that "client" would need to flow to an Out() which new incoming
        # connections could attach to rather than flowing to directly -
        # self._router.

        clientCommands = bytesFount.flowTo(series(bytesToLines(),
                                                  LinesToCommands()))
        # self._in is both commands from our own client and also messages from
        # other clients.
        clientCommands.flowTo(self._in.newDrain())

        (toClientFount
         .flowTo(series(CommandsToLines(), linesToBytes()))
         .flowTo(bytesDrain))


    def participateIn(self, channel):
        """
        
        """
        fountFromChannel, drainToChannel = (
            self._hub.channelNamed(channel).participate(self)
        )
        fountFromChannel.flowTo(self._in.newDrain())
        key, fountToChannel = self._router.newRoute()
        fountToChannel.flowTo(drainToChannel)
        self._participating[channel] = key



def dispatch(self, item):
    """
    Dispatch a received item to a "do_" method.
    """
    return getattr(self, "do_" + item.pop("type"))(**item)



class IDirected(Interface):
    """
    A message that is directed to some specific receiver, via a L{Router}.

    Basically just an interface for L{to}.
    """


@implementer(IDirected)
class to(object):
    """
    
    """
    def __init__(self, who, what):
        """
        
        """
        self._who = who
        self._what = what


@tube
class _AddressedTo(object):
    """
    
    """
    def __init__(self, token):
        """
        
        """
        self._token = token
        
    def received(self, item):
        """
        
        """
        if isinstance(item, to):
            if item._who is self._token:
                yield item._what



class Router(object):
    """
    Route messages created by C{to}.

    Really inefficient implementation, but the inefficient details (the use of
    "Out") is all private, and could be fixed/optimized fairly easily.
    """

    def __init__(self):
        """
        
        """
        # inputType of this Out is IDirected
        self._out = Out()
        self.drain = self._out.drain


    def newRoute(self):
        """
        
        """
        token = object()
        fount = self._out.newFount().flowTo(_AddressedTo(token))
        return (token, fount)



@tube
class Participantube(object):
    """
    
    """
    inputType = IDirected # really wish I had parametric types here!
                          # IDirected[IMapping]?

    def __init__(self, participant):
        """
        
        """
        self._participant = participant

    received = dispatch

    def do_name(self, name):
        """
        Give myself a name.
        """
        self._participant.name = name
        yield to(self._participant.client,
                 {"named": name})

    def do_join(self, channel):
        """
        Join a channel.
        """
        self._participant.participateIn(channel)
        yield to(self._participant.client,
                 dict(type="joined", channel="channel"))
        yield to(self._participant._participating[channel],
                 dict(type="joined"))

    def do_speak(self, channel, message):
        """
        I spoke (on a channel).
        """
        # NB: "sender", "channel" added by AddSender, so we don't have to do
        # that here.
        yield to(self._participant._participating[channel],
                 dict(type="spoke", message=message))

    def do_shout(self, message):
        """
        I shouted a message to everyone on all the channels I'm currently
        participating in.

        (Of dubious utility for an actual chat protocol, but showcases some
        interesting functionality vis-a-vis sending outputs to multiple places
        without worrying about flow control anywhere.)
        """
        for channel in self._participant._participating.values():
            yield to(channel, dict(type="spoke", message=message))

    def do_tell(self, receiver, message):
        """
        I sent a user a direct message.
        """
        # TODO: implement _establishRapportWith; should be more or less like
        # joining a channel.
        rapport = self._participant._establishRapportWith(receiver)
        yield to(rapport, dict(type="told", message=message))
        # TODO: when does a rapport end?  does a conversation time out?
        # Presumably a buffer has to be empty.  should I have to yield to(...)
        # something in order to establish rapport / join channels in the first
        # place?  should I have to yield a Deferred?

    def do_told(self, sender, message):
        """
        A user sent me a direct message.
        """
        yield to(self._participant.client, message)

    def do_spoke(self, channel, sender, message):
        """
        Someone spoke to me (on a channel).
        """
        yield to(self._participant.client,
                 dict(type="spoke", channel=channel, sender=sender.name,
                      message=message))



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

@tube
class CommandsToLines(object):
    """
    
    """
    inputType = IMapping
    outputType = IFrame

    def received(self, message):
        """
        
        """
        return dumps(message)



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
                yield dict(item, sender=participant, channel=self._name)

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
        @tube
        class RemoveOnStop(object):
            def received(stopper, item):
                yield item
            def stopped(stopper, reason):
                self.participants.remove(participant)
        participant = Participant(self, fount.flowTo(RemoveOnStop(), drain))
        self.participants.append(participant)

    def channelNamed(self, name):
        """
        get a channel with the given name
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
