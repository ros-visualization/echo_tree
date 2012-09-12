#!/usr/bin/env python

'''
Module holding three servers:
   1. Web server serving a fixed html file containing JavaScript for starting an event stream to clients.
   2. Server for anyone uploading a new JSON formatted EchoTree.
   3. Server to which browser based clients subscribe as server-sent stream recipients.
      This server pushes new EchoTrees as they arrive via (2.). The subscription is initiated
      by the served JavaScript (for example.)
For ports, see constants below.
'''

import os;
import sys;
import time;
import socket;
import argparse;
import datetime;
from threading import Event, Lock, Thread;

import tornado;
from tornado.ioloop import IOLoop;
from tornado.websocket import WebSocketHandler;
from tornado.httpserver import HTTPServer;

from echo_tree import WordExplorer;

HOST = socket.getfqdn();
ECHO_TREE_SCRIPT_SERVER_PORT = 5000;
ECHO_TREE_GET_PORT = 5001;
ECHO_TREE_NEW_ROOT_PORT = 5002;

#DBPATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "Resources/testDb.db");
DBPATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "Resources/EnronCollectionProcessed/EnronDB/enronDB.db");

SCRIPT_REQUEST_URI_PATH = r"/request_echo_tree_script";
NEW_TREE_SUBMISSION_URI_PATH = r"/submit_new_echo_tree";
ECHO_TREE_SUBSCRIBE_PATH = "r/subscribe_to_echo_trees";

# Name of script to serve on ECHO_TREE_SCRIPT_SERVER_PORT. 
# Fixed script intended to subscribe to the EchoTree event server: 
TREE_EVENT_LISTEN_SCRIPT_NAME = "wordTreeListener.html";

# -----------------------------------------  Top Level Service Provider Classes --------------------

class EchoTreeService(WebSocketHandler):
    '''
    Handles pushing new EchoTrees to browsers who display them.
    Each instance handles one browser via a long-standing WebSocket
    connection.
    '''
    
    # Class-level list of handler instances: 
    activeHandlers = [];
    # Lock to make access to activeHanlders data struct thread safe:
    activeHandlersChangeLock = Lock();
    
    # Current JSON EchoTree string:
    currentEchoTree = "";
    # Lock for changing the current EchoTree:
    currentEchoTreeLock = Lock();
    
    # Log FD for logging. If None, calls to log() are ignored.
    # Else log to this FD (allowed to be sys.stdout for console:
    logFD = None;
    # If true, log to console, independently of logFD. If logFD is
    # provided (and not just sys.stdout), then logging occurs to
    # that FD *and* to the console. Else just to the concole:
    logToConsole = False;
    
    def __init__(self, application, request, **kwargs):
        '''
        Invoked when browser accesses this server via ws://...
        Register this handler instance in the handler list. 
        @param application: Application object that defines the collection of handlers.
        @type application: tornado.web.Application
        @param request: a request object holding details of the incoming request
        @type request:HTTPRequest.HTTPRequest
        @param kwargs: dict of additional parameters for operating this service.
        @type kwargs: dict
        '''
        super(EchoTreeService, self).__init__(application, request, **kwargs);
        self.request = request;
        EchoTreeService.log("Browser at %s (%s) subscribing to EchoTrees." % (request.host, request.remote_ip));
        
        # Register this handler instance as wishing to hear
        # about new incoming EchoTrees:
        with EchoTreeService.activeHandlersChangeLock:
            EchoTreeService.activeHandlers.append(self);
        # Event that will be set when a new EchoTree arrives.
        # Thread NewEchoTreeWaitThread will wait for this event:
        self.newEchoTreeEvent = Event();
        
        # Go wait for new-tree updates:
        EchoTreeService.NewEchoTreeWaitThread(self).start();
    
#    def subscribeToNewTrees(self, handler):
#        with EchoTreeService.activeHandlersChangeLock:
#            EchoTreeService.activeHandlers.append(handler);
    
    def open(self): #@ReservedAssignment
        '''
        Called by WebSocket/tornado when a client connects. Method must
        be named 'open'
        '''
        with EchoTreeService.currentEchoTreeLock:
            # Deliver the current tree to the subscribing browser:
            try:
                self.write_message(EchoTreeService.currentEchoTree);
            except Exception as e:
                EchoTreeService.log("Error during send of current EchoTree to %s (%s) during initial subscription: %s" % (self.request.host, self.request.remote_ip, `e`));
        
    
    def on_message(self, message):
        '''
        Connected browser requests a new word:
        @param message: message arriving from the browser
        @type message: string
        '''
        newRootWord = message.encode('utf-8');
        RootWordSubmissionService.triggerTreeComputationAndDistrib(newRootWord);
        EchoTreeService.log("New root word from connected browser: '%s'." % newRootWord);
    
    def on_close(self):
        '''
        Called when socket is closed. Remove this handler from
        the list of handlers.
        '''
        with EchoTreeService.activeHandlersChangeLock:
            try:
                EchoTreeService.activeHandlers.remove(self);
            except:
                pass
        EchoTreeService.log("Browser at %s (%s) now disconnected." % (self.request.host, self.request.remote_ip));

    @staticmethod
    def log(theStr, addTimestamp=True):
        if EchoTreeService.logFD is None and not EchoTreeService.logToConsole:
            return;
        if addTimestamp:
            timestamp = str(datetime.datetime.now());
            # Write timestamp to log file if appropriate:
            if EchoTreeService.logFD is not None:
                EchoTreeService.logFD.write(timestamp + ": ");
            # Write timestamp to console, if appropriate:
            if EchoTreeService.logToConsole and EchoTreeService.logFD != sys.stdout:
                sys.stdout.write(timestamp + ': ');
        if EchoTreeService.logFD is not None:
            EchoTreeService.logFD.write(theStr + '\n');
            EchoTreeService.logFD.flush();
        if EchoTreeService.logToConsole and EchoTreeService.logFD != sys.stdout:
            sys.stdout.write(theStr + '\n');
        
    
    @staticmethod
    def notifyInterestedParties():
        '''
        Called from other threads to set the new-EchoTree-arrived event flags
        for all instances of EchoTreeService.  
        '''
        with EchoTreeService.activeHandlersChangeLock:
            for handler in EchoTreeService.activeHandlers:
                handler.newEchoTreeEvent.set();
    
    class NewEchoTreeWaitThread(Thread):
        '''
        Thread that waits for a new EchoTree to be submitted.
        '''
        
        def __init__(self, handlerObj):
            '''
            Init thread
            @param handlerObj: instance of EchoTreeService.
            @type handlerObj: EchoTreeService.
            '''
            super(EchoTreeService.NewEchoTreeWaitThread, self).__init__();
            self.handlerObj = handlerObj
        
        def run(self):
            while 1:
                # Hang on new-EchoServer event:
                self.handlerObj.newEchoTreeEvent.wait();
                with EchoTreeService.currentEchoTreeLock:
                    # Deliver the new tree to the browser:
                    try:
                        self.handlerObj.write_message(EchoTreeService.currentEchoTree);
                    except Exception:
                        EchoTreeService.log("Error during send of new EchoTree to %s (%s)" % (self.handlerObj.request.host, self.handlerObj.request.remote_ip));
                self.handlerObj.newEchoTreeEvent.clear();
                with EchoTreeService.currentEchoTreeLock:
                    EchoTreeService.log(EchoTreeService.currentEchoTree);
    
# -----------------------------------------  Class for submission of new EchoTrees ---------------    
    
    
class RootWordSubmissionService(HTTPServer):
    '''
    Service for submitting a new root word. Service will
    compute a new tree, and cause it to be distributed to
    all connected browsers.
    '''
    
#    def __init__(self, requestHandler):
#        super(RootWordSubmissionService, self).__init__(requestHandler);
#        RootWordSubmissionService.wordExplorer = WordExplorer(DBPATH);
    
    @staticmethod
    def handle_request(request):
        '''
        Receives a new root word, from which it asks the WordExplorer to make
        a JSON word tree. Stores that new tree in EchoTreeService.currentEchoTree.
        Then sets the newWordEvent so that everyone waiting for that event
        gets called.
        @param request: incoming new EchoTree 
        @type request: HTTPRequest.HTTPRequest
        '''
        
        EchoTreeService.log("New root via HTTP; word '%s' from %s (%s)..." % (request.body, request.host, request.remote_ip));    
        RootWordSubmissionService.triggerTreeComputationAndDistrib(request.body);

    @staticmethod
    def triggerTreeComputationAndDistrib(newRootWord):
        if newRootWord == RootWordSubmissionService.TreeComputer.rootWord:
            return;
        RootWordSubmissionService.TreeComputer.rootWord = newRootWord;
        RootWordSubmissionService.TreeComputer.newWordEvent.set();
    
    def on_close(self):
        pass
    
    
    class TreeComputer(Thread):
        
        rootWord = None;
        newWordEvent = Event();
        keepRunning = True;
        singletonRunning = False;
        
        def __init__(self):
            super(RootWordSubmissionService.TreeComputer, self).__init__();
            if RootWordSubmissionService.TreeComputer.singletonRunning:
                raise RuntimeError("Only one TreeComputer instance may run per process.");
            RootWordSubmissionService.TreeComputer.singletonRunning = True;
        
        def stop(self):
            RootWordSubmissionService.TreeComputer.keepRunning = False;
        
        def run(self):
            self.wordExplorer = WordExplorer(DBPATH);
            while RootWordSubmissionService.TreeComputer.keepRunning:
                RootWordSubmissionService.TreeComputer.newWordEvent.wait();
                newJSONEchoTreeStr = self.wordExplorer.makeJSONTree(self.wordExplorer.makeWordTree(RootWordSubmissionService.TreeComputer.rootWord));
                
                # Store the new tree in the appropriate EchoTreeService class variable:
                with EchoTreeService.currentEchoTreeLock:
                    EchoTreeService.currentEchoTree = newJSONEchoTreeStr;
                    
                # Signal to the new-tree-arrived event pushers that a new
                # jsonTree has arrived, and they should push it to their clients:
                EchoTreeService.notifyInterestedParties();
                RootWordSubmissionService.TreeComputer.newWordEvent.clear();
                EchoTreeService.log(RootWordSubmissionService.TreeComputer.rootWord);
                EchoTreeService.log(newJSONEchoTreeStr);
        
# --------------------  Request Handler Class for browsers requesting the JavaScript that knows to open an EchoTreeService connection ---------------
class EchoTreeScriptRequestHandler(HTTPServer):
    '''
    Web service serving a single JavaScript containing HTML page.
    That page contains instructions for requesting an event stream for
    new EchoTree instances from this server.
    '''

#    def _execute(self, transforms):
#        pass;

    @staticmethod
    def handle_request(request):
        '''
        Hangles the HTTP GET request.
        @param request: instance holding information about the request
        @type request: ???
        '''
        # Path to the HTML page we serve. Should probably just load that once, but
        # this request is not frequent. 
        scriptPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../browser_scripts/" + TREE_EVENT_LISTEN_SCRIPT_NAME);
        # Create the response and the HTML page string:
        reply =  "HTTP/1.1 200 OK\r\n" +\
                 "Content-type, text/html\r\n" +\
                 "Content-Length:%s\r\n" % os.path.getsize(scriptPath) +\
                 "Last-Modified:%s\r\n" % time.ctime(os.path.getmtime(scriptPath)) +\
                 "\r\n";
        # Add the HTML page to the header:
        with open(scriptPath) as fileFD:
            for line in fileFD:
                reply += line;
        request.write(reply);
        request.finish();
        
# --------------------  Helper class for spawning the services in their own threads ---------------
                
class SocketServerThreadStarter(Thread):
    '''
    Used to fire up the three services each in its own thread.
    '''
    
    def __init__(self, socketServerClassName, port):
        '''
        Create one thread for one of the services to run in.
        @param socketServerClassName: Name of top level server class to run.
        @type socketServerClassName: string
        @param port: port to listen on
        @type port: int
        '''
        super(SocketServerThreadStarter, self).__init__();
        self.socketServerClassName = socketServerClassName;
        self.port = port;
        self.ioLoop = None;

    def stop(self):
        self.ioLoop.stop();
       
    def run(self):
        '''
        Use the service name to instantiate the proper service, passing in the
        proper helper class.
        '''
        super(SocketServerThreadStarter, self).run();
        try:
            if  self.socketServerClassName == 'RootWordSubmissionService':
                EchoTreeService.log("Starting EchoTree new tree submissions server %d: accepts word trees submitted from connecting clients." % self.port);
                http_server = RootWordSubmissionService(RootWordSubmissionService.handle_request);
                http_server.listen(self.port);
                self.ioLoop = IOLoop();
                self.ioLoop.start();
                self.ioLoop.close(all_fds=True);
                return;
            elif self.socketServerClassName == 'EchoTreeScriptRequestHandler':
                EchoTreeService.log("Starting EchoTree script server %d: Returns one script that listens to the new-tree events in the browser." % self.port);
                http_server = EchoTreeScriptRequestHandler(EchoTreeScriptRequestHandler.handle_request);
                http_server.listen(self.port);
                self.ioLoop = IOLoop();
                self.ioLoop.start();
                self.ioLoop.close(all_fds=True);
                return;
            else:
                raise ValueError("Service class %s is unknown." % self.socketServerClassName);
        except Exception, e:
            # Typically an exception is caught here that complains about 'socket in use'
            # Should avoid that by sensing busy socket and timing out:
#            if e.errno == 98:
#                print "Exception: %s. You need to try starting this service again. Socket busy condition will time out within 30 secs or so." % `e`
#            else:
#                print `e`;
            #raise e;
            pass
        finally:
            if self.ioLoop is not None and self.ioLoop.running():
                self.ioLoop.stop();
                return;


if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog='echo_tree_server')
    parser.add_argument("-l", "--logFile, help=fully qualified log file name. Default: no logging.", dest='logFile');
    parser.add_argument("-v", "--verbose, help=print operational info to console.", 
                        dest='verbose',
                        action='store_true');
    
    
    args = parser.parse_args();
    if args.logFile is not None:
        try:
            EchoTreeService.logFD = open(args.logFile, 'w');
        except IOError, e:
            print "Cannot open log file '%s' for writing. Server not started." % args.logFile;
            sys.exit();
    
    if args.verbose:
        EchoTreeService.logToConsole = True;

    # Create the service that accepts new words, and distributes the corresponding
    # JSON tree to all connected browsers:
    EchoTreeService.log('Starting listener for new root words via HTTP at port %d' % ECHO_TREE_NEW_ROOT_PORT);
    rootWordAcceptor = SocketServerThreadStarter('RootWordSubmissionService', ECHO_TREE_NEW_ROOT_PORT); 
    rootWordAcceptor.start();
    
    # Create the service that serves out a small JS script that listens to the new-tree events:
    EchoTreeService.log('Starting EchoTree script server at port %d' % ECHO_TREE_SCRIPT_SERVER_PORT);
    scriptServer = SocketServerThreadStarter('EchoTreeScriptRequestHandler', ECHO_TREE_SCRIPT_SERVER_PORT); 
    scriptServer.start();
    
    EchoTreeService.log("Starting TreeComputer thread: computes new tree from Web-submitted words, using echo_tree.");
    treeComputerThread = RootWordSubmissionService.TreeComputer(); 
    treeComputerThread.start();    
    
    EchoTreeService.log("Starting EchoTree server at port %s: pushes new word trees to all connecting clients." % "/subscribe_to_echo_trees");
    application = tornado.web.Application([(r"/subscribe_to_echo_trees", EchoTreeService),
                                           ]);
                                           
    application.listen(ECHO_TREE_GET_PORT);
    try:
        ioLoop = IOLoop.instance();
        try:
            ioLoop.start()
            ioLoop.close(all_fds=True);
        except Exception, e:
            ioLoop.stop();
            if e.__class__ == KeyboardInterrupt:
                raise e;
    except KeyboardInterrupt:
        EchoTreeService.log("Stopping EchoTree servers...");
        if ioLoop.running():
            ioLoop.stop();
        rootWordAcceptor.stop();
        scriptServer.stop();
        treeComputerThread.stop();
        EchoTreeService.log("EchoTree servers stopped.");
        if EchoTreeService.logFD is not None:
            EchoTreeService.logFD.close();
        os._exit(0);
        