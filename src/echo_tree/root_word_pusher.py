#!/usr/bin/env python


import socket;

from echo_tree_server import NEW_TREE_SUBMISSION_URI_PATH;

class RootWordPusher(object):

    def __init__(self, serverHostNameOrIP, port=NEW_TREE_SUBMISSION_URI_PATH):
        
        self.serverHostNameOrIP = serverHostNameOrIP;
        self.port = port;

    def pushEchoTreeToServer(self, rootWord):
        '''
        Attempts to connect to the Web server defined by the
        imported HOST and NEW_TREE_SUBMISSION_URI_PATH. If successful,
        pushes the given JSON formatted tree to that server. The server will in turn
        push the new tree to any interested clients. It is not an
        error if the connection attempt to the Web server fails, 
        
        @param jsonTreeStr: EchoTree in JSON format
        @type jsonTreeStr: string
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
    