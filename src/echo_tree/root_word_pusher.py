#!/usr/bin/env python


import socket;

from echo_tree_server import ECHO_TREE_NEW_ROOT_PORT;
from echo_tree_server import NEW_TREE_SUBMISSION_URI_PATH;

class RootWordPusher(object):

    def __init__(self, serverHostNameOrIP, port=ECHO_TREE_NEW_ROOT_PORT):
        
        self.serverHostNameOrIP = serverHostNameOrIP;
        self.port = port;

    def pushEchoTreeToServer(self, rootWord):
        '''
        Attempts to connect to the Web server defined by the
        imported HOST and ECHO_TREE_NEW_ROOT_PORT. If successful,
        pushes the given JSON formatted tree to that server. The server will in turn
        push the new tree to any interested clients. It is not an
        error if the connection attempt to the Web server fails, 
        
        @param rootWord: new root word from which an EchoTree will be constructed.
        @type rootWord: string
        @return: None if the update to the EchoTree server succeeded, else an Exception object;
        '''
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
            sock.connect((self.serverHostNameOrIP, self.port));
            treeMsg = "POST " + NEW_TREE_SUBMISSION_URI_PATH + " HTTP/1.0\r\n" +\
                      "User-Agent: EchoTree_PushTool\r\n" +\
                      "Content-Type: application/json\r\n" +\
                      "Content-Length: " + str(len(rootWord)) + "\r\n" +\
                      "\r\n" +\
                      rootWord;
            sock.sendall(treeMsg);
            sock.close();
            return None
        except Exception as e:
            return e;

if __name__ == "__main__":
    pass;
    