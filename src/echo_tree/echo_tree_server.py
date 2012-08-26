#!/usr/bin/evn python

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
import time;
import socket;
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

DBPATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "Resources/testDb.db");

SCRIPT_REQUEST_URI_PATH = r"/request_echo_tree_script";
NEW_TREE_SUBMISSION_URI_PATH = r"/submit_new_echo_tree";
ECHO_TREE_SUBSCRIBE_PATH = "r/subscribe_to_echo_trees";

# Name of script to serve on ECHO_TREE_SCRIPT_SERVER_PORT. 
# Fixed script intended to subscribe to the EchoTree event server: 
TREE_EVENT_LISTEN_SCRIPT_NAME = "wordTreeListener.html";

# -----------------------------------------  Top Level Service Provider Classes --------------------

class EchoTreeService(tornado.websocket.WebSocketHandler):
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
        print "Browser at %s (%s) subscribing to EchoTrees." % (request.host, request.remote_ip);
        
        # Register this handler instance as wishing to hear
        # about new incoming EchoTrees:
        with EchoTreeService.activeHandlersChangeLock:
            EchoTreeService.activeHandlers.append(self);
        # Event that will be set when a new EchoTree arrives.
        # Thread NewEchoTreeWaitThread will wait for this event:
        self.newEchoTreeEvent = Event();
        
        # Go wait for new-tree updates:
        EchoTreeService.NewEchoTreeWaitThread(self).start();
    
    def open(self):
        with EchoTreeService.currentEchoTreeLock:
            # Deliver the current tree to the subscribing browser:
            try:
                self.write_message(EchoTreeService.currentEchoTree);
            except Exception as e:
                print "Error during send of current EchoTree to %s (%s) during initial subscription: %s" % (self.request.host, self.request.remote_ip, `e`);
        
    
    def on_message(self, message):
        '''
        We do not currently expect info flow from browser to this server.
        @param message: message arriving from the browser
        @type message: string
        '''
        pass
    
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
        print "Browser at %s (%s) now disconnected." % (self.request.host, self.request.remote_ip);
    
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
                    except Exception as e:
                        print "Error during send of new EchoTree to %s (%s)" % (self.handlerObj.request.host, self.handlerObj.request.remote_ip);
                self.handlerObj.newEchoTreeEvent.clear();
    
# -----------------------------------------  Class for submission of new EchoTrees ---------------    
    
    
class NewEchoTreeSubmissionService(HTTPServer):
    '''
    Service for submitting a new JSON encoded EchoTree.
    Uses WebSocket to receive new JSON encoded EchoTrees.
    '''
    
    wordExplorer = WordExplorer(DBPATH);
    
#    def __init__(self, requestHandler):
#        super(NewEchoTreeSubmissionService, self).__init__(requestHandler);
#        NewEchoTreeSubmissionService.wordExplorer = WordExplorer(DBPATH);
    
    @staticmethod
    def handle_request(request):
        '''
        Receives a new root word, from which it asks the WordExplorer to make
        a JSON word tree. Stores that new tree in EchoTreeService.currentEchoTree.
        Then raises NewEchoTreeSignal so that all EchoTree handlers' on_new_echo_tree()
        method gets called.
        @param request: incoming new EchoTree 
        @type request: HTTPRequest.HTTPRequest
        '''
        
        print "Receiving a new root word from %s (%s)..." % (request.host, request.remote_ip);
        rootWord = request.body;
        newJSONEchoTreeStr = NewEchoTreeSubmissionService.wordExplorer.makeJSONTree(NewEchoTreeSubmissionService.wordExplorer.makeWordTree(rootWord));
        
        # Store the new tree in the appropriate EchoTreeService class variable:
        with EchoTreeService.currentEchoTreeLock:
            EchoTreeService.currentEchoTree = newJSONEchoTreeStr;
            
        # Signal to the new-tree-arrived event pushers that a new
        # jsonTree has arrived, and they should push it to their clients:
        EchoTreeService.notifyInterestedParties();
        
    def on_close(self):
        pass
        
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
        scriptPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "scripts/" + TREE_EVENT_LISTEN_SCRIPT_NAME);
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
        self.socketServerClassName = socketServerClassName
        self.port = port
        
        
    def run(self):
        '''
        Use the service name to instantiate the proper service, passing in the
        proper helper class.
        '''
        try:
            if self.socketServerClassName == 'EchoTreeService':
                # Not used: done in main():
                print "Starting EchoTree server at port %d: pushes new word trees to all connecting clients." % self.port;
                application = tornado.web.Application([(r"/", EchoTreeService)]);
                application.listen(self.port);
                IOLoop.instance().start();
            elif self.socketServerClassName == 'NewEchoTreeSubmissionService':
                print "Starting EchoTree new tree submissions server %d: accepts word trees submitted from connecting clients." % self.port;
                http_server = NewEchoTreeSubmissionService(NewEchoTreeSubmissionService.handle_request);
                http_server.listen(self.port);
                IOLoop.instance().start()
            elif self.socketServerClassName == 'EchoTreeScriptRequestHandler':
                print "Starting EchoTree script server %d: Returns one script that listens to the new-tree events in the browser." % self.port;
                http_server = EchoTreeScriptRequestHandler(EchoTreeScriptRequestHandler.handle_request);
                http_server.listen(self.port);
                IOLoop.instance().start();
            else:
                raise ValueError("Service class %s is unknown." % self.socketServerClassName);
        except Exception, e:
            # Typically an exception is caught here that complains about 'socket in use'
            # Should avoid that by sensing busy socket and timing out:
#            if e.errno == 98:
#                print "Exception: %s. You need to try starting this service again. Socket busy condition will time out within 30 secs or so." % `e`
#            else:
#                print `e`;
            raise e;


if __name__ == '__main__':

    # Create the service that accepts new JSON trees for distribution:
    SocketServerThreadStarter('NewEchoTreeSubmissionService', ECHO_TREE_NEW_ROOT_PORT).start();
    
    # Create the service that serves out a small JS script that listens to the new-tree events:
    SocketServerThreadStarter('EchoTreeScriptRequestHandler', ECHO_TREE_SCRIPT_SERVER_PORT).start();
    
    print "Starting EchoTree server at port %s: pushes new word trees to all connecting clients." % "/subscribe_to_echo_trees";
    application = tornado.web.Application([(r"/subscribe_to_echo_trees", EchoTreeService),
                                           ]);
    application.listen(ECHO_TREE_GET_PORT);
    
    IOLoop.instance().start()                            

