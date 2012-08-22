#!/usr/bin/evn python

import os;
import time;
from threading import Event, Lock, Thread;
from SocketServer import TCPServer, ThreadingMixIn, StreamRequestHandler;
from SimpleHTTPServer import SimpleHTTPRequestHandler;

#HOST = 'localhost';
HOST = '';
ECHO_TREE_SCRIPT_SERVER_PORT = 5000;
ECHO_TREE_GET_PORT = 5001;
ECHO_TREE_NEW_ROOT_PORT = 5002;

TREE_EVENT_LISTEN_SCRIPT_NAME = "wordTreeListener.html";

class EchoTreeService(ThreadingMixIn, TCPServer):
    pass;

class EchoTreeNewTreeSubmissionService(ThreadingMixIn, TCPServer):
    pass

class EchoTreeClientScriptService(ThreadingMixIn, TCPServer):
    pass

class EchoTreeServiceHandler(SimpleHTTPRequestHandler):
    
    activeHandlerEvents = {};
    activeHandlersChangeLock = Lock();

    @staticmethod
    def notifyHandlersOfNewTree():
        for handlerKey in EchoTreeServiceHandler.activeHandlerEvents.keys():
            # Set one handler's new-tree-arrived event object:
            EchoTreeServiceHandler.activeHandlerEvents[handlerKey].set();
    
    @staticmethod
    def registerEchoTreeServer(echoTreeServiceHandlerObj):
        EchoTreeServiceHandler.activeHandlersChangeLock.acquire();
        EchoTreeServiceHandler.activeHandlerEvents[echoTreeServiceHandlerObj] = Event();
        EchoTreeServiceHandler.activeHandlersChangeLock.release();
        
    @staticmethod
    def unRegisterEchoTreeServer(echoTreeServiceHandlerObj):
        EchoTreeServiceHandler.activeHandlersChangeLock.acquire();        
        EchoTreeServiceHandler.activeHandlerEvents.pop(echoTreeServiceHandlerObj);
        EchoTreeServiceHandler.activeHandlersChangeLock.release();        
    
    def do_GET(self):
    
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
                    EchoTreeServiceHandler.activeHandlerEvents[self].clear();
                except KeyError:
                    # This server/client connection has failed, and the server
                    # unregistered itself.
                    return;
                
            
    def finish_request(self):
        try:
            StreamRequestHandler.finish_request();
        except:
            return;
    def finish(self):
        try:
            StreamRequestHandler.finish();
        except:
            return;
        
    def sendNewTree(self):
        try:
            EchoTreeUpdateListener.treeAccessLock.acquire();
            newTreeMsg = 'id: ' + self.constructMsgID() + '\n' + 'data: ' + EchoTreeUpdateListener.currentEchoTree + '\n'; 
            self.wfile.write(newTreeMsg);
            #self.wfile.write('id: ' + self.msgID + '\n');
            #self.wfile.write(EchoTreeUpdateListener.currentEchoTree + '\n');
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
        return self.connStartTime + '_' + str(self.msgID);        

class EchoTreeUpdateListener(StreamRequestHandler):
    
    treeAccessLock = Lock(); 
    currentEchoTree = 'Initial tree\n';
    
    def __init__(self, requestSocket, clientAddress, requestServerObj):
        StreamRequestHandler.__init__(self, requestSocket, clientAddress, requestServerObj);
        self.requestSocket = requestSocket;
        self.client_address = clientAddress;
        self.requestServerObj = requestServerObj;
        
    def handle(self):
        
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

class EchoTreeScriptRequestHandler(SimpleHTTPRequestHandler):
    
    def do_GET(request):
        scriptPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "scripts/" + TREE_EVENT_LISTEN_SCRIPT_NAME);
        request.send_response(200)
        reply =  "Content-type, text/html\n" +\
                 "Content-Length:%s\n" % os.path.getsize(scriptPath) +\
                 "Last-Modified:%s\n" % time.ctime(os.path.getmtime(scriptPath)) +\
                 "Cache-Control:no-cache\n" +\
                 "\n";

        with open(scriptPath) as fileFD:
            for line in fileFD:
                reply += line;
        request.wfile.write(reply);
                
class SocketServerThreadStarter(Thread):
    
    def __init__(self, socketServerClassName, host, port):
        super(SocketServerThreadStarter, self).__init__();
        self.socketServerClassName = socketServerClassName
        self.host = host
        self.port = port
        
        
    def run(self):
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
            print "Exception: %s" % `e`


if __name__ == '__main__':

    # Create the server for sending out new JSON trees
    SocketServerThreadStarter('EchoTreeService', HOST, ECHO_TREE_GET_PORT).start();
    # Create the service that accepts new JSON trees for distribution:
    SocketServerThreadStarter('EchoTreeNewTreeSubmissionService', HOST, ECHO_TREE_NEW_ROOT_PORT).start();
    # Create the service that serves out a small JS script that listens to the new-tree events:
    SocketServerThreadStarter('EchoTreeClientScriptService', HOST, ECHO_TREE_SCRIPT_SERVER_PORT).start();
    
    while 1:
        time.sleep(10);
