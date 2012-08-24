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
from SocketServer import TCPServer, ThreadingMixIn, StreamRequestHandler;
from SimpleHTTPServer import SimpleHTTPRequestHandler;

HOST = '';
ECHO_TREE_SCRIPT_SERVER_PORT = 5000;
ECHO_TREE_GET_PORT = 5001;
ECHO_TREE_NEW_ROOT_PORT = 5002;

# Name of script to serve on ECHO_TREE_SCRIPT_SERVER_PORT. 
# Fixed script intended to subscribe to the EchoTree event server: 
TREE_EVENT_LISTEN_SCRIPT_NAME = "wordTreeListener.html";

# -----------------------------------------  Top Level Service Provider Classes --------------------

class EchoTreeService(ThreadingMixIn, TCPServer):
    '''
    Top level service for server-push updates to clients. 
    See class EchoTreeServiceHandler for code where incoming
    requests are handled. All other methods are in the superclasses.
    '''
    pass;

class EchoTreeNewTreeSubmissionService(ThreadingMixIn, TCPServer):
    '''
    Top level service for submitting a new JSON encoded EchoTree.
    See class EchoTreeUpdateListener for code where incoming
    requests are handled. All other methods are in the superclasses.
    '''

class EchoTreeClientScriptService(ThreadingMixIn, TCPServer):
    '''
    Top level service for handing out a single script that knows how to 
    initiate a new-EchoTree even stream from the EchoTreeService to the
    browser-based client that is pulling this script.
    See class EchoTreeScriptRequestHandler for code where incoming
    requests are handled. All other methods are in the superclasses.
    '''
# -----------------------------------------  Request Handler Class for new-EchoTree Service ---------------

class EchoTreeServiceHandler(SimpleHTTPRequestHandler):
    '''
    Handles details of calls to the EchoTreeService. Registers its
    need to be notified when new EchoTrees are submitted. The first
    request hangs each instance in the infinite do_GET() loop that
    overrides the superclass method. One instance of this class runs
    for each browser client that draws EchoTrees. Each instance runs
    in its own thread, and is notified of a new EchoTree having come in
    via an Event instance, which is stored in the class var 
    EchoTreeServiceHandler.activeHandlerEvents dictionary. Key is the
    object itself. 
    '''
    
    activeHandlerEvents = {};
    activeHandlersChangeLock = Lock();

    @staticmethod
    def notifyHandlersOfNewTree():
        '''
        Static method to call when a new EchoTree has arrived. The method
        runs through the EchoTreeServiceHandler.activeHandlerEvents events
        dict, and sets all events. 
        '''
        for handlerKey in EchoTreeServiceHandler.activeHandlerEvents.keys():
            # Set one handler's new-tree-arrived event object:
            EchoTreeServiceHandler.activeHandlerEvents[handlerKey].set();
    
    @staticmethod
    def registerEchoTreeServer(echoTreeServiceHandlerObj):
        '''
        Static method to call by any instance that wishes to be informed
        when a new EchoTree is submitted. After calling this method, that instance
        needs to hang on EchoTreeServiceHandler.activeHandlerEvents[<instance>].wait()/
        @param echoTreeServiceHandlerObj: Instance that wishes to be informed.
        @type echoTreeServiceHandlerObj: EchoTreeServiceHandler
        '''
        EchoTreeServiceHandler.activeHandlersChangeLock.acquire();
        EchoTreeServiceHandler.activeHandlerEvents[echoTreeServiceHandlerObj] = Event();
        EchoTreeServiceHandler.activeHandlersChangeLock.release();
        
    @staticmethod
    def unRegisterEchoTreeServer(echoTreeServiceHandlerObj):
        '''
        Static method used to unregister interest in being notified when
        new EchoTrees are submitted.
        @param echoTreeServiceHandlerObj:  Instance that wishes to be informed.
        @type echoTreeServiceHandlerObj: EchoTreeServiceHandler 
        '''
        EchoTreeServiceHandler.activeHandlersChangeLock.acquire();        
        EchoTreeServiceHandler.activeHandlerEvents.pop(echoTreeServiceHandlerObj);
        EchoTreeServiceHandler.activeHandlersChangeLock.release();        
    
    def do_GET(self):
        '''
        Called when an incoming HTTP GET request needs handling.
        Method overrides SimpleHTTPRequestHandler method. Writes back
        to the client browser a header indicating that an even stream is to follow.
        Then goes into infinite loop, waiting for EchoTree-submitted events.
        Following the initial header, such events are written to the open 
        connection in this form:
        id: <msgID>
        data: <JSON formatted EchoTree>
        '''
    
        print "Starting an event push service for " + str(self.client_address);
        
        # Register this new EchoTreeServiceHandler, so that it will
        # have an event set whenever a new JSON word tree is received by
        # the EchoTreeUpdateListener:
        EchoTreeServiceHandler.registerEchoTreeServer(self);
             
        # Announce to remote browser that this will be a server event-sent
        # standing connection:
        self.wfile.write('HTTP/1.1 200 OK\n' +\
                         'Content-Type: text/event-stream\n' +\
                         'Cache-Control: no-cache\n' +\
                         '\n');
        self.wfile.flush();
        # Our (optional) message ids will be <connectionStartDateTime>_<IDnum>
        self.connStartTime = time.strftime("%m%d%Y_%H:%M:%S");
        self.msgID = 0;
        # Send the currently active JSON tree as the first response:
        if not self.sendNewTree():
            return;
        
        while 1:
            # Wait for a new tree to arrive. The activeHandlerEvents dict
            # contains our Event object:

            try:            
                EchoTreeServiceHandler.activeHandlerEvents[self].wait();
            except KeyError:
                # This server/client connection has failed, and the server
                # unregistered itself.
                return;
            
            # A new JSON tree arrived, and was installed by the 
            # EchoTreeUpdateListener. Lock access to that tree, and
            # send it to our browser:
            self.msgID += 1;
            # Try to send the new tree. If send fails, the
            # client served by this thread is likely no longer
            # connected. Fine; just return, terminating this thread:
            try:
                if not self.sendNewTree():
                    return;
            finally:
                try:
                    # Indicate that we delivered the new tree to this client:
                    EchoTreeServiceHandler.activeHandlerEvents[self].clear();
                except KeyError:
                    # This server/client connection has failed, and the server
                    # unregistered itself.
                    return;
                
    def sendNewTree(self):
        '''
        Send one JSON encoded EchoTree across the open connection to the browser client.
        @return: True if event could be delivered, else return False.
        @rtype: boolean
        '''
        try:
            EchoTreeUpdateListener.treeAccessLock.acquire();
            # Create the two-line event message:
            newTreeMsg = 'id: ' + self.constructMsgID() + '\n' + 'data: ' + EchoTreeUpdateListener.currentEchoTree + '\n'; 
            self.wfile.write(newTreeMsg);
            self.wfile.flush();
            return True;
        except:
            # Connection back to the browser is bad. Clean up and get out.
            print "Connection to browser broken after message %s. Stopping service for that browser." % self.constructMsgID();
            EchoTreeServiceHandler.unRegisterEchoTreeServer(self);
            return False;
        finally:
            EchoTreeUpdateListener.treeAccessLock.release();
        
    def constructMsgID(self):
        '''
        Build a new message ID, concatenating the start time of this 
        instance's connection to a browser, and a serial number.
        '''
        return self.connStartTime + '_' + str(self.msgID);        

# -----------------------------------------  Request Handler Class for new incoming EchoTree submissions ---------------

class EchoTreeUpdateListener(StreamRequestHandler):
    '''
    Instances of this class service a single incoming new-EchoTree submission,
    then die. The latest EchoTree is always stored in the class variable currentEchoTree.
    Access to this variable must be protected via the Lock object stored in class variable
    treeAccessLock. 
    '''
    
    treeAccessLock = Lock(); 
    currentEchoTree = 'Initial tree\n';
    
    def __init__(self, requestSocket, clientAddress, requestServerObj):
        '''
        Creates one instance of the class, making the requesting socket,
        the submitting client's address, and the responsible instance of
        EchoTreeNewTreeSubmissionService.
        @param requestSocket: Socket through which the request arrived.
        @type requestSocket: Socket
        @param clientAddress: IP address of submitting machine as (<host>,<port>) (I *think*)
        @type clientAddress: (string, string)
        @param requestServerObj: instance of the EchoTreeNewTreeSubmissionService that received the submission. 
        @type requestServerObj: EchoTreeNewTreeSubmissionService
        '''
        StreamRequestHandler.__init__(self, requestSocket, clientAddress, requestServerObj);
        self.requestSocket = requestSocket;
        self.client_address = clientAddress;
        self.requestServerObj = requestServerObj;
        
    def handle(self):
        '''
        Reads the new incoming tree, storing it in EchoTreeUpdateListener.currentEchoTree.
        Then raises the Event objects of all EchoTreeServiceHandler instances
        that are hanging on an open connection with a browser.
        '''
        
        print "Receiving a new JSON EchoTree...";
        
        # self.rfile is a file-like object created by the handler;
        # we can now use e.g. readline() instead of raw recv() calls
        # Get the HTTP request header plus all of the tree:
        self.data = self.rfile.readlines();
        # Protect the tree structure variable from multiple access
        # while we update it:
        EchoTreeUpdateListener.treeAccessLock.acquire();
        EchoTreeUpdateListener.currentEchoTree = '';
        EchoTreeUpdateListener.currentEchoTree = ''.join(self.data);
        EchoTreeUpdateListener.treeAccessLock.release();
        # Signal to the new-tree-arrived event pushers that a new
        # jsonTree has arrived, and they should push it to their clients:
        EchoTreeServiceHandler.notifyHandlersOfNewTree();

# --------------------  Request Handler Class for browsers requesting the JavaScript that knows about event streams ---------------

class EchoTreeScriptRequestHandler(SimpleHTTPRequestHandler):
    '''
    Web service serving a single JavaScript containing HTML page.
    That page contains instructions for requesting an event stream for
    new EchoTree instances from this server.
    '''

    def do_GET(request):
        '''
        Hangles the HTTP GET request.
        @param request: instance holding information about the request
        @type request: ???
        '''
        # Path to the HTML page we serve. Should probably just load that once, but
        # this request is not frequent. 
        scriptPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "scripts/" + TREE_EVENT_LISTEN_SCRIPT_NAME);
        # Create the response and the HTML page string:
        request.send_response(200)
        reply =  "Content-type, text/html\n" +\
                 "Content-Length:%s\n" % os.path.getsize(scriptPath) +\
                 "Last-Modified:%s\n" % time.ctime(os.path.getmtime(scriptPath)) +\
                 "Access-Control-Allow-Origin: http://" + socket.getfqdn() + ":" + str(ECHO_TREE_GET_PORT) +\
                 "Cache-Control:no-cache\n" +\
                 "\n";
        # Add the HTML page to the header:
        with open(scriptPath) as fileFD:
            for line in fileFD:
                reply += line;
        request.wfile.write(reply);
        
# --------------------  Helper class for spawning the services in their own threads ---------------
                
class SocketServerThreadStarter(Thread):
    '''
    Used to fire up the three services each in its own thread.
    '''
    
    def __init__(self, socketServerClassName, host, port):
        '''
        Create one thread for one of the services to run in.
        @param socketServerClassName: Name of top level server class to run.
        @type socketServerClassName: string
        @param host: name of host to run on (should normally be empty string; maybe remove this parm)
        @type host: string
        @param port: port to listen on
        @type port: int
        '''
        super(SocketServerThreadStarter, self).__init__();
        self.socketServerClassName = socketServerClassName
        self.host = host
        self.port = port
        
        
    def run(self):
        '''
        Use the service name to instantiate the proper service, passing in the
        proper helper class.
        '''
        try:
            if self.socketServerClassName == 'EchoTreeService':
                print "Starting EchoTree server %s: pushes new word trees to all connecting clients." % str((self.host, self.port));
                EchoTreeService((self.host, self.port), EchoTreeServiceHandler).serve_forever();
            elif self.socketServerClassName == 'EchoTreeNewTreeSubmissionService':
                print "Starting EchoTree new tree submissions server %s: accepts word trees submitted from connecting clients." % str((self.host, self.port));            
                EchoTreeNewTreeSubmissionService((self.host, self.port), EchoTreeUpdateListener).serve_forever();
            elif self.socketServerClassName == 'EchoTreeClientScriptService':
                print "Starting EchoTree script server %s: Returns one script that listens to the new-tree events in the browser." % str((self.host, self.port));
                EchoTreeClientScriptService((self.host, self.port), EchoTreeScriptRequestHandler).serve_forever();
            else:
                raise ValueError("Service class %s is unknown." % self.socketServerClassName);
        except Exception, e:
            # Typically an exception is caught here that complains about 'socket in use'
            # Should avoid that by sensing busy socket and timing out:
            if e.errno == 98:
                print "Exception: %s. You need to try starting this service again. Socket busy condition will time out within 30 secs or so." % `e`
            else:
                print `e`;


if __name__ == '__main__':

    # Create the server for sending out new JSON trees
    SocketServerThreadStarter('EchoTreeService', HOST, ECHO_TREE_GET_PORT).start();
    # Create the service that accepts new JSON trees for distribution:
    SocketServerThreadStarter('EchoTreeNewTreeSubmissionService', HOST, ECHO_TREE_NEW_ROOT_PORT).start();
    # Create the service that serves out a small JS script that listens to the new-tree events:
    SocketServerThreadStarter('EchoTreeClientScriptService', HOST, ECHO_TREE_SCRIPT_SERVER_PORT).start();
    
    while 1:
        time.sleep(10);
