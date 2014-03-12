
:LastChangedDate: $LastChangedDate$
:LastChangedRevision: $LastChangedRevision$
:LastChangedBy: $LastChangedBy$

An Introduction to Tubes
========================

Quick Description
-----------------

The :api:`twisted.tubes <twisted.tubes>` package implements a set of interfaces and a system for automatic propagation and manual management of data-agnostic flow-control, and composable processing of typed data.
However, unless you've had experience writing distributed systems before, that description might not make sense.
If that's the case, this next section should explain what :api:`twisted.tubes <twisted.tubes>` is, and why you would want to use it.

Long Description
----------------

All programs transform input to output.  Here's a simple example:

.. code-block:: python

    def process(input):
        output = something(input)
        return output

Writing programs like this is simple, but often useless, because this structure makes some assumptions which are rarely true.``process`` (and functions like it) assume that…

- …each input corresponds to only one output; in a *useful* program, one input may result in zero, one, or more outputs.
- …the input can be computed from stuff that's already in memory; in a *useful* program, you will need to load data from elsewhere.
- …simply returning the value is enough to send it on to the relevant output; in a *useful* program, one almost always needs to call a specific API to send output somewhere.
- …the system waiting for output is always ready to accept more; in a *useful* program, buffer sizes are limited, networks are slow, and you may have to wait before producing more output.


The ``twisted.tubes`` package exists to help you create *useful* programs, by providing both a structure that handles many of these issues when they can be addressed automatically, and tools to help you manage them when you need to deal with them manually.

For example, let's say you are processing a stream of bytes, containing messages that are delimited by marker, ``b"\r\n"`` (as many network protocols are).
If your program receives ``b"hello, world"`` , as an input, it should deliver zero outputs, since it hasn't seen a message boundary yet.
If it receives ``b"hello\r\nworld\r\n"`` , then it should deliver two outputs, ``b"hello"`` , and ``b"world"`` .
If your program receives ``b"hello\r"`` , and then *later* receives ``b"\nworld\r\n"`` , the *second* invocation needs to return two outputs.

Also, when dealing with streams of data from networks, it's common to want to send data somewhere as well as receiving it from somewhere.
Even if your all that your program is concerned with is converting a sequence bytes into a sequence of lines, it still needs to be aware of the fact that its output buffer may be full, and unprepared to receive any more lines.
For example, the line-splitting code above might be used in a proxy that relays output from a server with a very fast, low-latency uplink, to client computers on very slow high-latency networks.
The (fast) server's output will easily outpace a (slow) client's input, which means that if the line parser is going as fast as it can, lines will pile up in outgoing buffers while waiting to be sent out, and consume all of the proxy's memory.
When this happens, the line parsing program needs to tell *its* input to slow down, by indicating that it should no longer produce bytes, until the program consuming the line parser's output is ready again.

That's where the ``twisted.tubes`` package comes in; the rest of this document will teach you how to use the them.

.. note::
   
   If you've used Twisted before, you may notice that half of the line-splitting above is exactly what :api:`twisted.protocols.basic.LineReceiver <LineReceiver>`  does, and that there are lots of related classes that can do similar things for other message types.
   The other half is handled by :doc:`producers` .
   ``tubes``  is a *newer*  interface than those things, and you will find it somewhat improved.
   If you're writing new code, you should generally prefer to use ``tubes`` .
   
   There are three ways in which ``tubes``  is better than using producers, consumers, and the various ``XXXReceiver``  classes directly.
   
   
   #. ``twisted.tubes`` is *general purpose* .
      Whereas each ``FooReceiver`` class receives ``Foo`` s in its own way, ``tubes`` provides consistent, re-usable abstractions for sending and receiving.
   #. ``twisted.tubes`` *does not require subclassing* .
      The fact that different responsibilities live in different objects makes it easier to test and instrument them.
   #. ``twisted.tubes`` *handles flow control automatically* .
      The manual flow-control notifications provided by ``IProducer`` and ``IConsumer`` are still used internally in ``tubes`` to hook up to ``twisted.internet`` , but the interfaces defined in ``tubes`` itself are considerably more flexible, as they allow you to hook together chains of arbitrary length, as opposed to just getting buffer notifications for a single connection to a single object.

Tutorial
--------

Let's start with the simplest example; the simplest way to process any data is to avoid processing it entirely, to pass input straight on to output.
In a networking context, that means an echo server.
Here's a complete program which uses interfaces defined by ``twisted.tubes`` to send its input straight on to its output:

.. code-block:: python
    
    def echoFlow(fount, drain):
        return fount.flowTo(drain)

In the above example, ``echoFlow`` takes two things: a *fount* , or a source of data, and a *drain* , or a place where data eventually goes.
In the context of using tubes, we call such a function a "flow", because it establishes a flow of data from one place to another.
Most often, the arguments to such a function are the two parts of the same network connection. The fount represents data coming in over the connection, and the drain represents data going back out over that same connection.

Let's do exactly that, and call ``echoFlow`` with a real, network-facing ``fount`` and ``drain`` .

:download:`echotube.py <listings/tubes/echotube.py>`

.. literalinclude:: listings/tubes/echotube.py

This fully-functioning example (just run it with "``python echotube.py`` ") implements an echo server.
You can test it out with ``telnet localhost 4321`` .
(If you are on Windows, and do not have ``telnet`` installed, try running ``pkgmgr /iu:"TelnetClient"`` first; after waiting a few moments, ``telnet`` should be available.)

However, this example still performs no processing of the data that it is receiving.

To demonstrate both receiving and processing data, let's write a server that:

#. accepts an incoming connection
#. receives lines from that connection
#. interprets those lines as either:
   
   #. an integer, expressed as an ASCII decimal number, OR
   #. a command, which is ``SUM`` or ``PRODUCT`` 
   
#. executes the SUM and PRODUCT commands by adding or multiplying all of the numbers received since the last command (or the beginning of the connection)
#. responds to the SUM and PRODUCT commands by writing the result of the calculation out to the connection.

In order to implement this program, we will construct a *series* of objects which process the data; or, in the parlance of the ``tubes`` package, "``Pump`` s".
Each ``Pump`` in the ``series`` will be responsible for processing part of the data.

To demonstrate this, we'll build a little network-based calculator.
This program will take input, provided as a series of lines.
These lines will contain data (numbers) and instructions (arithmetic operations, in this case "SUM" and "PRODUCT" for addition and multiplication respectively) and produce output data (lines containing an equal sign and then results).

First we will create a pump that transforms arbitrary segments of a TCP stream into lines.
Then, a pump that will transform lines into a combination of integers and callables (functions that perform the work of the ``SUM`` and ``PRODUCT commands`` ), then from integers and callables into more integers - sums and products - from those integers into lines, and finally from those lines into CRLF-terminated segments of TCP data that are sent back out over the network.

Here's a sketch of the overall structure of such a program:

:download:`computube.py <listings/tubes/computube.py>`

.. literalinclude:: listings/tubes/computube.py

As with ``echoFlow`` , ``mathFlow`` takes a fount and a drain.
Rather than connecting them directly, it puts an object between them to process the data.
So what is ``dataProcessor`` and what does it return?  We need to write it, and it would look something like this:

:download:`dataproc.py <listings/tubes/dataproc.py>`

.. literalinclude:: listings/tubes/dataproc.py

To complete the example, we need to implement 3 classes, each of which is a Pump:

- ``LinesToIntegersOrCommands`` 
- ``CommandsAndIntegersToResultIntegers`` 
- ``IntegersToLines`` 

Let's implement them.  First, ``LinesToIntegersOrCommands`` receives lines and converts them into either integers, or functions, then delivers them on.

:download:`intparse.py <listings/tubes/intparse.py>`

.. literalinclude:: listings/tubes/intparse.py

Next, ``CommandsAndIntegersToResultIntegers`` takes that output

:download:`worker.py <listings/tubes/worker.py>`

.. literalinclude:: listings/tubes/worker.py

Next, ``IntegersToLines`` converts ``int`` objects into lines for output.

:download:`output.py <listings/tubes/output.py>`

.. literalinclude:: listings/tubes/output.py

Finally, we can put them all together by importing them in our original program, and hooking it up to a server just like ``echoFlow`` .

:download:`computube3.py <listings/tubes/computube3.py>`

.. literalinclude:: listings/tubes/computube3.py

A more interesting example might demonstrate the use of tubes to send data to another server.

:download:`portforward.py <listings/tubes/portforward.py>`

.. literalinclude:: listings/tubes/portforward.py

For each incoming connection on port ``6543`` , we create an outgoing connection to the echo server in our previous example.
When we have successfully connected to the echo server we connect our incoming ``listeningFount`` to our outgoing ``connectingDrain`` and our ``connectingFount`` to our ``listeningDrain`` .
This forwards all bytes from your ``telnet`` client to our echo server, and all bytes from our echo server to your client.

.. code-block:: python

    def echoFlow(fount, drain):
        return (fount.flowTo(Tube(stringToNetstring()))
                     .flowTo(drain))

:api:`twisted.tubes.itube.IFount.flowTo <flowTo>` can return a :api:`twisted.tube.itube.IFount <IFount>` so we can chain :api:`twisted.tubes.itube.IFount.flowTo <flowTo>` calls (in other words, call ``flowTo`` on the result of ``flowTo`` ) to construct a "flow".
In this case, ``.flowTo(Tube(stringToNetstring()))`` returns a new :api:`twisted.tubes.itube.IFount <IFount>` whose output will be `netstrings <http://cr.yp.to/proto/netstrings.txt>`_

.. note::

    If you're curious: specifically, :api:`twisted.tubes.itube.IFount.flowTo <flowTo>`  takes an :api:`twisted.tube.itube.IDrain <IDrain>` , and returns the result of that  :api:`twisted.tube.itube.IDrain <IDrain's>` :api:`twisted.tubes.itube.IDrain.flowingFrom <flowingFrom>`  method.
    This allows the ``Tube``  - which is the ``IDrain``  in this scenario, and therefore what knows what the output will be after it's processed it, to affect the return value of the previous ``IFount`` 's ``flowTo``  method.

We have now extended our simple ``echoFlow`` to add a length prefix to each chunk of its input before echoing it back to your client.
This demonstrates how you can manipulate data as it passes through a flow.
