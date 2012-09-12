#!/usr/bin/env python

import os;
import sys;
import string;
import argparse;
from collections import OrderedDict;

# TODO: 
#       write dumpToDB()
#       write dumpToCSV()

EMAIL_SEPARATOR_PREFIX  = '#/*'
EMAIL_SEPARATOR_POSTFIX = '*/!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#^@\n'

EMAIL_FILE_CHUNK_SIZE   = 50000000 # 50MB

# ---------------------------------------------- Class DBCreator --------------------------

class EmailOrganizer(object):

    DELETE_EMBEDDED_HEADERS = True
    
    def __init__(self, mailDirRoot, targetDBPath):
        '''
        Prepare for creating the database.
        @param mailDirRoot: fully qualified directory of raw-email root directory 
        @type mailDirRoot: string
        @param targetDBPath: fully qualified filename of final SQLite database
        @type targetDBPath: string
        '''
        self.mailDirRoot = mailDirRoot
        self.targetDBPath = targetDBPath
        if os.path.isdir(targetDBPath):
            raise ValueError("Target db path must be a file name, not, for example, a directory");
        self.targetDBDir  = os.path.dirname(os.path.realpath(targetDBPath));
        #self.emailFeeder = EmailMessageFeeder(mailDirRoot, fileContentCleaner=EmailOrganizer.cleanEmailMessageFile);
        self.currentSentenceID = 0;

    def createInMemoryWordStats(self, numMessages=None):
        if numMessages is None:
            numMessages = self.emailFeeder.getNumMsgs();
        for msg in self.emailFeeder:
            tokenArray = self.tokenize(msg);
            for token in tokenArray:
                WordIndex.addPosting(WordPosting(token.word, token.sentenceID));


    def createEmailCollection(self, outputDirPath, filePrefix='email', maxContent=None, deleteEmailHeaders=True, deleteFilesWithHeaders=True):
        '''
        Pulls all email messages from a directory tree, using the EmailMessageFeeder class.
        Creates a series of EMAIL_FILE_CHUNCK_SIZE files with the resulting email messages. 
        Within these chunk files messages are separated with a standard string that contains 
        a serial number of the following email message. The string is constructed by
        concatenating EMAL_SEPARATOR_PREFIX<serialNumber>EMAIL_SEPARATOR_POSTFIX.
        Example:
        
        #*/123*/-------------------------#^@\n
        
        The chunks are named <filePrefix><serialNumber>.txt
        
        If deleteEmailHeaders is True, each chunk of email messages is scanned by
        Unix stream editor sed to remove email headers. A new chunk file is created
        and named <filePrefix><serialNumber>_NoHeads.txt.
        
        If deleteFilesWithHeaders is True, the initial, headers-containing chunk files
        are deleted after the headers are cleaned out. Else the files are retained.
        Note that this roughly doubles the size of the directory. 
        
        
        
        @param outputDirPath: path to where output files will be stored
        @type outputDirPath: string
        @param filePrefix: string prepended to each email file chunk, which is followed by a serial number. 
        @type filePrefix: string
        @param maxContent: limit to number of bytes worth of email messages to process.
        @type maxContent: int
        @param deleteEmailHeaders: if True, email headers will be deleted from the results
        @type deleteEmailHeaders: boolean
        @param deleteFilesWithHeaders: if True, and if headerless versions were created
                                       (i.e. deleteEmailHeaders was True), then the initial
                                       email files that include headers will be deleted.
        @type deleteFilesWithHeaders: boolean
        @return: number of email messages collected, and total number of bytes
        @rtype: (int,int)
        @raises ValueError if output directory does not exist
        '''
        
        # Test whether the output dir exists before doing any work:
        if not os.path.isdir(outputDirPath):
            raise IOError("Path '%s' is not an existing directory." % outputDirPath);
        
        # Print a progress message every REPORT_INTERVAL processed bytes:
        REPORT_INTERVAL = 50000;
        
        feeder = EmailMessageFeeder(self.mailDirRoot);
        if maxContent is not None:
            maxContent = int(maxContent);
        emailIndex = -1;
        currFileIndex = -1;
        currFileFD = None;
        latestProgressReportAt = 0;
        # Force new file as first action in loop below:
        contentLenThisFile = EMAIL_FILE_CHUNK_SIZE + 1;
        createdFilesList = [];
        # Keep track of overall bytes processed (across all output files):
        contentLenTotal = 0;
        try:
            for email in feeder:
                # Has this chunk file reached its max size:
                if contentLenThisFile >= EMAIL_FILE_CHUNK_SIZE:
                    # Close the just finished file:
                    if currFileFD is not None:
                        currFileFD.close();
                    currFileIndex += 1;
                    # Start a new chunk file:
                    currFilePath = os.path.join(outputDirPath, filePrefix + str(currFileIndex) + '.txt');
                    try:
                        currFileFD = open(currFilePath, 'w');
                        createdFilesList.append(currFilePath);
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
                if (contentLenTotal - latestProgressReportAt) > REPORT_INTERVAL:
                    print "Processed %.3f KB" % (contentLenTotal / 1000);
                    sys.stdout.flush();
                    latestProgressReportAt = contentLenTotal;
                if maxContent is not None and contentLenTotal >= maxContent:
                    return (emailIndex + 1, contentLenTotal);
        finally:
            currFileFD.close();
            # Are we to delete email headers?
            if deleteEmailHeaders:
                self.deleteEmailHeaders(outputDirPath);
                # Are we to delete the initial chunk files?
                if deleteFilesWithHeaders:
                    for initialChunkFile in createdFilesList:
                        try:
                            os.remove(initialChunkFile);
                        except IOError:
                            print "Could not delete initial chunk file '%s'" % initialChunkFile;
        return (emailIndex + 1, contentLenTotal);
             
    def deleteEmailHeaders(self, emailDirectory):
        '''
        Go through each file in the given directory, ignoring files with "_NoHeads" in the name.
        Run each file through the Unix sed editor to remove email headers. That script creates
        files with email headers removed. Those files are named the original names, with '_NoHeads'
        added.
        @param emailDirectory: directory containing files with any number of email messages.
        @type emailDirectory: string
        '''
        os.system(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../bash_scripts/removeEmailHeaders.sh %s %s' % (emailDirectory, '.*_NoHead.*')));        
        
# ---------------------------------------------- Class EmailMessageFeeder --------------------------        
        
class EmailMessageFeeder(object):
    '''
    Iterator that feeds one email message after the other to a caller.
    Input is the root directory of a file system tree containing
    files that each hold one email message. The optionally passed-in
    function fileContentCleaner is called with each email. 
    '''

    def __init__(self, mailDirRoot, fileContentCleaner=None):
        '''
        Create email message iterator. Every call to 'next()' will deliver a string
        that is one email message. Assumption is that files in mailDirRoot
        are email messages, one per file. 

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
    
# --------------------------  Main -----------------------

if __name__ == '__main__':
    

    parser = argparse.ArgumentParser()
    parser.add_argument("mailDirRoot", help="Root of dir tree with emails at leaves.");
    parser.add_argument("dbOutFile", help="Full path to final database file");
    
    parser.add_argument("-m", "--maxBytes", type=int,
                        help="max number of bytes to process.");
    parser.add_argument("-c", "--clearHeaders", action="store_true",
                        help="flag to delete email headers.");
    parser.add_argument("-d", "--delRawFiles", action="store_true",
                        help="flag to delete raw email files if versions with no headers were created.");
    
    
    args = parser.parse_args()    
#    print "Mail dir root: " + args.mailDirRoot;
#    print "dbOutFile: " + args.dbOutFile;
#    print "max num: " + str(args.maxBytes);
#    print "clear Header: " + str(args.clearHeaders);
#    print "delRawFiles: " + str(args.delRawFiles);

    if os.path.isdir(args.dbOutFile):
        print "Second argument must be a target SQLite database file name, not, for example, a directory.";
        sys.exit();

    emailOrganizer = EmailOrganizer(args.mailDirRoot, args.dbOutFile);
    collectedEmailsDir = os.path.dirname(os.path.realpath(args.dbOutFile));
    
        
    (numEmails, numBytes) = emailOrganizer.createEmailCollection(emailOrganizer.targetDBDir, 
                                                            filePrefix='email', 
                                                            maxContent=args.maxBytes, 
                                                            deleteEmailHeaders=args.clearHeaders, 
                                                            deleteFilesWithHeaders=args.delRawFiles);
    
    if numBytes < 1000000:
        print 'Processed %d emails (%.3f KB)' % (numEmails, numBytes / 1000);
    else:
        print 'Processed %d emails (%.3f MB)' % (numEmails, numBytes / 1000000);
    sys.exit();
    
    # ------------------------------------------------------------------------------------------
    # The -t or --test option was given to the script implementation. Do unittesting:
    
    import unittest
    import shutil
    
    testAll = False;
    
    class TestSuite(unittest.TestCase):
                
        def setUp(self):
            self.testTreeDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.join('Resources', 'TestDirTree'));
            self.emailOrganizer = EmailOrganizer(self.testTreeDir, None);
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
            msg = self.emailMsgFeederWithCleanup = EmailMessageFeeder(self.testTreeDir, EmailOrganizer.cleanEmailMessageFile).next();
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
                self.emailOrganizer.createCleanEmailCollection(outputDir, 'emailTest');
                # Should have failed, because output directory doesn't exist:
                raise AssertionError("Should have seen IOError about output dir not existing.");
            except IOError:
                # Got expected exception:
                pass;
            
            os.mkdir(outputDir);
            self.emailOrganizer.createCleanEmailCollection(outputDir, 'emailTest');
                
            
    unittest.main();
    