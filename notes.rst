In the interst of making this branch more accessible to additional contributors, here are some thoughts that we have about what's going on right now.

Framing needs a ton of tests.
It hasn't changed a whole lot so documenting and testing this module might be a good way to get started.

``twisted.tubes.protocol`` is pretty well tested and roughly complete but could really use some docstrings, and improve the ones it has.
See for example the docstring for factoryFromFlow.

Similarly, ``twisted.tubes.fan`` is a pretty rough sketch, although it's a bit less self-evident what is going on there since it's not fully implemented.
(*Hopefully* it's straightforward, but let's not count on hope.)

There are a bunch of un-covered `__repr__`s, probably.

`twisted.tubes.tube.Diverter` could use some better docstrings, as could its helpers `_DrainingFount` and `_DrainingTube`.

We need a decorator for a function so that this:

.. code-block:: python

    class Foo(Tube):
        def receive(self, item):
            yield item

can become this:

.. code-block:: python

    @receiver
    def Foo(item):
        yield item

exactly how to map the name Foo or foo or whatever is left as an exercise for the reader, but defining things with just receive seems to be a thing to do all over the place.

Also subclassing Tube is dumb, it has the danger of becoming the new subclassing Protocol.
Also when we get new-new-style classes in Python it will be a problem.
Perhaps the decorator should just be @tube and it can detect whether it was given a class or a function.
It could also make sure you overrode at least one method, and that you named things right.

We need a QueueFount, something where you construct it with a maximum size, and then can push in a value and have it delivered onwards to its drain, or buffered if it is currently paused.
"push" is not the same as "receive" because QueueFount's contract should be to raise an exception if too many values are provided before the drain can consume them all, something that ``receive`` should never do because ``receive`` will pause the fount if there's too much traffic.
Raising an exception like this is a way of applying backpressure to a python program that is producing too much data rather than to a "real" data source.

QueueFount would be useful for testing applications that are built on top of tubes, so that a test could simply construct one and deliver it to the system under test without setting up I/O.
We presently need it in order to write simpler examples that explain how data flows work and operate on sample data without necessarily dealing with real sockets and transports in the first example.
Only the *last*, fully-integrated example really ought to have that sort of concern.
Having to explain all this stuff up front makes all the introductory prose very unweildy.

It would be nice to have a constructor or utility function that constructs a QueueFount from a list so you don't have to call "push" yourself a bunch of times.
