#!/usr/bin/env python

import os
import sys
import re
import argparse
from collections import OrderedDict 


# TODO:
#   - [<sep>] gives a trailing sentence fragment of ']]' Fix.

class DBCreator(object):

    def __init__(self):
        pass

# ---------------------------------------------- Class Token  --------------------------

class Token():
    
    def __init__(self, emailID, sentenceID, word):
        self.word = word;
        self.sentenceID = sentenceID;
        self.emailID = emailID;
        
    def __repr__(self):
        return "<Token: email %d sentence %d word '%s'>" % (self.emailID, self.sentenceID, self.word);
        
    def __str__(self):
        return "<Token: email %d sentence %d word '%s'>" % (self.emailID, self.sentenceID, self.word);
        
# ---------------------------------------------- Class TokenFeeder --------------------------        

class TokenFeeder(object):
    '''
    Given one tokenized sentence, provide an iterator over the tokens.
    A tokenized sentence is a string of the form:
    [see, there, :, he, 'll, jump]. The next() method returns a 
    Token object, which contains the token's word, the sentenceID
    of the sentence in which the word occurred, and the emailID.
     
    The next() method therefore notices if a sentence includes the 
    email message separator.
    
    '''
   
    currSentenceID = 0;
    currMsgID = 0;
    sentenceFrontFrag = '';
    
    # Example email separator: The number is the ID of the next email:
    emailSep = "#, \/, \*, 5, \*, \/, !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!, #, ^, @"

	# Regular expressions for use in weeding out bad tokeans:
    allPunctuationTest = re.compile('[^,!;.?]') #  If None: only punctuation
    allCapsTest = re.compile('[a-z]')        # If None: only Upper case
    contractionTest = re.compile("[\s]*('[a-z]*)") # If non-None, then matchObj.group(1) is the contraction
	# Regexp pattern that matches <anything>#, \/, \*, 383869, \*, \/, !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!, #, ^, @<anything>
	# The three groups (parenthsized portions) capture, respectively everything before the opening '#',
	# the number (email ID of following msg), and everything after the closing '@':
    messageSepTest = re.compile("([^#]*)#, \\\\/, \\\\*.*[\\s]([0-9]*),.*, !{36}, #, \\^, @(.*)");
    
    #firstTokenExtract = "\[([^,\]]*)[,\]]";
    #secondPlusTokensExtract = ", (.*)[\]]|, ";
    tokenExtractPattern = re.compile(", ([\w]*)|\[([\w]*)");
    
    def __init__(self, sentence):
        self.sentence = sentence;
        self.fragNextMessage = None;
        self.nextMsgID = None;
        self.startOfSentence = True;
        
    def __iter__(self):
        return self;
    
    def next(self):
        '''
        Returns a Token instance holding the next token's 
        email message ID, its sentence ID, and the word. None
        if the sentence is exhausted.
        @return: Token instance with email ID, sentence ID, and the word.
        @rtype: Token
        '''
        
        # First token of sentence?
        if self.startOfSentence:
            self.startOfSentence = False;
            (sentenceTrail, nextEmailID, sentenceFrontEnd) = self.isNewMsgSep(self.sentence);
            if sentenceTrail is None:
                # Just an ordinary sentence:
                self.tokenIt = TokenFeeder.tokenExtractPattern.finditer(self.sentence);
            else:                
                # This sentence straddles two messages.
                # Remember the start of the next email message on the 
                # far side of the email message separator:
                self.fragNextMessage = sentenceFrontEnd;
                # The ID of the upcoming message: 
                self.nextMsgID = nextEmailID;
                self.tokenIt = TokenFeeder.tokenExtractPattern.finditer(sentenceTrail);
                
        try:
            matchObj = self.tokenIt.next();
        except StopIteration:
            # Sentence is exhausted. But do we already have the beginning
            # sentence of the next message in this sentence?:
            if self.fragNextMessage is not None:
                TokenFeeder.currMsgID = self.nextMsgID;
                self.tokenIt = TokenFeeder.tokenExtractPattern.finditer(self.fragNextMessage);
                self.fragNextMessage = None;
                TokenFeeder.currMsgID = self.nextMsgID;
                self.nextMsgID = None;
                try:
                    matchObj = self.tokenIt.next();
                except StopIteration:
                    return None;
            else:
                raise StopIteration;
        if matchObj is None:
           return None;
        
        # The regexp pattern creates two groups. The first is always None
        # for the first token in each sentence. The second is always None
        # for all other tokens (could build a better pattern, I'm sure):
        if matchObj.group(1) is None:
            word = matchObj.group(2)
        else:
            word = matchObj.group(1)
            
        # Clean tokens: eliminate empty strings, all-caps, and punctuation-only strings:
        word = self.cleanToken(word);
            
        return (Token(TokenFeeder.currMsgID, TokenFeeder.currSentenceID, word));
    

        
    def isContraction(self, token):
        matchObj = self.contractionTest.search(token);
        if matchObj is None:
            return None;
        else:
            try:
                return(matchObj.group(1))
            except IndexError:
                print "Warning: token '%s' thought to be contraction, but wasn't." % token;
                return None;

    def isPunctuationOnly(self, token):
        # Pattern: '[^,!;.?]'  # If None: only punctuation
        return not self.allPunctuationTest.search(token);
    
    def isCapsOnly(self, token):
        # Pattern: '[a-z]' # If None: only caps
        return not self.allCapsTest.search(token);
    
    def isNewMsgSep(self, sentence):
        '''
        Given an entire tokenized sentence, determines whether 
        it is an email message separator. If a message separator
        is found, method returns:
           1. Remnant of the previous message if separator was not at start of sentence
           2. Message ID (of the following email message)
           3. Remnant of sentence remaining after the string 
        
        Else, returns (None, None, None)
        Example sentence with separator embedded:
        
        [For, further, important, information, #, \/, \*, 383869, \*, \/, !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!, #, ^, @, Subject, :, Domestic] 
        "
        @param sentence: String of one tokenized sentence enclosed in brackets
        @type sentence: string
        '''
        
        matchObj = TokenFeeder.messageSepTest.search(sentence);
        if matchObj is None:
            return (None,None,None);
        else:
            # One of each pair of brackets below are not inserted. That's because they
            # come in as part of the matches:
            return ('[' + matchObj.group(1), matchObj.group(2), matchObj.group(3) + ']');
    
    def cleanToken(self, tokenStr):
        '''
        Given a single token, return None if the token is to be ignored,
        or otherwise the possibly modified token. Tokens to ignore consist
        of empty space, are all caps, or are only punctuation.
        @param tokenStr: Token to be examined
        @type tokenStr: string
        @return: new token, or None.
        @rtype: string
        '''
        
        # Empty string?
        tokenStr = tokenStr.strip();
        if len(tokenStr) == 0:
            return None;
        # Skip block-caps-only words (usually acronyms or callouts):
        if self.isPunctuationOnly(tokenStr) or self.isCapsOnly(tokenStr):
            return None;
        else:
            return tokenStr;
        
# ---------------------------------------------- Class LineFeeder --------------------------

class SentenceFeeder(object):
    '''
    Iterator over sentences of the entire email collection. Each call to next()
    returns one string of tokens enclosed in brackets, and separated by
    ' ,'. 
    
    Can operate once email files have been concatenated into chunk files,
    have been cleaned of headers and other clutter, and have been sentence
    segmented and tokenized. See notes.txt in package root. 
    '''
    
    def __init__(self, dirToTokens):
        '''
        Expects a directory containing chunk files of the form email12_NoHeads_Tokens.txt,
        with 12 being an example of a changing serial number. Each file is
        expected to contain a series of bracketed, comma-separated tokens. Each
        bracket pair delineates one sentence.
        
        Message boundaries are marked with this sequence of tokens: 
        
        [#, \/, \*, 383867, \*, \/, !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!, #, ^, @,...]
        
        where the number is the serial number of the following email.
         
        Method creates a sorted list of the chunk file names in self.sortedEmailChunks.

        @param dirToTokens: directory path to email token chunk files
        @type dirToTokens: string
        '''
        if not os.path.isdir(dirToTokens):
            raise ValueError("LineFeeder needs absolute path to directory with email token files.");
        # Get all the chunk file names:
        allTokenFiles = os.listdir(dirToTokens);
        # Count the .txt files:
        numTokenFiles = sum(1 for fileName in allTokenFiles if fileName.find('.txt') > -1);
        if numTokenFiles == 0:
            raise ValueError("No email files found in '%s'." % dirToTokens);
        self.sortedTokenChunks = [None] * numTokenFiles;
        # Email chunk files have names like email12_NoHeads.txt. Sort
        # them into sortedTokenChunks according to their embedded
        # serial number (in this case 12:
        for chunkFileName in allTokenFiles:
            # Skip non-text files.
            if chunkFileName.find('.txt') == -1:
                continue;
            serialNumStr = re.sub(r'[^0-9]', '', chunkFileName);
            try:
                serialNum = int(serialNumStr);
            except ValueError:
                raise ValueError("Could not extract email chunk file serial number from file name '%s'. Extraction got '%s" % (chunkFileName, serialNumStr));
            self.sortedTokenChunks[serialNum] = os.path.join(dirToTokens, chunkFileName);
        
        self.currFileIndex = 0;
        
        self.ingestOneTokenFile(); 

    def ingestOneTokenFile(self):
        if self.currFileIndex >= len(self.sortedTokenChunks):
            return False;
        with open(self.sortedTokenChunks[self.currFileIndex], 'r') as fd:
            content = fd.read();
        self.currFileIndex += 1;
        self.contentIndex = 0;
        self.currContent = content;
        # Loaded another chunk file:
        return True;
        
    def __iter__(self):
        return self;
        
    def next(self): #@ReservedAssignment
        
        startIndex = self.contentIndex;
        try:
            # Point past the next closing closing bracket:
            self.contentIndex = self.currContent.index(']', startIndex) + 1;
            return self.currContent[startIndex:self.contentIndex-1];
        except ValueError:
            # No more sentences in this chunk file. Get next one:
            ingestionWorked = self.ingestOneTokenFile();
            if not ingestionWorked:
                raise StopIteration();
            return self.next();
    
        
        
      
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
    A single posting. It contains:
        - the word itself, 
        - a set of sentence IDs in which the word occurred,
        - a set of message IDs in which the word occurred, 
        - a total occurrences count, and 
        - a dictionary of follow-on words. 
    May be used as an iterator: for followPosting in oneWordPosting:...
    '''
    
    def __init__(self, word, sentenceID, emailMsgID):
        self.rootWord = word;
        self.wordPostingsDict = OrderedDict();
        self.inSentence = set([sentenceID]);
        self.inEmail = set([emailMsgID]);
        self.followingCount = 1;
        self.wordPostingsIndex = -1;

    def getRootWord(self):
        return self.rootWord;
    
    def addFollowsWord(self, newFollowWordPosting, currentSentenceID, currentEmailID):
        '''
        Given a posting that follows this word, and a sentence ID for context,
        add the new posting into the wordPostingsDict. Also add the sentence ID
        into the inSentence set.
        @param newFollowWordPosting: WordPosting to be added as a follower.
        @type newFollowWordPosting: WordPosting
        @param currentSentenceID: ID of sentence in which the new word followed.
        @type currentSentenceID: int
        @param currentEmailID: ID of email message in which new word occurred.
        @type: currentEmailID: int
        '''
        try:
            # Does this follow-word already exist in this posting's follow-words?
            myFollowPosting = self.wordPostingsDict[newFollowWordPosting.getRootWord()];
            myFollowPosting.followingCount += 1;
        except KeyError:
            self.wordPostingsDict[newFollowWordPosting.getRootWord()] = newFollowWordPosting;
        self.inSentence.add(currentSentenceID);
        self.inEmail.add(currentEmailID);
        
    def __iter__(self):
        self.rootWords = WordIndex.allPostings.keys();
        return self;
    
    def next(self): #@ReservedAssignment
        self.wordPostingsIndex += 1;
        if self.wordPostingsIndex >= len(self.rootWords):
            raise StopIteration;
        return WordIndex.allPostings[self.wordPostingsIndex];
        
# -----------------------  Testing ------------------------

if __name__ == '__main__':
    
#******** This part above testing is just a copy from make_clean_email_files.
#         Update that when testing is done.
#    parser = argparse.ArgumentParser()
#    parser.add_argument("mailDirRoot", help="Root of dir tree with emails at leaves.");
    
#    parser.add_argument("-m", "--maxBytes", type=int,
#                        help="max number of bytes to process.");
#    parser.add_argument("-c", "--clearHeaders", action="store_true",
#                        help="flag to delete email headers.");
#    parser.add_argument("-d", "--delRawFiles", action="store_true",
#                        help="flag to delete raw email files if versions with no headers were created.");
#    parser.add_argument("-t", "--testing", action="store_true",
#                        help="flag to just run tests.");
#    
#    
#    args = parser.parse_args()    

#    emailOrganizer = EmailOrganizer(args.mailDirRoot, args.dbOutFile);
#    collectedEmailsDir = os.path.dirname(os.path.realpath(args.dbOutFile));
#    
#        
#    (numEmails, numBytes) = emailOrganizer.createEmailCollection(emailOrganizer.targetDBDir, 
#                                                            filePrefix='email', 
#                                                            maxContent=args.maxBytes, 
#                                                            deleteEmailHeaders=args.clearHeaders, 
#                                                            deleteFilesWithHeaders=args.delRawFiles);
#    
#    if numBytes < 1000000:
#        print 'Processed %d emails (%.3f KB)' % (numEmails, numBytes / 1000);
#    else:
#        print 'Processed %d emails (%.3f MB)' % (numEmails, numBytes / 1000000);
#    sys.exit();
    
    # ------------------------------------------------------------------------------------------
    # The -t or --test option was given to the script implementation. Do unittesting:
    
    import unittest
    import shutil
    
    testAll = False;
    
    class TestSuite(unittest.TestCase):
                
        def setUp(self):
            self.tokenChunkFilesDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Resources/EnronCollectionProcessed/EnronTokenized');
            self.sentenceFeeder = SentenceFeeder(self.tokenChunkFilesDir);

        @unittest.skipIf(not testAll, 'Skipping testIngest')
        def testIngest(self):
            self.sentenceFeeder.ingestOneTokenFile();
            print self.sentenceFeeder.currContent[0:300];

        def testTokenFeeder(self):
            sentence = "[foo]" 
            tokenFeeder = TokenFeeder(sentence);
            token = tokenFeeder.next();
            #print "MsgID: %d, SentenceID: %d, Word: %s" % (token.emailID, token.sentenceID, token.word);
            self.assertEqual(token.emailID, 0, "First msg id not zero: " + str(token.emailID));
            self.assertEqual(token.sentenceID, 0, "First sentence id not zero: " + str(token.sentenceID));
            self.assertEqual(token.word, 'foo', "First sentence word is not 'foo': " + str(token.word));
            
            sentence = "[foo, bar]";
            tokenFeeder = TokenFeeder(sentence);
            for i, token in enumerate(tokenFeeder):
                #print "MsgID: %d, SentenceID: %d, Word: %s" % (token.emailID, token.sentenceID, token.word);
                self.assertEqual(token.emailID, 0, "First msg id not zero: " + str(token.emailID));
                self.assertEqual(token.sentenceID, 0, "Sentence id of sentence %d bad : %d" % (i, token.sentenceID))
                if i == 0: 
                    self.assertEqual(token.word, 'foo', "First sentence word is not 'foo': " + str(token.word));
                else:
                    self.assertEqual(token.word, 'bar', "Second sentence word is not 'foo': " + str(token.word));
            
            sentence = "[]";
            tokenFeeder = TokenFeeder(sentence);
            for i, token in enumerate(tokenFeeder):
                if i == 0:
                    self.assertEqual(token.word, None, "First and only token out of an empty sentence should be None. Was '%s'" % token.word);
                    continue;
                self.fail("Received more than one token for an empty sentence: '%s' (i=%d)." % (str(token), i));
                
            sentence = "[%s]" % TokenFeeder.emailSep;
            tokenFeeder = TokenFeeder(sentence);
            for i, token in enumerate(tokenFeeder):
                if i == 0:
                    self.assertEqual(token.word, None, "First token should None for the (empty) sentence fragment before the sep. Was '%s'" % token.word);
                    continue;
                if i == 1:
                    self.assertEqual(token.word, None, "Second token should None for the (empty) sentence fragment after the sep. Was '%s'" % token.word);
             
            
    unittest.main();

