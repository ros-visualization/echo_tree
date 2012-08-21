#!/usr/bin/evn python

import os;
import time;
from threading import Event, Lock, Thread;
from SocketServer import TCPServer, ThreadingMixIn, StreamRequestHandler;

HOST = '';
ECHO_TREE_GET_PORT = 5000;
ECHO_TREE_NEW_ROOT_PORT = 5001;

class EchoTreeServiceHandler(StreamRequestHandler):
    
    activeHandlers = {};
    activeHandlersChangeLock = Lock();
    
    def __init__(self, requestSocket, clientAddress, requestServerObj):
        StreamRequestHandler.__init__(self, requestSocket, clientAddress, requestServerObj);
        self.requestSocket = requestSocket;
        self.client_address = clientAddress;
        self.requestServerObj = requestServerObj;

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
             
        # self.rfile is a file-like object created by the handler;
        # we can now use e.g. readline() instead of raw recv() calls
        # Get the HTTP request header:
        self.data = self.rfile.readlines();
        # Announce to remote browser that this will be a server event-sent
        # standing connection:
        self.wfile.write('Content-Type: text/event-stream\n' +\
                         'Content-Type: text/event-stream\n\n');
        # Our (optional) message ids will be <connectionStartDateTime>_<IDnum>
        self.connStartTime = time.strftime("%m%d%Y_%H:%M:%S");
        self.msgID = -1;
        # Send the currently active JSON tree as the first response:
        self.sendNewTree();
        while 1:
            # Wait for a new tree to arrive. The activeHandlers dict
            # contains our Event object:
            
            EchoTreeServiceHandler.activeHandlers[self].wait();
            
            # A new JSON tree arrived, and was installed by the 
            # EchoTreeUpdateListener. Lock access to that tree, and
            # send it to our browser:
            try:
                EchoTreeUpdateListener.treeAccessLock.acquire();
                self.wfile.write();
            except:
                # Connection back to the browser is bad. Clean up and get out.
                print "Connection to browser broken after message %s. Stopping service for that browser." % self.constructMsgID();
                return;
            finally:
                EchoTreeUpdateListener.treeAccessLock.release();
                EchoTreeServiceHandler.unRegisterEchoTreeServer(self);
            self.msgID += 1;
            self.wfile.write("id: " + self.constructMsgID() + '\n');
            EchoTreeUpdateListener.treeAccessLock.acquire();
            try:
                self.wfile.write('data: ' + EchoTreeUpdateListener.currentEchoTree);
            except:
                # Connection back to the browser is bad. Clean up and get out.
                print "Connection to browser broken while attempting to write message %s. Stopping service for that browser." % self.constructMsgID();
                return;
            finally:
                EchoTreeUpdateListener.treeAccessLock.release();
                EchoTreeServiceHandler.unRegisterEchoTreeServer(self);
        
    def constructMsgID(self):
        return self.connStartTime + '_' + str(self.msgID);        

class EchoTreeUpdateListener(StreamRequestHandler):
    
    treeAccessLock = Lock(); 
    currentEchoTree = 'null';
    
    def __init__(self, requestSocket, clientAddress, requestServerObj):
        StreamRequestHandler.__init__(self, requestSocket, clientAddress, requestServerObj);
        self.requestSocket = requestSocket;
        self.client_address = clientAddress;
        self.requestServerObj = requestServerObj;
        
    def handle(self):
        
        print "Starting a JSON reception service...";
        
        # self.rfile is a file-like object created by the handler;
        # we can now use e.g. readline() instead of raw recv() calls
        # Get the HTTP request header plus all of the tree:
        self.data = self.rfile.readlines();
        # Find the empty line that separates the HTTP header from
        # the JSON tree structure:
        while 1:
            dataLine = self.data.pop(0);
            if len(dataLine) == 0:
                # Found empty line after HTTP header:
                # Ensure that there is at least one more
                # line of data, which should be the start
                # of a JSON structure, if this update is
                # healthy:
                if len(self.data) == 0:
                    print "Bad echo tree update header. No data after header. Ignoring this update: %s" % str(self.data);
                    return;
                break;
            
        # Protect the tree structure variable from multiple access
        # while we update it:
        EchoTreeUpdateListener.treeAccessLock.acquire();
        EchoTreeUpdateListener.currentEchoTree = '';
        for jsonLine in self.data:
            EchoTreeUpdateListener.currentEchoTree.append(jsonLine);
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
    echoTreeServer = TCPServer((HOST, ECHO_TREE_GET_PORT), EchoTreeServiceHandler);
    # Create the service that accepts new JSON trees for distribution:
    echoTreeUpdateReceiver = TCPServer((HOST, ECHO_TREE_NEW_ROOT_PORT), EchoTreeUpdateListener); 

    # Activate the servers; they will keep running until you
    # interrupt the program with Ctrl-C
    SocketServerThreadStarter(echoTreeUpdateReceiver).run();
    SocketServerThreadStarter(echoTreeServer).run();
    
    while 1:
        time.sleep(10);
