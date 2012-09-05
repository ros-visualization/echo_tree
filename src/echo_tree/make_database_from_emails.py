#!/usr/bin/env python

import os
import sys
import re

class DBCreator(object):

    def __init__(self):
        pass

# ---------------------------------------------- Class Token  --------------------------

class Token(object):
    
    def __init__(self, word, sentenceID, emailID):
        self.word = word;
        self.sentenceID = sentenceID;
        self.emailID = emailID;
        
# ---------------------------------------------- Class LineFeeder --------------------------

class LineFeeder(object):
    '''
    Iterator over the entire email collection. Each call to next()
    returns a triplet: (msgID, sentenceID, sentence) 
    
    Can operated after make_clean_email_files was run to collect emails from the Enron
    email directory tree, and after those messages have been cleaned
    of email headers and most non-alpha chars. That is all accomplished
    by script src/bash_scripts/removeEmailHeaders.sh. 
    '''
    
    def __init__(self, dirToCleanEmails):
        '''
        Expects a directory containing files of the form email12_NoHeads.txt,
        with 12 being an example of a changing serial number. Each file is
        expected to contain a collection of email messages, cleaned of headers,
        numbers, and other extraneous chars. The messages within the chunk files
        are expected to be separated by lines of the form:
        
        #/*277165*/!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!#^@
        
        where the number is the serial number of the following email.
         
        Method creates a sorted list of these chunk names in self.sortedEmailChunks.
        @param dirToCleanEmails: directory path to email chunk files
        @type dirToCleanEmails: string
        '''
        if not os.isdir(dirToCleanEmails):
            raise ValueError("LineFeeder needs absolute path to directory with cleaned email files.");
        # Get all the email chunk file names:
        allEmailFiles = os.listdir(dirToCleanEmails);
        # Count the .txt files:
        numEmailFiles = sum(1 for fileName in allEmailFiles if fileName.find('.txt') > -1);
        if numEmailFiles == 0:
            raise ValueError("No email files found in '%s'." % dirToCleanEmails);
        self.sortedEmailChunks = [None] * numEmailFiles;
        # Email chunk files have names like email12_NoHeads.txt. Sort
        # them into sortedEmailChunks according to their embedded
        # serial number (in this case 12:
        for chunkFileName in allEmailFiles:
            serialNumStr = re.sub(r'[^0-9]', '', chunkFileName);
            try:
                serialNum = int(serialNumStr);
            except ValueError:
                raise ValueError("Could not extract email chunk file serial number from file name '%s'. Extraction got '%s" % (chunkFileName, serialNumStr));
            self.sortedEmailChunks[serialNum] = chunkFileName;
        
        self.currMsg = 0;
        self.currSentence = 0;
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
        
        
