#!/usr/bin/evn python

import os;
import time;
from threading import Event, Lock, Thread;
from SocketServer import TCPServer, ThreadingMixIn, StreamRequestHandler;

HOST = 'localhost';
ECHO_TREE_GET_PORT = 5000;
ECHO_TREE_NEW_ROOT_PORT = 5001;

class EchoTreeService(ThreadingMixIn, TCPServer):
    pass;

class EchoTreeServiceHandler(StreamRequestHandler):
    
    activeHandlers = {};
    activeHandlersChangeLock = Lock();

    @staticmethod
    def notifyHandlersOfNewTree():
        for handlerKey in EchoTreeServiceHandler.activeHandlers.keys():
            # Set one handler's new-tree-arrived event object:
            EchoTreeServiceHandler.activeHandlers[handlerKey].set();
    
    @staticmethod
    def registerEchoTreeServer(echoTreeServiceHandlerObj):
        EchoTreeServiceHandler.activeHandlersChangeLock.acquire();
        EchoTreeServiceHandler.activeHandlers[echoTreeServiceHandlerObj] = Event();
        EchoTreeServiceHandler.activeHandlersChangeLock.release();
        
    @staticmethod
    def unRegisterEchoTreeServer(echoTreeServiceHandlerObj):
        EchoTreeServiceHandler.activeHandlersChangeLock.acquire();        
        EchoTreeServiceHandler.activeHandlers.pop(echoTreeServiceHandlerObj);
        EchoTreeServiceHandler.activeHandlersChangeLock.release();        
    
    def handle(self):
    
        print "Starting an event push service for " + str(self.client_address);
        
        # Register this new EchoTreeServiceHandler, so that it will
        # have an event set whenever a new JSON word tree is received by
        # the EchoTreeUpdateListener:
        EchoTreeServiceHandler.registerEchoTreeServer(self);
             
        # Announce to remote browser that this will be a server event-sent
        # standing connection:
        self.wfile.write('Content-Type: text/event-stream\n' +\
                         'Content-Type: text/event-stream\n\n');
        # Our (optional) message ids will be <connectionStartDateTime>_<IDnum>
        self.connStartTime = time.strftime("%m%d%Y_%H:%M:%S");
        self.msgID = 0;
        # Send the currently active JSON tree as the first response:
        if not self.sendNewTree():
            return;
        
        while 1:
            # Wait for a new tree to arrive. The activeHandlers dict
            # contains our Event object:
            
            EchoTreeServiceHandler.activeHandlers[self].wait();
            
            # A new JSON tree arrived, and was installed by the 
            # EchoTreeUpdateListener. Lock access to that tree, and
            # send it to our browser:
            self.msgID += 1;
            # Try to send the new tree. If send fails, the
            # client served by this thread is likely no longer
            # connected. Fine; just return, terminating this thread:
            if not self.sendNewTree():
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
            self.wfile.write("id: " + self.constructMsgID() + '\n');
            self.wfile.write(EchoTreeUpdateListener.currentEchoTree);
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

class SocketServerThreadStarter(Thread):
    
    def __init__(self, socketServerObj):
        super(SocketServerThreadStarter, self).__init__();
        self.socketServerObj = socketServerObj;
        
    def run(self):
        self.socketServerObj.serve_forever();


if __name__ == '__main__':

    # Create the server for sending out new JSON trees
    print "Starting EchoTree server: pushes new word trees to all clients connecting to %s." % str((HOST, ECHO_TREE_GET_PORT));
    echoTreeServer = EchoTreeService((HOST, ECHO_TREE_GET_PORT), EchoTreeServiceHandler);
    # Create the service that accepts new JSON trees for distribution:
    print "Starting EchoTree update server: accepts word trees submitted from clients connecting to %s." % str((HOST, ECHO_TREE_NEW_ROOT_PORT));
    echoTreeUpdateReceiver = TCPServer((HOST, ECHO_TREE_NEW_ROOT_PORT), EchoTreeUpdateListener); 

    # Activate the servers; they will keep running until you
    # interrupt the program with Ctrl-C
    SocketServerThreadStarter(echoTreeUpdateReceiver).start();
    SocketServerThreadStarter(echoTreeServer).start();
    
    while 1:
        time.sleep(10);
