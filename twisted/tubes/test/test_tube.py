# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.tubes.tube}.
"""

from zope.interface import implementer
from zope.interface.verify import verifyObject

from twisted.trial.unittest import TestCase
from twisted.tubes.test.util import (TesterTube, FakeFount,
                                     FakeDrain, IFakeInput)

from twisted.tubes.itube import IDivertable
from twisted.python.failure import Failure
from twisted.tubes.tube import Tube, series, _Pauser, _Siphon
from twisted.tubes.itube import IPause
from twisted.tubes.itube import AlreadyUnpaused
from twisted.tubes.itube import ITube
from zope.interface.declarations import directlyProvides
from twisted.internet.defer import Deferred, succeed


class ReprTube(Tube):
    def __repr__(self):
        return '<Tube For Testing>'



class PassthruTube(Tube):
    def received(self, data):
        yield data



class FakeFountWithBuffer(FakeFount):
    """
    Probably this should be replaced with a C{MemoryFount}.
    """
    def __init__(self):
        super(FakeFountWithBuffer, self).__init__()
        self.buffer = []


    def bufferUp(self, item):
        self.buffer.append(item)


    def flowTo(self, drain):
        result = super(FakeFountWithBuffer, self).flowTo(drain)
        self._go()
        return result


    def _actuallyResume(self):
        super(FakeFountWithBuffer, self)._actuallyResume()
        self._go()


    def _go(self):
        while not self.flowIsPaused and self.buffer:
            item = self.buffer.pop(0)
            self.drain.receive(item)



class StopperTest(TestCase):
    """
    Tests for L{_Pauser}, helper for someone who wants to implement a thing
    that pauses.
    """

    def test_pauseOnce(self):
        """
        One call to L{_Pauser.pause} will call the actuallyPause callable.
        """
        def pause():
            pause.d += 1
        pause.d = 0
        pauser = _Pauser(pause, None)
        result = pauser.pauseFlow()
        self.assertTrue(verifyObject(IPause, result))
        self.assertEqual(pause.d, 1)


    def test_pauseThenUnpause(self):
        """
        A call to L{_Pauser.pause} followed by a call to the result's
        C{unpause} will call the C{actuallyResume} callable.
        """
        def pause():
            pause.d += 1
        pause.d = 0
        def resume():
            resume.d += 1
        resume.d = 0
        pauser = _Pauser(pause, resume)
        pauser.pauseFlow().unpause()
        self.assertEqual(pause.d, 1)
        self.assertEqual(resume.d, 1)


    def test_secondUnpauseFails(self):
        """
        The second of two consectuive calls to L{IPause.unpause} results in an
        L{AlreadyUnpaused} exception.
        """
        def pause():
            pass
        def resume():
            resume.d += 1
        resume.d = 0
        pauser = _Pauser(pause, resume)
        aPause = pauser.pauseFlow()
        aPause.unpause()
        self.assertRaises(AlreadyUnpaused, aPause.unpause)
        self.assertEqual(resume.d, 1)


    def test_repeatedlyPause(self):
        """
        Multiple calls to L{_Pauser.pause} where not all of the pausers are
        unpaused do not result in any calls to C{actuallyResume}.
        """
        def pause():
            pause.d += 1
        pause.d = 0
        def resume():
            resume.d += 1
        resume.d = 0
        pauser = _Pauser(pause, resume)
        one = pauser.pauseFlow()
        two = pauser.pauseFlow()
        three = pauser.pauseFlow()
        four = pauser.pauseFlow()

        one.unpause()
        two.unpause()
        three.unpause()
        self.assertEqual(pause.d, 1)
        self.assertEqual(resume.d, 0)
        four.unpause()
        self.assertEqual(resume.d, 1)



class TubeTest(TestCase):
    """
    Tests for L{Tube}'s various no-ops.
    """

    def test_provider(self):
        """
        L{Tube} provides L{ITube}.
        """
        self.failUnless(verifyObject(ITube, Tube()))


    def test_noOps(self):
        """
        All of L{Tube}'s implementations of L{ITube} are no-ops.
        """
        # There are no assertions here because there's no reasonable way this
        # test will fail rather than error; however, coverage --branch picks up
        # on methods which haven't been executed and the fact that these
        # methods exist (i.e. for super() to invoke them) is an important
        # property to verify. -glyph

        # TODO: maybe make a policy of this or explain it somewhere other than
        # a comment.  Institutional learning ftw.

        tube = Tube()
        tube.started()
        tube.received(None)
        tube.stopped(None)



class SiphonTest(TestCase):
    """
    Tests for L{series}.
    """

    def setUp(self):
        """
        Create a siphon, and a fake drain and fount connected to it.
        """
        self.tube = TesterTube()
        self.siphonDrain = series(self.tube)
        self.ff = FakeFount()
        self.fd = FakeDrain()


    def test_tubeStarted(self):
        """
        The L{_Siphon} starts its L{Tube} upon C{flowingFrom}.
        """
        class Starter(Tube):
            def started(self):
                yield "greeting"

        self.ff.flowTo(series(Starter(), self.fd))
        self.assertEquals(self.fd.received, ["greeting"])


    def test_tubeReStarted(self):
        """
        It's perfectly valid to take a L{_Siphon} and call C{flowingFrom} with
        the same drain it's already flowing to.

        This will happen any time that a series is partially constructed and
        then flowed to a new drain.
        """
        class ReStarter(Tube):
            didStart = False
            def started(self):
                if self.didStart:
                    yield "regreeting"
                else:
                    self.didStart = True
                    yield "greeting"

        srs = series(PassthruTube(), ReStarter(),
                     PassthruTube())
        nextFount = self.ff.flowTo(srs)
        self.assertEqual(self.ff.flowIsPaused, 1)
        print(nextFount)
        nextFount.flowTo(self.fd)
        self.assertEqual(self.ff.flowIsPaused, 0)
        self.assertEquals(self.fd.received, ["greeting"])


    def test_tubeStopped(self):
        """
        The L{_Siphon} stops its L{Tube} and propagates C{flowStopped}
        downstream upon C{flowStopped}.
        """
        reasons = []
        class Ender(Tube):
            def stopped(self, reason):
                reasons.append(reason)
                yield "conclusion"

        self.ff.flowTo(series(Ender(), self.fd))
        self.assertEquals(reasons, [])
        self.assertEquals(self.fd.received, [])

        stopReason = Failure(ZeroDivisionError())

        self.ff.drain.flowStopped(stopReason)
        self.assertEquals(self.fd.received, ["conclusion"])
        self.assertEquals(len(reasons), 1)
        self.assertIdentical(reasons[0].type, ZeroDivisionError)

        self.assertEqual(self.fd.stopped, [stopReason])


    def test_tubeStoppedDeferredly(self):
        """
        The L{_Siphon} stops its L{Tube} and propagates C{flowStopped} downstream
        upon the completion of all L{Deferred}s returned from its L{Tube}'s
        C{stopped} implementation.
        """
        reasons = []
        conclusion = Deferred()
        class SlowEnder(Tube):
            def stopped(self, reason):
                reasons.append(reason)
                yield conclusion

        self.ff.flowTo(series(SlowEnder(), self.fd))
        self.assertEquals(reasons, [])
        self.assertEquals(self.fd.received, [])

        stopReason = Failure(ZeroDivisionError())

        self.ff.drain.flowStopped(stopReason)
        self.assertEquals(self.fd.received, [])
        self.assertEquals(len(reasons), 1)
        self.assertIdentical(reasons[0].type, ZeroDivisionError)
        self.assertEqual(self.fd.stopped, [])

        conclusion.callback("conclusion")
        # Now it's really done.
        self.assertEquals(self.fd.received, ["conclusion"])
        self.assertEqual(self.fd.stopped, [stopReason])


    def test_tubeFlowSwitching(self):
        """
        The L{_Siphon} of a L{Tube} sends on data to a newly specified L{IDrain}
        when its L{IDivertable.divert} method is called.
        """
        @implementer(IDivertable)
        class SwitchablePassthruTube(PassthruTube):
            def reassemble(self, data):
                return data

        sourceTube = SwitchablePassthruTube()
        fakeDrain = self.fd
        testCase = self

        class Switcher(Tube):
            def received(self, data):
                # Sanity check: this should be the only input ever received.
                testCase.assertEqual(data, "switch")
                sourceTube.divert(series(Switchee(), fakeDrain))
                return ()

        class Switchee(Tube):
            def received(self, data):
                yield "switched " + data

        firstDrain = series(sourceTube)

        self.ff.flowTo(firstDrain).flowTo(series(Switcher(), fakeDrain))
        self.ff.drain.receive("switch")
        self.ff.drain.receive("to switchee")
        self.assertEquals(fakeDrain.received, ["switched to switchee"])


    def test_tubeFlowSwitchingReassembly(self):
        """
        The L{_Siphon} of a L{Tube} sends on reassembled data - the return value
        of L{Tube.reassemble} to a newly specified L{Drain}; it is only called
        with un-consumed elements of data (those which have never been passed
        to C{receive}).
        """
        preSwitch = []
        @implementer(IDivertable)
        class ReassemblingTube(Tube):
            def received(self, datum):
                nonBorks = datum.split("BORK")
                return nonBorks

            def reassemble(self, data):
                for element in data:
                    yield '(bork was here)'
                    yield element

        class Switcher(Tube):
            def received(self, data):
                # Sanity check: this should be the only input ever received.
                preSwitch.append(data)
                sourceTube.divert(series(Switchee(), fakeDrain))
                return ()

        class Switchee(Tube):
            def received(self, data):
                yield "switched " + data

        sourceTube = ReassemblingTube()
        fakeDrain = self.fd
        firstDrain = series(sourceTube)
        self.ff.flowTo(firstDrain).flowTo(series(Switcher(), fakeDrain))

        self.ff.drain.receive("beforeBORKto switchee")

        self.assertEqual(preSwitch, ["before"])
        self.assertEqual(self.fd.received, ["switched (bork was here)",
                                            "switched to switchee"])


    def test_tubeFlowSwitchingControlsWhereOutputGoes(self):
        """
        If a siphon A with a tube Ap is flowing to a siphon B with a switchable
        tube Bp, Ap.received may switch B to a drain C, and C will receive any
        outputs produced by that received call; B (and Bp) will not.
        """
        class Switcher(Tube):
            def received(self, data):
                if data == "switch":
                    yield "switching"
                    destinationTube.divert(series(Switchee(), fakeDrain))
                    yield "switched"
                else:
                    yield data

        class Switchee(Tube):
            def received(self, data):
                yield "switched({})".format(data)

        fakeDrain = self.fd
        destinationTube = PassthruTube()
        # reassemble should not be called, so don't implement it
        directlyProvides(destinationTube, IDivertable)

        firstDrain = series(Switcher(), destinationTube)
        self.ff.flowTo(firstDrain).flowTo(fakeDrain)
        self.ff.drain.receive("before")
        self.ff.drain.receive("switch")
        self.ff.drain.receive("after")
        self.assertEqual(self.fd.received,
                         ["before", "switching",
                          "switched(switched)",
                          "switched(after)"])


    def test_initiallyEnthusiasticFountBecomesDisillusioned(self):
        """
        If an L{IFount} provider synchronously calls C{receive} on a
        L{_SiphonDrain}, whose corresponding L{_SiphonFount} is not flowing to an
        L{IDrain} yet, it will be synchronously paused with
        L{IFount.pauseFlow}; when that L{_SiphonFount} then flows to something
        else, the buffer will be unspooled.
        """
        ff = FakeFountWithBuffer()
        ff.bufferUp("something")
        ff.bufferUp("else")
        newDrain = series(PassthruTube())
        # Just making sure.
        self.assertEqual(ff.flowIsPaused, False)
        newFount = ff.flowTo(newDrain)
        self.assertEqual(ff.flowIsPaused, True)
        # "something" should have been un-buffered at this point.
        self.assertEqual(ff.buffer, ["else"])
        newFount.flowTo(self.fd)
        self.assertEqual(ff.buffer, [])
        self.assertEqual(ff.flowIsPaused, False)
        self.assertEqual(self.fd.received, ["something", "else"])


    def test_flowingFromNoneInitialNoOp(self):
        """
        L{_SiphonFount.flowTo}C{(None)} is a no-op when called before
        any other invocations of L{_SiphonFount.flowTo}.
        """
        siphonFount = self.ff.flowTo(self.siphonDrain)
        self.assertEquals(siphonFount.drain, None)
        siphonFount.flowTo(None)


    def test_tubeFlowSwitching_ReEntrantResumeReceive(self):
        """
        Switching a tube that is receiving data from a fount which
        synchronously produces some data to C{receive} will ... uh .. work.
        """
        class Switcher(Tube):
            def received(self, data):
                if data == "switch":
                    destinationTube.divert(series(Switchee(), fakeDrain))
                    return None
                else:
                    return [data]

        class Switchee(Tube):
            def received(self, data):
                yield "switched " + data

        fakeDrain = self.fd
        destinationTube = PassthruTube()
        # reassemble should not be called, so don't implement it
        directlyProvides(destinationTube, IDivertable)

        firstDrain = series(Switcher(), destinationTube)

        ff = FakeFountWithBuffer()
        ff.bufferUp("before")
        ff.bufferUp("switch")
        ff.bufferUp("after")
        ff.flowTo(firstDrain).flowTo(fakeDrain)
        self.assertEquals(self.fd.received, ["before", "switched after"])


    def test_tubeFlowSwitching_LotsOfStuffAtOnce(self):
        """
        If a tube returns a sequence of multiple things, great.
        """
        # TODO: docstring.
        @implementer(IDivertable)
        class SwitchablePassthruTube(PassthruTube):
            """
            Reassemble should not be called; don't implement it.
            """

        class Multiplier(Tube):
            def received(self, datums):
                return datums

        class Switcher(Tube):
            def received(self, data):
                if data == "switch":
                    destinationTube.divert(series(Switchee(), fakeDrain))
                    return None
                else:
                    return [data]

        class Switchee(Tube):
            def received(self, data):
                yield "switched " + data

        fakeDrain = self.fd
        destinationTube = SwitchablePassthruTube()

        firstDrain = series(Multiplier(), Switcher(), destinationTube)

        self.ff.flowTo(firstDrain).flowTo(fakeDrain)
        self.ff.drain.receive(["before", "switch", "after"])
        self.assertEquals(self.fd.received, ["before", "switched after"])


    def test_tubeYieldsFiredDeferred(self):
        """
        When a tube yields a fired L{Deferred} its result is synchronously
        delivered.
        """

        class SucceedingTube(Tube):
            def received(self, data):
                yield succeed(''.join(reversed(data)))

        fakeDrain = self.fd
        self.ff.flowTo(series(SucceedingTube())).flowTo(fakeDrain)
        self.ff.drain.receive("hello")
        self.assertEquals(self.fd.received, ["olleh"])


    def test_tubeYieldsUnfiredDeferred(self):
        """
        When a tube yields an unfired L{Deferred} its result is asynchronously
        delivered.
        """

        d = Deferred()

        class WaitingTube(Tube):
            def received(self, data):
                yield d

        fakeDrain = self.fd
        self.ff.flowTo(series(WaitingTube())).flowTo(fakeDrain)
        self.ff.drain.receive("ignored")
        self.assertEquals(self.fd.received, [])

        d.callback("hello")

        self.assertEquals(self.fd.received, ["hello"])


    def test_tubeYieldsMultipleDeferreds(self):
        """
        When a tube yields multiple deferreds their results should be delivered
        in order.
        """

        d = Deferred()

        class MultiDeferredTube(Tube):
            didYield = False
            def received(self, data):
                yield d
                MultiDeferredTube.didYield = True
                yield succeed("goodbye")

        fakeDrain = self.fd
        self.ff.flowTo(series(MultiDeferredTube())).flowTo(fakeDrain)
        self.ff.drain.receive("ignored")
        self.assertEquals(self.fd.received, [])

        d.callback("hello")

        self.assertEquals(self.fd.received, ["hello", "goodbye"])


    def test_tubeYieldedDeferredFiresWhileFlowIsPaused(self):
        """
        When a L{Tube} yields an L{Deferred} and that L{Deferred} fires when
        the L{_SiphonFount} is paused it should buffer it's result and deliver it
        when L{_SiphonFount.resumeFlow} is called.
        """
        d = Deferred()

        class DeferredTube(Tube):
            def received(self, data):
                yield d

        fakeDrain = self.fd
        self.ff.flowTo(series(DeferredTube())).flowTo(fakeDrain)
        self.ff.drain.receive("ignored")

        anPause = self.fd.fount.pauseFlow()

        d.callback("hello")
        self.assertEquals(self.fd.received, [])

        anPause.unpause()
        self.assertEquals(self.fd.received, ["hello"])


    def test_flowingFromFirst(self):
        """
        If L{_Siphon.flowingFrom} is called before L{_Siphon.flowTo}, the argument
        to L{_Siphon.flowTo} will immediately have its L{IDrain.flowingFrom}
        called.
        """
        self.ff.flowTo(self.siphonDrain).flowTo(self.fd)
        self.assertNotIdentical(self.fd.fount, None)


    def test_siphonReceiveCallsTubeReceived(self):
        """
        L{_SiphonDrain.receive} will call C{tube.received} and synthesize a fake
        "0.5" progress result if L{None} is returned.
        """
        got = []
        class ReceivingTube(Tube):
            def received(self, item):
                got.append(item)
        drain = series(ReceivingTube())
        drain.receive("sample item")
        self.assertEqual(got, ["sample item"])


    def test_flowFromTypeCheck(self):
        """
        L{_Siphon.flowingFrom} checks the type of its input.  If it doesn't match
        (both are specified explicitly, and they don't match).
        """
        class ToTube(Tube):
            inputType = IFakeInput
        siphonDrain = series(ToTube())
        self.failUnlessRaises(TypeError, self.ff.flowTo, siphonDrain)


    def test_receiveIterableDeliversDownstream(self):
        """
        When L{Tube.received} yields a value, L{_Siphon} will call L{receive} on
        its downstream drain.
        """
        self.ff.flowTo(series(PassthruTube())).flowTo(self.fd)
        self.ff.drain.receive(7)
        self.assertEquals(self.fd.received, [7])


    def test_receiveCallsTubeReceived(self):
        """
        L{_SiphonDrain.receive} will send its input to L{ITube.received} on its
        tube.
        """
        self.siphonDrain.receive("one-item")
        self.assertEquals(self.tube.allReceivedItems, ["one-item"])


    def test_flowToWillNotResumeFlowPausedInFlowingFrom(self):
        """
        L{_SiphonFount.flowTo} will not call L{_SiphonFount.resumeFlow} when
        it's L{IDrain} calls L{IFount.pauseFlow} in L{IDrain.flowingFrom}.
        """
        class PausingDrain(FakeDrain):
            def flowingFrom(self, fount):
                self.fount = fount
                self.fount.pauseFlow()

        self.ff.flowTo(self.siphonDrain).flowTo(PausingDrain())

        self.assertTrue(self.ff.flowIsPaused, "Upstream is not paused.")


    def test_reentrantFlowTo(self):
        """
        An L{IDrain} may call its argument's L{_SiphonFount.flowTo} method in
        L{IDrain.flowingFrom} and said fount will be flowing to the new drain.
        """
        test_fd = self.fd

        class ReflowingDrain(FakeDrain):
            def flowingFrom(self, fount):
                self.fount = fount
                self.fount.flowTo(test_fd)

        self.ff.flowTo(series(PassthruTube())).flowTo(ReflowingDrain())

        self.ff.drain.receive("hello")
        self.assertEqual(self.fd.received, ["hello"])


    def test_drainPausesFlowWhenPreviouslyPaused(self):
        """
        L{_SiphonDrain.flowingFrom} will pause its fount if its L{_SiphonFount} was
        previously paused.
        """
        newFF = FakeFount()

        myPause = self.ff.flowTo(self.siphonDrain).pauseFlow()
        newFF.flowTo(self.siphonDrain)

        self.assertTrue(newFF.flowIsPaused, "New upstream is not paused.")


    def test_siphonDrainRepr(self):
        """
        repr for L{_SiphonDrain} includes a reference to its tube.
        """

        self.assertEqual(repr(series(ReprTube())),
                         '<Drain for <Tube For Testing>>')


    def test_siphonFountRepr(self):
        """
        repr for L{_SiphonFount} includes a reference to its tube.
        """

        fount = FakeFount()

        self.assertEqual(repr(fount.flowTo(series(ReprTube()))),
                         '<Fount for <Tube For Testing>>')


    def test_siphonRepr(self):
        """
        repr for L{_Siphon} includes a reference to its tube.
        """

        tube = ReprTube()

        self.assertEqual(repr(_Siphon(tube)),
                         '<_Siphon for <Tube For Testing>>')


    def test_stopFlow(self):
        """
        L{_SiphonFount.stopFlow} stops the flow of its L{_Siphon}'s upstream
        fount.
        """
        self.ff.flowTo(series(self.siphonDrain, self.fd))
        self.assertEquals(self.ff.flowIsStopped, False)
        self.fd.fount.stopFlow()
        self.assertEquals(self.ff.flowIsStopped, True)


    def test_stopFlowBeforeFlowBegins(self):
        """
        L{_SiphonFount.stopFlow} will stop the flow of its L{_Siphon}'s
        upstream fount later, when it acquires one, if it's previously been
        stopped.
        """
        partially = series(self.siphonDrain, self.fd)
        self.fd.fount.stopFlow()
        self.ff.flowTo(partially)
        self.assertEquals(self.ff.flowIsStopped, True)


    def test_seriesSomething(self):
        """
        ...?
        """
        class Blub(Tube):
            def received(self, datum):
                yield "Blub"
                yield datum

        class Glub(Tube):
            def received(self, datum):
                yield "Glub"
                yield datum

        partially = series(Blub(), Glub())
        self.ff.flowTo(series(partially, self.fd))
        self.ff.drain.receive("hello")
        self.assertEqual(self.fd.received, ["Glub", "Blub", "Glub", "hello"])



class Reminders(TestCase):
    def test_startedRaises(self):
        """
        If L{ITube.started} raises an exception, the exception will be logged,
        the tube's fount will have L{IFount.stopFlow} called, and
        L{IDrain.flowStopped} will be called on the tube's downstream drain.
        """
        class UnstartableTube(Tube):
            def started(self):
                raise ZeroDivisionError

        ff = FakeFount()
        fd = FakeDrain()
        siphonDrain = series(UnstartableTube(), fd)
        ff.flowTo(siphonDrain)
        errors = self.flushLoggedErrors(ZeroDivisionError)
        self.assertEquals(len(errors), 1)
        self.assertEquals(ff.flowIsStopped, True)
        self.assertEquals(fd.stopped[0].type, ZeroDivisionError)


    def test_startedRaisesNoDrain(self):
        """
        If L{ITube.started} raises an exception, the exception will be logged,
        the tube's fount will have L{IFount.stopFlow} called, and
        L{IDrain.flowStopped} will be called on the tube's downstream drain.
        """
        class UnstartableTube(Tube):
            def started(self):
                raise ZeroDivisionError

        ff = FakeFount()
        siphonDrain = series(UnstartableTube())
        ff.flowTo(siphonDrain)
        errors = self.flushLoggedErrors(ZeroDivisionError)
        self.assertEquals(len(errors), 1)
        self.assertEquals(ff.flowIsStopped, True)


class Todo(TestCase):
    todo = "not just yet"

    def test_receivedRaises(self):
        """
        If L{ITube.received} raises an exception, the exception will be logged,
        and...
        """
        self.fail()


    def test_stoppedRaises(self):
        """
        If L{ITube.stopped} raises an exception, the exception will be logged,
        and...
        """
        self.fail()


    def test_iterOnResultRaises(self):
        """
        When the iterator returned from L{ITube}.
        """
        self.fail()


    def test_nextOnIteratorRaises(self):
        """
        If L{next} on the iterator returned from L{ITube.started} (OR OTHER)
        raises an exception, the exception will be logged, and...
        """
        self.fail()


    def test_deferredFromNextOnIteratorFails(self):
        """
        If L{next} on the iterator returned from L{ITube.started} (OR OTHER)
        returns a L{Deferred} which then fails, the failure will be logged,
        and...
        """
        self.fail()


    def test_reassembleRaises(self):
        """
        
        """
        self.fail()


    def test_setDivertRaises(self):
        """
        What if setting the C{divert} attribute of an L{IDivertable} raises?
        """
        self.fail()


    def test_setDivertToNoneRaises(self):
        """
        What if setting the C{divert} attribute of an L{IDivertable} to C{None}
        raises?
        """
        self.fail()
