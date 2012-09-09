#!/usr/bin/env python

import os
import sys
import re
import argparse
from collections import OrderedDict 


# TODO:

STOPWORDS = ['the', 'of', 'and', 'to', 'in', 'I', 'that', 'was', 'his', 'he', 'it', 'is', 'for',
             'as', 'had', 'on', 'at', 'by', 'this', 'are', 'an', 'has', 'its', 'a', 'these', 'mr',
             'you'];

class DBCreator(object):

    def __init__(self, dirToTokens, outFileName=None, maxNumSentences=None, logFile=None):
        
        
        if not os.path.isdir(dirToTokens):
            raise IOError("Directory to token chunk files must exist, and must contain files.");
        if maxNumSentences is not None and maxNumSentences <= 0:
            raise ValueError("Maximum number of sentences to process must be a postive integers.");
    
    
        self.logFile = logFile;
        if self.logFile is not None:
            try:
                self.logFD = open(self.logFile, 'w');
            except IOError:
                raise IOError("Cannot open logfile %s for writing." % logFile);
        else:
            self.logFD = sys.stdout;
    
        # Ensure that we will be able to open the output file
        # before we do a bunch of work, unless outputFile is None,
        # in which case we'll write to stdout:
        if outFileName is not None: 
            try:
                fd = open(outFileName,'w');
                fd.close();
            except IOError:
                raise IOError("Cannot open output file %s for writing." % outFileName);
        
        # (WordIndex is a static method, so no instantiation)
        tokenFeeder = TokenFeeder(dirToTokens, maxNumSentences=maxNumSentences);
        currToken = tokenFeeder.next();
        # For progress reporting:
        msgsProcessed = 0;
        msgsSinceLastReported = 0;
        LOG_MSG_INTERVAL = 1000
        currMsgID = 0;
        try:
            for token in tokenFeeder:
                nextToken = tokenFeeder.next();
                currPosting = WordIndex.getPosting(currToken.word);
                if currPosting is None:
                    currPosting = WordPosting(currToken.word);
                    # This posting is at the top level of the index.
                    # Set the respective flag to True. This will 
                    # change somne of the wordPosting's behavior:
                    currPosting.isTopLevelPosting = True;
                    # The count is set to
                    currPosting.initOccurrenceInCollection();
                    WordIndex.addPosting(currPosting);
                else:
                    # Found this token before, bump its count:
                    currPosting.bumpOccurrenceInCollection();
                nextPosting = WordIndex.getPosting(nextToken.word);
                if nextPosting is None:
                    nextPosting = WordPosting(nextToken.word);
                    # This posting is at the top level of the index.
                    # Set the respective flag to True. This will 
                    # change somne of the wordPosting's behavior:
                    nextPosting.isTopLevelPosting = True;
                    currPosting.initOccurrenceInCollection();                    
                    WordIndex.addPosting(nextPosting);
                else:
                    nextPosting.bumpOccurrenceInCollection();
                if nextToken.sentenceID == currToken.sentenceID:
                    # Make a new posting for this follow-on word. That new
                    # posting will live in currPosting's dict of followers,
                    # and will have its own occurrence count. That count is
                    # separate from the overall count kept in currPosting:
                    followerWordPosting = WordPosting(nextPosting.rootWord);
                    followerWordPosting.initFollowingCount();
                    currPosting.addFollowsWord(followerWordPosting);
                currToken = nextToken;
                if currToken.emailID != currMsgID:
                    currMsgID = currToken.emailID;
                    msgsProcessed += 1;
                    msgsSinceLastReported += 1;
                    if msgsSinceLastReported >= LOG_MSG_INTERVAL:
                        msgsSinceLastReported = 0;
                        self.log("Processed %d emails..." % msgsProcessed);
        except StopIteration:
            pass
            
        self.log("Done creating in-memory index. Writing to csv file...");

        # Build the CSV file:
        try:
            if outFileName is not None:
                csvFD = open(outFileName,'w');
            else:
                csvFD = sys.stdout;
            # The column headers:
            # FollowersCount is number of times a given word followed a given other word:
            csvFD.write("Word,Follower,FollowersCount,MetaNumOccurrences,MetaNumSuccessors,MetaWordLength\n");
            for wordPosting in WordIndex.__iter__():
                word = wordPosting.getRootWord();
                # Write the summary information about this word:
                csvFD.write(word + ',' +\
                            # No Follower
                            ',' +\
                            # No FollowersCount
                            ',' +\
                            # MetaNumOccurrences:
                            str(wordPosting.getNumOccurrences()) + ',' +\
                            # MetaNumSuccessors:
                            str(wordPosting.getNumFollowers()) + ',' +\
                            # MetaWordLength:
                            str(len(wordPosting.getRootWord())) +\
                            '\n');
                # Write one line for each follower:
                for followerWordPosting in wordPosting:
                    csvFD.write(word + ',' +\
                                followerWordPosting.getRootWord() + ',' +\
                                str(followerWordPosting.getHowOftenIFollowed()) +\
                                # No MetaWordCount:
                                ',' +\
                                # No MetaNumSuccessors:
                                ',' +\
                                # No MetaNumSentenceOcc,
                                ',' +\
                                # No MetaNumMsgOcc:
                                #',' +\  # this adds an extra comma, making Sqlite think there are 7 cols.
                                '\n');
                    
        finally:
            if outFileName is not None:
                csvFD.close();
            if self.logFile is not None:
                self.log("Done.");
                self.logFD.close();
            else:
                print "Done.";
        
    
    def log(self, msg):
        print >>self.logFD, msg; 
        
# ---------------------------------------------- Class TokenFeeder  --------------------------

class TokenFeeder(object):
    '''
    Main class. Given a directory with tokenized emails, generate
    a CSV file. Schema: Word,EmailID,SentenceID
    '''
    
    def __init__(self, dirToTokens, maxNumSentences=None):
    
        if maxNumSentences is not None and maxNumSentences <= 0:
            raise ValueError("Maximum number of sentences to process must be a postive integers.");
        self.maxNumSentences = maxNumSentences    
        self.sentenceIt = SentenceFeeder(dirToTokens);
        self.currSentence = None;
        self.tokenIt = None;
        self.numSentencesProcessed = 0;
        TokenFromSentenceFeeder.currSentenceID = 0;
            
    def __iter__(self):
        return self;
    
    def next(self):
        while 1:
            if self.currSentence is None:
                # Will throw StopIteration when no more sentences:
                self.currSentence = self.sentenceIt.next();
                self.numSentencesProcessed += 1;
                TokenFromSentenceFeeder.currSentenceID += 1;
                if self.maxNumSentences is not None and self.numSentencesProcessed > self.maxNumSentences:
                    raise StopIteration;
                self.tokenIt = TokenFromSentenceFeeder(self.currSentence);
            while 1:
                try:
                    newTokenObj = self.tokenIt.next();
                except StopIteration:
                    # All tokens in this sentence have been fed out.
                    # Continue in the outer loop, getting a new sentence:
                    self.currSentence = None;
                    break;
                if newTokenObj is None:
                    continue;
                return newTokenObj;

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

class TokenFromSentenceFeeder(object):
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
    contractionTest = re.compile("('[^,]*)"); # If non-None, then matchObj.group(1) is the contraction
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
                self.tokenIt = TokenFromSentenceFeeder.tokenExtractPattern.finditer(self.sentence);
            else:                
                # This sentence straddles two messages.
                # Remember the start of the next email message on the 
                # far side of the email message separator:
                self.fragNextMessage = sentenceFrontEnd;
                # The ID of the upcoming message:
                try: 
                    self.nextMsgID = int(nextEmailID);
                except ValueError as e:
                    # Email recognition fails when two message headers are in
                    # a single sentence. In that case, nextEmailID is an empty
                    # string. We just bump the latest msg ID we know about:
                    self.nextMsgID = TokenFromSentenceFeeder.currMsgID + 1;
                    print "Warning: Bad emailID extraction (bumping old ID to recover): '%s'. Tail:'%s'. Front:'%s'.CurrMsgID: '%s'." % (nextEmailID,sentenceTrail,sentenceFrontEnd, self.currMsgID);
                self.tokenIt = TokenFromSentenceFeeder.tokenExtractPattern.finditer(sentenceTrail);
                
        try:
            matchObj = self.tokenIt.next();
        except StopIteration:
            # Sentence is exhausted. But do we already have the beginning
            # sentence of the next message in this sentence?:
            if self.fragNextMessage is not None:
                TokenFromSentenceFeeder.currMsgID = self.nextMsgID;
                self.tokenIt = TokenFromSentenceFeeder.tokenExtractPattern.finditer(self.fragNextMessage);
                self.fragNextMessage = None;
                TokenFromSentenceFeeder.currMsgID = self.nextMsgID;
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
            endOfToken = matchObj.end(2);
        else:
            word = matchObj.group(1)
            endOfToken = matchObj.end(1);
            
        # Clean tokens: eliminate empty strings, all-caps, and punctuation-only strings:
        word = self.cleanToken(word);
        if word is None:
            return None;
        
        # Is next word a contraction? (e.g. [this, 'll, blow, your, mind]).
        # token iterator cursor will point to the comma after the 
        # current word (e.g. the comma after 'this'):
        contraction = self.isContraction(endOfToken);
        if contraction is not None:
            # Skip past the contraction:
            self.tokenIt.next();
            # Drop closing right bracket that's there if
            # contraction was last token of sentence:
            if contraction[-1] == ']':
                word += contraction[0:-1];
            else:
                word += contraction;
        
        return (Token(TokenFromSentenceFeeder.currMsgID, TokenFromSentenceFeeder.currSentenceID, word));
        
    def isContraction(self, endOfCurrMatch):
        '''
        Returns a string containing the contraction, if 
        a contraction token follows the given position in 
        self.sentence. Else returns None. Example:
        [this, 'll, blow, your, mind]. If endOfCurrMatch
        is 5, then this method returns "'ll". 
        @param endOfCurrMatch: index to the comma that follows the current token.
        @type token: int
        '''
        matchObj = self.contractionTest.search(self.sentence, endOfCurrMatch);
        # If we have no match, done:
        if matchObj is None:
            return None;
        
        contraction = matchObj.group(1);
        # But is the contraction immediately following
        # the passed-in starting position, rather than 
        # several tokens further down? The passed-in
        # endOfCurrMatch pts to the curr token's closing
        # comma. The start pos of the contraction neeeds
        # to be passed that comma and the space that follows
        # that comma:
        if matchObj.start(1) != endOfCurrMatch + 2:
            return None;
        return contraction;

    def isPunctuationOnly(self, token):
        # Pattern: '[^,!;.?[\]]'  # If None: only punctuation
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
        
        matchObj = TokenFromSentenceFeeder.messageSepTest.search(sentence);
        if matchObj is None:
            return (None,None,None);
        else:
            # One of each pair of brackets below are not inserted. That's because they
            # come in as part of the matches:
            currEmailTrailTokens = matchObj.group(1);
            nextEmailID = matchObj.group(2);
            nextEmailFrontTokens = matchObj.group(3);
            return (currEmailTrailTokens, nextEmailID, nextEmailFrontTokens);
    
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
        # Remove stopwords:
        if tokenStr.lower() in STOPWORDS:
            return None;
        
        return tokenStr;
        
# ---------------------------------------------- Class SentenceFeeder --------------------------

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
            raise ValueError("SentenceFeeder needs absolute path to directory with email token files.");
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
                raise ValueError("Could not extract email chunk file serial number from file name '%s'. Extraction got '%s'" % (chunkFileName, serialNumStr));
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
    
    foo(2,set([0]),set([0]))
    bar(5,set([1, 2, 3]), set([3]))
    ----one(1,set([2]),set([2,5,10]))
    ----two(2,set([3]), set([3,14]))
    
    foo occurred twice, both times in sentence 0 of msg 0.
    bar occurred five times, in sentences 1,2,and 3 of msg 3
    bar was following by the word 'one' one time, in sentence 3, msgs 2,5, and 10
    bar was following by the word 'two' twice, in sentence 3, msgs 3 and 14
    '''
    
    allPostings = OrderedDict();


    @staticmethod
    def __iter__():
        return WordIndex.WordIterator();
    
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
            # wordPosting was not yet in the index: insert it:
            WordIndex.allPostings[wordPosting.getRootWord()] = wordPosting;
            return True;
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
    
    class WordIterator(object):
        '''
        Provides an iterator service for the enclosing class WordIndex.
        Feeds out one WordPosting at a time, one for each word in the index.
        '''
        
        def __init__(self):
            # Use iteration through WordIndex's root words, i.e. the dict keys:
            self.theIterator = WordIndex.allPostings.__iter__();
            
        def __iter__(self):
            return self;
        
        def next(self):
            '''
            Get next key from the WordIndex.allPostings dict (a word), and 
            return its item: a WordPosting.
            '''
            # Get next word's posting, and return it.
            # The WordIndex.allPostings iterator with throw
            # the required StopIteration exception when
            # the word index is exhausted:
            return WordIndex.getPosting(self.theIterator.next());
        

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
    
    #def __init__(self, word, sentenceID, emailMsgID):
    def __init__(self, word):
        self.rootWord = word;
        self.wordPostingsDict = OrderedDict();
        #self.inSentence = set([sentenceID]);
        #self.inEmail = set([emailMsgID]);
        self.followingCount = -1;
        self.numOccInCollection = -1;
        self.wordPostingsIndex = -1;
        self.isTopLevelPosting = False;
        
    def initOccurrenceInCollection(self):
        self.numOccInCollection = 1;
        
    def initFollowingCount(self):
        self.followingCount = 1;

    def __repr__(self):
        return "<WordPosting: %s %d followers following %d (%d)>" % (self.rootWord, len(self.wordPostingsDict.keys()), self.followingCount, id(self));

    def __str__(self):
        return "<WordPosting: %s %d followers following %d (%d)>" % (self.rootWord, len(self.wordPostingsDict.keys()), self.followingCount, id(self));

    def bumpOccurrenceInCollection(self):
        '''
        Only called by WordIndex when a word is found (again).
        This is greater than 1 only for the top level WordPosting within
        WordIndex
        '''
        if self.isTopLevelPosting:
            self.numOccInCollection += 1;

    def getNumOccurrences(self):
        '''
        Return number of times this posting's word occurred in the emails total.
        @return: total number of this word's occurrences. Or -1, if this WordPosting
                 is not a top level posting in WordIndex.
        @rtype: int
        '''
        if self.isTopLevelPosting:
            return self.numOccInCollection;
        else:
            return -1;
    
    def getHowOftenIFollowed(self):
        '''
        Returns how often this WordPosting W's rootWord followed the 
        WordPosting in whose wordPostingsDict W is listed as a follower.
        I.e. this number is how often this word followed a particular
        other word. If this WordPosting is not top level in WordIndex,
        method returns -1.
        '''
        if not self.isTopLevelPosting:
            return self.followingCount;
        else:
            -1;
    
    def getNumFollowers(self):
        '''
        @return: number of words that follow this word
        @rtype: int
        '''
        return len(self.wordPostingsDict.keys());
    
#    def getNumOfEmailOccurrences(self):
#        '''
#        @return: number of emails  in which this word occurred.
#        @rtype: int
#        '''
#        return len(self.inEmail);
#    
#    def getNumOfSentenceOccurrences(self):
#        '''
#        @return: number of sentences  in which this word occurred.
#        @rtype: int
#        '''
#        return len(self.inSentence);

    def getRootWord(self):
        return self.rootWord;
    
    def addFollowsWord(self, newFollowWordPosting):
        '''
        Given a posting that follows this word, and a sentence ID for context,
        add the new posting into the wordPostingsDict. Also add the sentence ID
        into the inSentence set.
        @param newFollowWordPosting: WordPosting to be added as a follower.
        @type newFollowWordPosting: WordPosting
        '''
        try:
            # Does this follow-word already exist in this posting's follow-words?
            myFollowPosting = self.wordPostingsDict[newFollowWordPosting.getRootWord()];
            # The new word has followed this WordPosting index's root word before. Keep count:
            myFollowPosting.followingCount += 1;
        except KeyError:
            self.wordPostingsDict[newFollowWordPosting.getRootWord()] = newFollowWordPosting;
        
    def __iter__(self):
        self.rootWords = self.wordPostingsDict.keys();
        return self;
    
    def next(self): #@ReservedAssignment
        '''
        Iterator over the successor postings of this posting.
        @return: each call returns one posting that represents a follow-on word,
                 until no more followers are left.
        @rtype: WordPosting
        '''
        self.wordPostingsIndex += 1;
        if self.wordPostingsIndex >= len(self.rootWords):
            raise StopIteration;
        # Get next root word from the keys of self.wordPostingsDict array,
        # and return that word's posting in the WordIndex
        nextFollowerWord = self.rootWords[self.wordPostingsIndex]; 
        return self.wordPostingsDict[nextFollowerWord];
        
# -----------------------  Testing ------------------------

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(prog='make_database_from_emails')
    parser.add_argument("tokenChunkFileDir", help="directory with chunk files of tokenized emails.");
    parser.add_argument("-o", "--outputCSVPath", help="fully qualified path to ouput .csv file (gets overwritten). If omitted: tuples written to stdout.");    
    parser.add_argument("-t", "--testing", action="store_true", dest="testing",
                        help="flag to just run tests.");
    
    
    args = parser.parse_args();

    if not args.testing:
        #Uncomment this block for real run
        logFileDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Resources/EnronCollectionProcessed');
        logFile    = os.path.join(logFileDir,'enronDBCreation.log');
        DBCreator(args.tokenChunkFileDir, args.outputCSVPath, logFile=logFile);
        
        
        #tokenChunkFilesDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Resources/EnronCollectionProcessed/EnronTokenized');
#        tokenChunkFilesDir = "/home/paepcke/tmp/TokenTest"
#        #dbCreator = DBCreator(tokenChunkFilesDir, '/tmp/outTest.csv', maxNumSentences=10, logFile='/tmp/myLog.txt');
#        dbCreator = DBCreator(tokenChunkFilesDir, '/tmp/outTest.csv', logFile='/tmp/myLog.txt');
        sys.exit();
    else:
        args.testing = None;

    
    # ------------------------------------------------------------------------------------------
    # The -t or --test option was given to the script implementation. Do unittesting:
    
    import unittest
    import shutil
    
    testAll = False;

#    DBCreator(args.tokenChunkFileDir, args.outputCSVPath, maxNumSentences=2000);
#    sys.exit()
    
    class TestSuite(unittest.TestCase):
                
        def setUp(self):
            self.tokenChunkFilesDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Resources/EnronCollectionProcessed/EnronTokenized');
            self.sentenceFeeder = SentenceFeeder(self.tokenChunkFilesDir);

        @unittest.skipIf(not testAll, 'Skipping testIngest')
        def testIngest(self):
            self.sentenceFeeder.ingestOneTokenFile();
            print self.sentenceFeeder.currContent[0:300];

        @unittest.skipIf(not testAll, 'Skipping testIngest')
        def testTokenFromSentenceFeeder(self):
            
            # Single token:
            sentence = "[foo]" 
            tokenFeeder = TokenFromSentenceFeeder(sentence);
            token = tokenFeeder.next();
            #print "MsgID: %d, SentenceID: %d, Word: %s" % (token.emailID, token.sentenceID, token.word);
            self.assertEqual(token.emailID, 0, "First msg id not zero: " + str(token.emailID));
            self.assertEqual(token.sentenceID, 0, "First sentence id not zero: " + str(token.sentenceID));
            self.assertEqual(token.word, 'foo', "First sentence word is not 'foo': " + str(token.word));
            
            # Two tokens
            sentence = "[foo, bar]";
            tokenFeeder = TokenFromSentenceFeeder(sentence);
            for i, token in enumerate(tokenFeeder):
                #print "MsgID: %d, SentenceID: %d, Word: %s" % (token.emailID, token.sentenceID, token.word);
                self.assertEqual(token.emailID, 0, "First msg id not zero: " + str(token.emailID));
                self.assertEqual(token.sentenceID, 0, "Sentence id of sentence %d bad : %d" % (i, token.sentenceID))
                if i == 0: 
                    self.assertEqual(token.word, 'foo', "First sentence word is not 'foo': " + str(token.word));
                else:
                    self.assertEqual(token.word, 'bar', "Second sentence word is not 'foo': " + str(token.word));
            
            # Empty sentence:
            sentence = "[]";
            tokenFeeder = TokenFromSentenceFeeder(sentence);
            for i, token in enumerate(tokenFeeder):
                if i == 0:
                    self.assertEqual(token, None, "First and only token out of an empty sentence should be None. Was '%s'" % str(token));
                    continue;
                self.fail("Received more than one token for an empty sentence: '%s' (i=%d)." % (str(token), i));
                
            # Email separator only:
            sentence = "[%s]" % TokenFromSentenceFeeder.emailSep;
            tokenFeeder = TokenFromSentenceFeeder(sentence);
            for i, token in enumerate(tokenFeeder):
                if i == 0:
                    self.assertEqual(token, None, "First token should be None for the (empty) sentence fragment before the sep. Was '%s'" % str(token));
                    continue;
                if i == 1:
                    self.assertEqual(token, None, "Second token should be None for the (empty) sentence fragment after the sep. Was '%s'" % str(token));
                    continue;
                if i == 3:
                    self.fail("Should not have had a third round through loop.. Token was '%s'" % str(token));
             
            # Email separator with one-word remainder in front:
            sentence = "[foo, %s]" % TokenFromSentenceFeeder.emailSep;
            tokenFeeder = TokenFromSentenceFeeder(sentence);
            # Pretend the email currently being processed has ID=4
            TokenFromSentenceFeeder.currMsgID = 4; 
            for i, token in enumerate(tokenFeeder):
                if i == 0:
                    self.assertEqual(token.word, 'foo', "First token should 'foo' for the (empty) sentence fragment before the sep. Was '%s'" % token.word);
                    self.assertEqual(token.emailID, 4, "EmailID should be 4. Was %d." % token.emailID);
                    continue;
                if i == 1:
                    self.assertEqual(token, None, "Second token should be None for the end of the sentence fragment before the sep. Was '%s'" % str(token));
                    continue;
                if i == 2:
                    self.assertEqual(token, None, "Third token should None for the non-existing sentence frag after the sep. Was '%s'" % str(token));
                    continue;
                if i == 3:
                    self.fail("Should not have had a third round through loop.. Token was '%s'" % str(token));
            
            # Email separator with two-word remainder in front:
            sentence = "[foo, bar, %s]" % TokenFromSentenceFeeder.emailSep;
            tokenFeeder = TokenFromSentenceFeeder(sentence);
            TokenFromSentenceFeeder.currMsgID = 4; 
            for i, token in enumerate(tokenFeeder):
                if i == 0:
                    self.assertEqual(token.word, 'foo', "First token should 'foo' for the (empty) sentence fragment before the sep. Was '%s'" % token.word);
                    self.assertEqual(token.emailID, 4, "EmailID should be 4. Was %d." % token.emailID);
                    continue;
                if i == 1:
                    self.assertEqual(token.word, 'bar', "Second token should 'bar' for the (empty) sentence fragment before the sep. Was '%s'" % token.word);
                    self.assertEqual(token.emailID, 4, "EmailID should be 4. Was %d." % token.emailID);
                    continue;
                if i == 2:
                    self.assertEqual(token, None, "Third token should None for the end of the sentence fragment before the sep. Was '%s'" % str(token));
                    continue;
                if i == 3:
                    self.assertEqual(token, None, "Fourth token should None for the non-existing sentence frag after the sep. Was '%s'" % str(token));
                    continue;
                if i == 4:
                    self.fail("Should not have had a Fifth round through loop.. Token was '%s'" % str(token));
            
            # Email separator with no trailing tokens from prev msg, but one token belonging to next msg:
            sentence = "[%s, green]" % TokenFromSentenceFeeder.emailSep;
            tokenFeeder = TokenFromSentenceFeeder(sentence);
            TokenFromSentenceFeeder.currMsgID = 4; 
            for i, token in enumerate(tokenFeeder):
                if i == 0:
                    self.assertEqual(token, None, "First token should be None for the (empty) sentence fragment before the sep. Was '%s'" % str(token));
                    continue;
                if i == 1:
                    self.assertEqual(token.word, 'green', "First token should 'foo' for the (empty) sentence fragment before the sep. Was '%s'" % token.word);
                    self.assertEqual(token.emailID, 5, "EmailID should be 5. Was %d." % token.emailID);                    
                    continue;
                if i == 2:
                    self.fail("Should not have had a third round through loop.. Token was '%s'" % str(token));
            
            # Email separator with no trailing tokens from prev msg, but one token belonging to next msg:
            sentence = "[%s, green, red]" % TokenFromSentenceFeeder.emailSep;
            tokenFeeder = TokenFromSentenceFeeder(sentence);
            TokenFromSentenceFeeder.currMsgID = 4; 
            for i, token in enumerate(tokenFeeder):
                if i == 0:
                    self.assertEqual(token, None, "First token should be None for the (empty) sentence fragment before the sep. Was '%s'" % str(token));
                    continue;
                if i == 1:
                    self.assertEqual(token.word, 'green', "First token should 'green' for the (empty) sentence fragment before the sep. Was '%s'" % token.word);
                    self.assertEqual(token.emailID, 5, "EmailID should be 5. Was %d." % token.emailID);                    
                    continue;
                if i == 2:
                    self.assertEqual(token.word, 'red', "First token should 'red' for the (empty) sentence fragment before the sep. Was '%s'" % token.word);
                    self.assertEqual(token.emailID, 5, "EmailID should be 5. Was %d." % token.emailID);                    
                    continue;
                if i == 3:
                    self.fail("Should not have had a third round through loop.. Token was '%s'" % str(token));
                    
            # Email separator with both leading and trailing tokens:
            sentence = "[foo, %s, green, red]" % TokenFromSentenceFeeder.emailSep;
            tokenFeeder = TokenFromSentenceFeeder(sentence);
            TokenFromSentenceFeeder.currMsgID = 4; 
            for i, token in enumerate(tokenFeeder):
                if i == 0:
                    self.assertEqual(token.word, 'foo', "First token should 'foo' for the (empty) sentence fragment before the sep. Was '%s'" % token.word);
                    self.assertEqual(token.emailID, 4, "EmailID should be 4. Was %d." % token.emailID);
                    continue;
                if i == 1:
                    self.assertEqual(token, None, "Second token should None for the end of the sentence fragment before the sep. Was '%s'" % str(token));
                    continue;
                if i == 2:
                    self.assertEqual(token.word, 'green', "First token should 'green' for the (empty) sentence fragment before the sep. Was '%s'" % token.word);
                    self.assertEqual(token.emailID, 5, "EmailID should be 5. Was %d." % token.emailID);                    
                    continue;
                if i == 3:
                    self.assertEqual(token.word, 'red', "First token should 'red' for the (empty) sentence fragment before the sep. Was '%s'" % token.word);
                    self.assertEqual(token.emailID, 5, "EmailID should be 5. Was %d." % token.emailID);                    
                    continue;
                if i == 4:
                    self.fail("Should not have had a third round through loop.. Token was '%s'" % str(token));
                    
            # Contraction at start of sentence:
            sentence = "[this, 'll, blow]";
            tokenFeeder = TokenFromSentenceFeeder(sentence);
            for i, token in enumerate(tokenFeeder):
                if i == 0:
                    self.assertEqual(token.word, "this'll", "Expected 'this', got '%s'." % token.word);
                    continue;
                if i == 1:
                    self.assertEqual(token.word, 'blow', "Expected 'this', got '%s'." % token.word);
                    continue;
                if i == 2:
                    self.fail("Should not have had a third round through loop.. Token was '%s'" % str(token));
                
                
            # Contraction in middle of sentence:
            sentence = "[foo, this, 'll, blow]";
            tokenFeeder = TokenFromSentenceFeeder(sentence);
            for i, token in enumerate(tokenFeeder):
                if i == 0:
                    self.assertEqual(token.word, 'foo', "Expected 'this', got '%s'." % token.word);
                    continue;
                if i == 1:
                    self.assertEqual(token.word, "this'll", "Expected 'this', got '%s'." % token.word);
                    continue;
                if i == 2:
                    self.assertEqual(token.word, 'blow', "Expected 'this', got '%s'." % token.word);
                    continue;
                if i == 3:
                    self.fail("Should not have had a third round through loop.. Token was '%s'" % str(token));
            
            # Contraction at end of sentence:
            sentence = "[this, 'll]";
            tokenFeeder = TokenFromSentenceFeeder(sentence);
            for i, token in enumerate(tokenFeeder):
                if i == 0:
                    self.assertEqual(token.word, "this'll", "Expected 'this'll', got '%s'." % token.word);
                if i == 2:
                    self.fail("Should not have had a second round through loop.. Token was '%s'" % str(token));
                    continue;
                
        # Contraction at end of sentence:                
        def testTokenFeeder(self):
            tokenDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "Resources/EnronCollectionProcessed/EnronTokenized");                       
            for token in TokenFeeder(tokenDir, maxNumSentences=3):
                print(str(token));
            
            
    unittest.main();

