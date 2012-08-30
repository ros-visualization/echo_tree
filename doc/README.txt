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

---------------

Example tree:
/*
 *
 * Building the following tree:
 *
  *            keyboard
 *                            shortcut
 *                                    lost
 *                                    woods
 *                            failure
 *                                    mode
 *                                    option
 *                            cleaner
 *                                    undocumented
 *                                    acidic
 * great      land
 *                            free
 *                                    potatoes
 *                                    wheeling
 *                            reform
 *                                    school
 *                                    attempt
 *                            dispute
 *                                    defendant
 *                                    allegations
 *            labor
 *                            movement
 *                                    free
 *                                    therapy
 *                            union
 *                                    concerned
 *                                    denied
 *                            relations
 *                                    bad
 *                                    visit
 *
 */ 

Corresponding JavaScript structure:

var myWord = new WordObj("great", [new WordObj("keyboard", [new WordObj("shortcut",
                                                                [new WordObj("lost", []),
                                                                 new WordObj("woods", [])]),
                                                            new WordObj("failure",
                                                                [new WordObj("mode", []),
                                                                 new WordObj("option", [])]),
                                                            new WordObj("cleaner",
                                                                [new WordObj("undocumented", []),
                                                                 new WordObj("acidic", [])])
                                                            ]),
                                   new WordObj("land",     [new WordObj("free",
                                                                [new WordObj("potatoes", []),
                                                                 new WordObj("wheeling", [])]),
                                                            new WordObj("reform",
                                                                [new WordObj("school", []),
                                                                 new WordObj("attempt", [])]),
                                                            new WordObj("dispute",
                                                                [new WordObj("defendant", []),
                                                                 new WordObj("allegations", [])])
                                                               ]),
                                   new WordObj("labor",    [new WordObj("movement",
                                                                [new WordObj("free", []),
                                                                 new WordObj("therapy", [])]),
                                                            new WordObj("union",
                                                                [new WordObj("concerned", []),
                                                                 new WordObj("denied", [])]),
                                                            new WordObj("relations",
                                                                [new WordObj("bad", []),
                                                                 new WordObj("visit", [])])
                                                               ])
                                    ]);

