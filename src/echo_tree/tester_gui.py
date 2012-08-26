#!/usr/bin/env python

import sys;
import os;
import getopt;

from python_qt_binding import QtBindingHelper;
from QtGui import QApplication, QMainWindow, QWidget, QErrorMessage, QMessageBox;

from root_word_pusher import RootWordPusher;

GUI_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "QtCreatorFiles/echo_tree_push_tester/wordpushergui.ui");

# ---------------------------------------------  Class WordPusherGui ---------------------

class DialogService(QWidget):

    #----------------------------------
    # Initializer
    #--------------

    def __init__(self, parent=None):
        super(DialogService, self).__init__(parent);
        
        # All-purpose error popup message:
        # Used by self.showErrorMsgByErrorCode(<errorCode>), 
        # or self.showErrorMsg(<string>). Returns a
        # QErrorMessage without parent, but with QWindowFlags set
	    # properly to be a dialog popup box:
        self.errorMsgPopup = QErrorMessage.qtHandler();
       	# Re-parent the popup, retaining the window flags set
        # by the qtHandler:
        self.errorMsgPopup.setParent(parent, self.errorMsgPopup.windowFlags());
        #self.errorMsgPopup.setStyleSheet(SpeakEasyGUI.stylesheetAppBG);
        self.infoMsg = QMessageBox(parent=parent);
        #self.infoMsg.setStyleSheet(SpeakEasyGUI.stylesheetAppBG);
    
    #----------------------------------
    # showErrorMsg
    #--------------
    QErrorMessage
    def showErrorMsg(self,errMsg):
        '''
        Given a string, pop up an error dialog.
        @param errMsg: The message
        @type errMsg: string
        '''
        self.errorMsgPopup.showMessage(errMsg);
    
    #----------------------------------
    # showInfoMsg 
    #--------------

    def showInfoMsg(self, text):
        self.infoMsg.setText(text);
        self.infoMsg.exec_();        

# ---------------------------------------------  Class WordPusherGui ---------------------


class WordPusherGui(QMainWindow):
    
    def __init__(self, serverAddr, port=5002):
        super(WordPusherGui, self).__init__();
        
        self.serverAddr = serverAddr
        self.port = port
        
        self.pusher = RootWordPusher(self.serverAddr, port=self.port);
        
        self.ui = QtBindingHelper.loadUi(GUI_PATH, self);
        self.dialogService = DialogService(parent=self);
        self.connectWidgets();
        self.show();
        
    def connectWidgets(self):
        #self.wordField.textChanged.connect(self.wordFieldAction);
        self.submitButton.clicked.connect(self.submitAction);
        #self.treeDisplayField
    
    def submitAction(self):
        word = self.wordField.toPlainText();
        if len(word) == 0:
            self.dialogService.showErrorMsg("Enter a single word in the 'Word' textbox before clicking New Tree");
            return;
        result = self.pusher.pushEchoTreeToServer(word);
        if result is not None:
            # Error:
            self.dialogService.showErrorMsg(`result`);
        
    
if __name__ == '__main__':    
    
    usage = "Usage: tester_gui [{-p | --port} echoTreeServerWordSubmissionPort] <echoTreeServerName>";
    
    thePort = None;
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hp:", ['help=', 'port=']);
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        print usage;
    if len(args) != 1:
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
    
    app = QApplication(sys.argv);
    if thePort is not None:
        wordPusher = WordPusherGui(serverAddr, port=thePort);
    else:
        wordPusher = WordPusherGui(serverAddr);
    app.exec_();
    sys.exit();
    