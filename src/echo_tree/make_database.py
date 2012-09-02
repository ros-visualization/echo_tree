#!/usr/bin/env python

import os;
import sys;
import string;
from collections import OrderedDict;

from optparse import OptionParser;

# TODO: write tokenize()
#       write dumpToDB()
#       write dumpToCSV()

EMAIL_SEPARATOR_PREFIX  = '#/*'
EMAIL_SEPARATOR_POSTFIX = '*/!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#^@\n'

EMAIL_FILE_CHUNK_SIZE   = 50000000 # 50MB

# ---------------------------------------------- Class DBCreator --------------------------

class DBCreator(object):

    DELETE_EMBEDDED_HEADERS = True
    
    def __init__(self, mailDirRoot, targetDBPath):
        self.mailDirRoot = mailDirRoot
        self.targetDBPath = targetDBPath
        self.emailFeeder = EmailMessageFeeder(mailDirRoot, fileContentCleaner=DBCreator.cleanEmailMessageFile);
        self.currentSentenceID = 0;

    def createInMemoryWordStats(self, numMessages=None):
        if numMessages is None:
            numMessages = self.emailFeeder.getNumMsgs();
        for msg in self.emailFeeder:
            tokenArray = self.tokenize(msg);
            for token in tokenArray:
                WordIndex.addPosting(WordPosting(token.word, token.sentenceID));

    def createCleanEmailCollection(self, outputDirPath, filePrefix='email', maxContent=None):
        '''
        Pulls all email messages through the EmailMessageFeeder, clearing 
        out the headers. Creates a series of EMAIL_FILE_CHUNCK_SIZE files
        with the resulting cleaned email messages. Within files messages are
        separated with a standard string that contains a serial number
        of the following email message. The string is constructed by
        concatenating EMAL_SEPARATOR_PREFIX<serialNumber>EMAIL_SEPARATOR_POSTFIX.
        Example:
        
        #*/123*/-------------------------#^@\n
        
        @param outputDirPath: path to where output files will be stored
        @type outputDirPath: string
        @param filePrefix: string prepended to each email file chunk, which is followed by a serial number. 
        @type filePrefix: string
        @param maxContent: limit to number of bytes worth of email messages to process.
        @type maxContent: int
        @raises: ValueError if output directory does not exist
        '''
        
        # Test whether the output dir exists before doing any work:
        if not os.path.isdir(outputDirPath):
            raise IOError("Path '%s' is not an existing directory." % outputDirPath);
        
        feeder = EmailMessageFeeder(self.mailDirRoot, fileContentCleaner=DBCreator.cleanEmailMessageFile);
        emailIndex = -1;
        currFileIndex = -1;
        currFileFD = None;
        # Force new file as first action in loop below:
        contentLenThisFile = EMAIL_FILE_CHUNK_SIZE + 1;
        # Keep track of overall bytes processed (across all output files):
        contentLenTotal = 0;
        for email in feeder:
            if contentLenThisFile >= EMAIL_FILE_CHUNK_SIZE:
                if currFileFD is not None:
                    currFileFD.close();
                currFileIndex += 1;
                currFilePath = os.path.join(outputDirPath, filePrefix + str(currFileIndex) + '.txt');
                try:
                    currFileFD = open(currFilePath, 'w');
                except IOError as e:
                    raise IOError("Cannot open new email file '%s' for writing: %s" % (currFilePath, `e`));
                contentLenThisFile = 0;     
                
            # Email separator:
            emailIndex += 1;
            sep = EMAIL_SEPARATOR_PREFIX + str(emailIndex) + EMAIL_SEPARATOR_POSTFIX;
            currFileFD.write(sep);
            currFileFD.write(email);
            currFileFD.write('\n');
            contentLenThisFile += len(email);
            contentLenTotal += len(email);
            if maxContent is not None and contentLenTotal >= maxContent:
                return;
             
    def tokenize(self, msg):
        '''
        Given an email message as a string, partition the msg into sentences,
        and return an array of Token instances, each containing one word, and
        a running sequence number of sentence ID integers. 
        @param msg: email message to tokenize
        @type msg: string
        @return: array of token instances.
        @rtype: [Token]
        '''
    
    @staticmethod
    def cleanEmailMessageFile(contentStr):
        '''
        Given one email message, remove its header, except for the content
        of the Subject line. If DBCreator.DELETE_EMBEDDED_HEADERS is True,
        goes through entire message and deletes lines starting with any of
        the common email headers.
        @param contentStr: content of email, including header
        @type contentStr: string
        @return: cleaned up email
        @rtype: string
        '''
        # Delete all but the subject in the header:
        subjLineIndx = string.find(contentStr, 'Subject:');
        if  subjLineIndx > -1:
            # Found start of 'Subject: ' field in header:
            # Pt to start of subject proper:
            subjLineIndx += 8; # len('Subject:')
            subjLineEndIndx = string.find(contentStr[subjLineIndx:], '\r\n');
            if subjLineEndIndx > -1:
                subjLine = contentStr[subjLineIndx:subjLineIndx + subjLineEndIndx].strip();
            else:
                subjLine = '';
        # Find end of header:
        headerEndIndx = string.find(contentStr, '\r\n\r\n');
        if headerEndIndx > -1:
            # Drop content to just after double \r\n:
            res = subjLine + '\n' + contentStr[headerEndIndx + 4:]; 
        else:
            res = contentStr;
            
        if DELETE_EMBEDDED_HEADERS:
            pass
        return res;
        
# ---------------------------------------------- Class Token  --------------------------

class Token(object):
    
    def __init__(self, word, sentenceID):
        self.word = word;
        self.sentenceID = sentenceID;
        
# ---------------------------------------------- Class LineFeeder --------------------------

class LineFeeder(object):
    
    def __init__(self, strWithNLs):
        self.content = strWithNLs;
        self.startIndex = 0;
        
    def __iter__(self):
        return self;
        
    def next(self): #@ReservedAssignment
        if self.startIndex < 0:
            raise StopIteration();
        
        startIndex = self.startIndex;
        try:
            self.startIndex = self.content.index('\n', startIndex) + len('\n');
            return self.content[startIndex:self.startIndex].strip();
        except ValueError:
            # No more newlines.
            finalLineStartIndex = self.startIndex;
            self.startIndex = -1; 
            return self.content[finalLineStartIndex:].strip();
        
    def hasNext(self):
        return self.startIndex >= 0;
    
# ---------------------------------------------- Class WordIndex --------------------------

class WordIndex(object):
    '''
    Entire word index. Holds a data structure like this:
    
    foo(2,set([0]))
    bar(5,set([1, 2, 3]))
    ----one(1,set([2]))
    ----two(2,set([3]))
    
    foo occurred twice, both times in sentence 0.
    bar occurred five times, in sentences 1,2,and 3
    bar was following by the word 'one' one time, in sentence 3
    bar was following by the word 'two' twice, in sentence 3
    '''
    
    allPostings = OrderedDict();
    
    @staticmethod
    def addPosting(wordPosting):
        '''
        If given word posting's root word is already in 
        the index, do nothing, and return False. Else add
        the new posting, and return True. For replacing an
        existing posting, use setPosting().
        @param wordPosting: posting to be added to the index.
        @type wordPosting: WordPosting
        @return: True if posting was added, False if the given posting's root word was already in the index.
        @rtype: boolean
        '''
        posting = WordIndex.getPosting(wordPosting) 
        if posting is None:
            WordIndex.allPostings[wordPosting.getRootWord()] = wordPosting;
            return True;
        # Word was already in index; bump its count:
        wordPosting.followingCount += 1;
        return False;
    
    @staticmethod
    def addPostings(wordPostingArr):
        '''
        Convenience method for adding multiple postings at once.
        @param wordPostingArr: array of postings to add.
        @type wordPostingArr: [WordPosting]
        '''
        for posting in wordPostingArr:
            WordIndex.addPosting(posting);

    @staticmethod
    def setPosting(wordPosting):
        '''
        Add posting, or replace an existing one.
        @param wordPosting: posting to add
        @type wordPosting: WordPosting
        '''
        WordIndex[wordPosting.getRootWord()] = wordPosting;
        
    @staticmethod
    def getPosting(wordOrWordPosting):
        '''
        Given either a string or a WordPosting, return the
        first-level posting in the index.
        @param wordOrWordPosting: word string or posting to retrieve
        @type wordOrWordPosting: {word | WordPosting}
        @return: WordPosting, or None, if not in index
        @rtype: {WordPosting}
        '''
        # Fake overloading a la Python: duck typing
        try:
            word = wordOrWordPosting.getRootWord();
        except AttributeError:
            word = wordOrWordPosting;
        try:
            return WordIndex.allPostings[word];
        except KeyError:
            return None; 

    @staticmethod
    def prettyPrint():
        '''
        Print indented ASCII tree of the index data structure
        '''
        for rootWord in WordIndex.allPostings.keys():
            print WordIndex.prettyPrintHelper(0, rootWord, WordIndex.allPostings[rootWord]);
        
    @staticmethod    
    def prettyPrintHelper(indentSpaces, word, posting):
        printout = ' '*indentSpaces + word + '(' + str(posting.followingCount) + ',' + str(posting.inSentence) + ')';
        for followKey in posting.wordPostingsDict.keys():
            printout += '\n' + WordIndex.prettyPrintHelper(indentSpaces + len(word), followKey, posting.wordPostingsDict[followKey]);
        return printout;

# ---------------------------------------------- Class WordPosting --------------------------


class WordPosting(object):
    '''
    A single posting. It contains the word itself, a set of sentence IDs in
    which the word occurred, an occurrence count, and a dictionary of follow-on
    words. May be used as an iterator: for followPosting in oneWordPosting:...
    '''
    
    def __init__(self, word, sentenceID):
        self.rootWord = word;
        self.wordPostingsDict = OrderedDict();
        self.inSentence = set([sentenceID]);
        self.followingCount = 1;
        self.wordPostingsIndex = -1;

    def getRootWord(self):
        return self.rootWord;
    
    def addFollowsWord(self, newFollowWordPosting, currentSentenceID):
        '''
        Given a posting that follows this word, and a sentence ID for context,
        add the new posting into the wordPostingsDict. Also add the sentence ID
        into the inSentence set.
        @param newFollowWordPosting: WordPosting to be added as a follower.
        @type newFollowWordPosting: WordPosting
        @param currentSentenceID: ID of sentence in which the new word followed.
        @type currentSentenceID: int
        '''
        try:
            # Does this follow-word already exist in this posting's follow-words?
            myFollowPosting = self.wordPostingsDict[newFollowWordPosting.getRootWord()];
            myFollowPosting.followingCount += 1;
        except KeyError:
            self.wordPostingsDict[newFollowWordPosting.getRootWord()] = newFollowWordPosting;
        self.inSentence.add(currentSentenceID);    
        
    def __iter__(self):
        self.rootWords = WordIndex.allPostings.keys();
        return self;
    
    def next(self): #@ReservedAssignment
        self.wordPostingsIndex += 1;
        if self.wordPostingsIndex >= len(self.rootWords):
            raise StopIteration;
        return WordIndex.allPostings[self.wordPostingsIndex];
        
        
# ---------------------------------------------- Class EmailMessageFeeder --------------------------        
        
class EmailMessageFeeder(object):
    '''
    Iterator that feeds one email message after the other to a caller.
    Input is the root directory of a file system tree at that contains
    files that each contain one email message. The optionally passed-in
    function fileContentCleaner is called with each email. 
    '''

    def __init__(self, mailDirRoot, fileContentCleaner=None):
        '''
        Create email message iterator.
        @param mailDirRoot: path to root directory of email files. 
        @type mailDirRoot: string
        @param fileContentCleaner: optional function to call with each email message as a string.
        @type fileContentCleaner: function
        '''
        self.mailDirRoot = mailDirRoot;
        self.fileContentCleaner = fileContentCleaner;
        self.currFileIndex = 0;
        self.filePaths = self.allFiles();
        self.numMsgs = len(self.filePaths);

    def getNumMsgs(self):
        return self.numMsgs;

    def allFiles(self):
        '''
        Return a list of fully qualified paths to each of the email files.
        @returns: list of file paths
        @rtype: [string]
        '''
        res = [];
        for root, fileDirList, fileNames in os.walk(self.mailDirRoot): #@UnusedVariable
            for fileName in fileNames:
                res.append(os.path.join(root,fileName));
        return res;

    def __iter__(self):
        return self;
    
    def next(self): #@ReservedAssignment
        '''
        @returns: Return the next file path string.
        @rtype: string
        '''
        fileContents = None;
        if self.currFileIndex >= len(self.filePaths):
            raise StopIteration;
        try:
            with open(self.filePaths[self.currFileIndex]) as fd:
                fileContents = fd.read();
            if self.fileContentCleaner is not None:
                fileContents = self.fileContentCleaner(fileContents);
        finally:
            self.currFileIndex += 1;
        return fileContents;
    
# --------------------------  Tests -----------------------

if __name__ == '__main__':
    
    parser = OptionParser();
    #parser.add_option("-d", "--dirIn", dest="emailsDirName");
    #parser.add_option("-o", "--fileOut", dest="dbOutFile");
    parser.add_option("-t", "--test", dest="testing");
    
    (options, args) = parser.parse_args()
    if (len(args) != 2) and testing is None:
        print "Usage: make_database { -t/--test | <emailDirPath> <mySqlOutFilePath>}";
        sys.exit();
        
    #print "Args: '%s'" % args
    #print "Options: '%s'" % options
    #sys.exit()
    
    emailsDir = args[0];
    dbOutFile = args[1];
    dbCreator = dbCreator(emailsDir, dbOutFile);
    
    
    import unittest
    import shutil
    
    testAll = False;
    
    class TestSuite(unittest.TestCase):
                
        def setUp(self):
            self.testTreeDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.join('Resources', 'TestDirTree'));
            self.dbCreator = DBCreator(self.testTreeDir, None);
            self.emailMsgFeederNoCleanup = EmailMessageFeeder(self.testTreeDir);
            
    
        @unittest.skipIf(not testAll, 'Skipping testCollectingFileNames')
        def testCollectingFileNames(self):
            result = self.emailMsgFeeder.allFiles();
            self.assertEquals(result,
                              [os.path.join(self.testTreeDir, 'topLevelFile.txt'),
                               os.path.join(self.testTreeDir, 'Level1', 'Level2', 'file1.txt'), 
                               os.path.join(self.testTreeDir, 'Level1', 'Level2', 'file2.txt')
                               ], 
                              "File path collection failed. Got %s" % str(result))
            
        @unittest.skipIf(not testAll, 'Skipping email feeder without message cleanup')            
        def testEmailFeederNoCleaner(self):
            for msg in self.emailMsgFeederNoCleanup:
                print msg;
        
        @unittest.skipIf(not testAll, 'Skipping email feeder with header removal')
        def testEmailFeederWithCleaner(self):
            msg = self.emailMsgFeederWithCleanup = EmailMessageFeeder(self.testTreeDir, DBCreator.cleanEmailMessageFile).next();
            self.assertEqual(msg, 
                            'Greg Thorse\nMy test message.\n', 
                            "Failed extraction of subject line and stripping of header. Got: '%s'" % msg);
                
        @unittest.skipIf(not testAll, 'Skipping word tree construction')
        def testBuildWordTree(self):
            root1 = 'foo';
            root2 = 'bar';
            followBar1 = 'one';
            followBar2 = 'two';
            root1Posting = WordPosting(root1, 0);
            WordIndex.addPosting(root1Posting);
            root2Posting = WordPosting(root2, 1);
            
            WordIndex.addPostings([root1Posting, root2Posting]);
            
            barPosting = WordIndex.getPosting('bar');
            barPosting.addFollowsWord(WordPosting(followBar1, 2),2);
            barPosting.addFollowsWord(WordPosting(followBar2, 3),3);
            # Follows again:
            barPosting.addFollowsWord(WordPosting(followBar2, 3),3);
            
            #print str(WordIndex.allPostings);
            WordIndex.prettyPrint();

        @unittest.skipIf(not testAll, 'Skipping word tree construction')
        def testLineFeeder(self):
            content = "This is\nmy poem.";
            feeder = LineFeeder(content);
            lineCounter = 0;
            for line in feeder:
                if lineCounter == 0:
                    self.assertEqual(line,
                                     'This is', 
                                     "Failed first line. Got: '%s'" % str(line));
                else:
                    lineCounter += 1;
                    self.assertEqual(line,
                                     'my poem.', 
                                     "Failed second line. Got: '%s'" % str(line));
        def testCreateCleanEmailCollection(self):
            outputDir = os.path.join(os.path.dirname(os.path.realpath(__file__)),'Resources/EmailCollectingTest');
            if os.path.isdir(outputDir):
                # For fresh test, remove the test target dir:
                shutil.rmtree(outputDir);
            try:
                self.dbCreator.createCleanEmailCollection(outputDir, 'emailTest');
                # Should have failed, because output directory doesn't exist:
                raise AssertionError("Should have seen IOError about output dir not existing.");
            except IOError:
                # Got expected exception:
                pass;
            
            os.mkdir(outputDir);
            self.dbCreator.createCleanEmailCollection(outputDir, 'emailTest');
                
            
    unittest.main();
    