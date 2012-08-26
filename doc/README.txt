1. Start the services that
     o Listen for words submitted to be turned into EchoTrees. 
       (HTTP, port 5002, POST).
     o Listen for browsers or programs that wish to be sent any new
       EchoTrees that result from submitted words. Many such
       interested parties may subscribe 
       (WebSockets, port 5001)
     o Optionally serve out a JavaScript that subscribes to EchoTrees
       and shows them in an HTML page. This is as a JavaScript
       example.
       (HTTP, port 5000, GET).

          src/echo_tree/echo_tree_server.py

2. Start a GUI tester. It lets you enter a word, hit a button, and see
   the browser windows running the example script change the displayed
   tree:
   
         src/echo_tree/tester_gui.py localhost

   Could be any other server.

OR Start the Command Line Interface (CLI) tester:

         src/echo_tree/tester_cli.py localhost <newRootWord>

