
An Introduction to Tubes
========================

What Are Tubes?
---------------

The :api:`twisted.tubes <twisted.tubes>` package provides composable flow-control and data processing.

Flow-control is control over the source, destination, and rate of data being processed.
Tubes implements this in a type-agnostic way, meaning that a set of rules for controlling the flow of data can control that flow regardless of the type of that data, from raw streams of bytes to application-specific messages and back again.

Composable data processing refers to processing that can occur in independent units.
For example, the conversion of a continuous stream of bytes into a discrete sequence of messages can be implemented independently from the presentation of or reactions to those messages.
This allows for similar messages to be relayed in different formats and by different protocols, but be processed by the same code.

In this document, you will learn how to compose founts (places where data comes from), drains (places where data goes to), and tubes (things that modify data by converting inputs to outputs) to create flows.
You'll also learn how to create your own tubes to perform your own conversions of input to output.
By the end, you should be able to put a series of tubes onto the Internet as a server or a client.


Getting Connected: an Echo Server
---------------------------------

Let's start with an example.
The simplest way to process any data is to avoid processing it entirely, to pass input straight on to output.
On a network, that means an echo server as described in :rfc:`862`.
Here's a function which uses interfaces defined by ``twisted.tubes`` to send its input straight on to its output:

.. code-block:: python

    def echoFlow(fount, drain):
        return fount.flowTo(drain)

In the above example, ``echoFlow`` takes two things: a :api:`twisted.tubes.itube.IFount <fount>`, or a source of data, and a *drain* , or a place where data eventually goes.
We call such a function a "flow", because it establishes a flow of data from one place to another.
Most often, the arguments to such a function are the input from and the output to the same network connection.
The fount represents data coming in over the connection, and the drain represents data going back out over that same connection.

To *use* ``echoFlow`` as a server, we have to attach it to a listening :doc:`endpoint <endpoints>`.

Let's do exactly that, and call ``echoFlow`` with a real, network-facing ``fount`` and ``drain``.

:download:`echotube.py <listings/tubes/echotube.py>`

.. literalinclude:: listings/tubes/echotube.py

This fully-functioning example (just run it with "``python echotube.py``") implements an echo server.
By default, you can test it out by typing into it.

.. code-block:: console

    $ python echotube.py
    are you an echo server?
    are you an echo server?
    ^C

If you want to see this run on a network, you can give it an endpoint description.
For example, to run on TCP port 4321:

.. code-block:: console

    $ python echotube.py tcp:4321

and then in another command-line window:

.. code-block:: console

    $ telnet 127.0.0.1 4321
    Trying 127.0.0.1...
    Connected to localhost.
    Escape character is '^]'.
    are you an echo server?
    are you an echo server?
    ^]
    telnet> close
    Connection closed.

You can test it out with ``telnet localhost 4321``.

.. note::

    If you are on Windows, ``telnet`` is not installed by default.
    If you see an error message like:

    .. code-block:: console

        'telnet' is not recognized as an internal or external command,
        operable program or batch file.

    then you can install ``telnet`` by running the command

    .. code-block:: console

        C:\> dism /online /Enable-Feature /FeatureName:TelnetClient

    in an Administrator command-prompt first.

However, this example still performs no processing of the data that it is receiving.

Processing Some Data: A Networked Calculator
--------------------------------------------

To demonstrate both receiving and processing data, let's write a `reverse polish notation <https://en.wikipedia.org/wiki/Reverse_Polish_notation>`_ calculator for addition and multiplication.

Interacting with it should look like this:

.. code-block:: console

    > 3
    > 4
    > +
    = 7
    > 2
    > *
    = 14

In order to implement this program, we will construct a *series* of objects which process the data; specifically, we will create a :api:`twisted.tubes.series` of :api:`twisted.tubes.Tube`\s.
Each :api:`twisted.tubes.Tube` in the :api:`twisted.tubes.series` will be responsible for processing part of the data.

First we will create a tube that transforms a continuous stream of bytes into lines.
Then, a tube that will transform lines into a combination of numbers and operators (functions that perform the work of the ``"+"`` and ``"*"`` commands), then from numbers and operators into more numbers - sums and products - from those integers into lines, and finally from those lines into newline-terminated segments of data that are sent back out.

Here's a sketch of the overall structure of such a program:

:download:`computube.py <listings/tubes/computube.py>`

.. literalinclude:: listings/tubes/computube.py

As with ``echoFlow``, ``mathFlow`` takes a fount and a drain.
Rather than connecting them directly, it puts an object between them to process the data.
So what is ``dataProcessor`` and what does it return?  We need to write it, and it would look something like this:

:download:`dataproc.py <listings/tubes/dataproc.py>`

.. literalinclude:: listings/tubes/dataproc.py

To complete the example, we need to implement 3 classes, each of which is a Tube:

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

Finally, we can put them all together by importing them in our original program, and hooking it up to a server just like ``echoFlow``.

:download:`computube3.py <listings/tubes/computube3.py>`

.. literalinclude:: listings/tubes/computube3.py

A more interesting example might demonstrate the use of tubes to send data to another server.

:download:`portforward.py <listings/tubes/portforward.py>`

.. literalinclude:: listings/tubes/portforward.py

For each incoming connection on port ``6543``, we create an outgoing connection to the echo server in our previous example.
When we have successfully connected to the echo server we connect our incoming ``listeningFount`` to our outgoing ``connectingDrain`` and our ``connectingFount`` to our ``listeningDrain``.
This forwards all bytes from your ``telnet`` client to our echo server, and all bytes from our echo server to your client.

.. code-block:: python

    def echoFlow(fount, drain):
        return (fount.flowTo(Tube(stringToNetstring()))
                     .flowTo(drain))

:api:`twisted.tubes.itube.IFount.flowTo <flowTo>` can return a :api:`twisted.tube.itube.IFount <IFount>` so we can chain :api:`twisted.tubes.itube.IFount.flowTo <flowTo>` calls (in other words, call ``flowTo`` on the result of ``flowTo`` ) to construct a "flow".
In this case, ``.flowTo(Tube(stringToNetstring()))`` returns a new :api:`twisted.tubes.itube.IFount <IFount>` whose output will be `netstrings <http://cr.yp.to/proto/netstrings.txt>`_

.. note::

    If you're curious: specifically, :api:`twisted.tubes.itube.IFount.flowTo <flowTo>` takes an :api:`twisted.tube.itube.IDrain <IDrain>`, and returns the result of that  :api:`twisted.tube.itube.IDrain <IDrain>`’s :api:`twisted.tubes.itube.IDrain.flowingFrom <flowingFrom>` method.
    This allows the :api:`twisted.tube.Tube` - which is the ``IDrain`` in this scenario, and therefore what knows what the output will be after it's processed it, to affect the return value of the previous ``IFount``’s ``flowTo`` method.

We have now extended ``echoFlow`` to add a length prefix to each chunk of its input before echoing it back to your client.
This demonstrates how you can manipulate data as it passes through a flow.
