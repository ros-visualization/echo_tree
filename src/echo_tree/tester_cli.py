#!/usr/bin/env python

import getopt;
import sys;
import traceback;

from root_word_pusher import RootWordPusher;

class WordPusherCLI(object):
    
    def __init__(self, serverAddr, rootWord, thePort=None):
    
        if thePort is None:
            pusher = RootWordPusher(serverAddr);
        else:
            pusher = RootWordPusher(serverAddr, port=thePort);
        result = pusher.pushEchoTreeToServer(rootWord);
        if result is not None:
            # Error:
            #print `result;`
            #print traceback.print_exc();
            raise result;
        else:
            print "Seems to have worked. Check whether your browsers updated their EchoTree.";

if __name__ == '__main__':    
    
    usage = "Usage: tester_cli [{-p | --port} echoTreeServerWordSubmissionPort] <echoTreeServerName> <rootWord>";
    
    thePort = None;
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hp:", ['help=', 'port=']);
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        print usage;
    if len(args) != 2:
        print usage;
        sys.exit(2);
    for option, arg in opts:
        if option == "-p" or option == '--port':
            thePort = arg;
        elif option in ("-h", "--help"):
            print usage;
            sys.exit()
        else:
            assert False, "unhandled option"

    serverAddr = args[0];
    rootWord = args[1].strip();
    if len(rootWord) == 0:
        print usage;
        sys.exit(2);
    WordPusherCLI(serverAddr, rootWord, thePort=thePort);
    
