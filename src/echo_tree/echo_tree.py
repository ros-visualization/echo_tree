#!/usr/bin/env python

import os;
import sys;

import sqlite3;
import json;
from contextlib import contextmanager;
from operator import itemgetter;
from collections import OrderedDict;

'''
Module for generating word tree datastructures from an underlying
database of co-occurrence data in a collection. Provides both 
Python and JSON results.
'''

class WordDatabase(object):
    '''
    Service class to wrap an underlying SQLite database file.
    '''
    
    def __init__(self, SQLiteDbPath):
        '''
        Open an SQLite connection to the underlying SQLite database file: 
        @param SQLiteDbPath: SQLite database file.
        @type SQLiteDbPath: string
        '''
        self.dbPath = SQLiteDbPath;
        self.conn   = sqlite3.connect(self.dbPath);
        
    def close(self):
        pass;

class WordFollower(object):
    '''
    Provides a 'with' facility for database cursors. Used by
    methods of class WordExplorer to treat db cursors as
    tuple generators that close the cursor even after
    exceptions. See Python contextmanager.
    '''

    def __init__(self, db, word):
        '''
        Provides a tuple generator, given a WordDatabase instance 
        that accesses a word co-occurrence file, and a root word.
        @param db: WordDatabase instance that wraps an SQLite co-occurrence file.
        @type db: WordDatabase
        @param word: Root word, whose follower words are to be found.
        @type word: string
        '''
        self.db   = db;
        self.word = word;
        
    def __enter__(self):
        '''
        Method required by contextmanager. Create a new cursor,
        then initializes a tuple stream <followerWord><count>.
        @return: initialized database cursor.
        @rtype: sqlite3.cursor
        '''
        self.cursor = self.db.conn.cursor();
        self.cursor.execute('SELECT follower,count from WordStats where word="%s";' % self.word);
        # Return iterator:
        return self.cursor;
    
    def __exit__(self, excType, excValue, traceback):
        '''
        Method required by contextmanager. Closes cursor. Called automatically
        when 'with' clause goes out of scope, naturally, or via an exception. 
        @param excType: Exception type if an exception occurred, or None.
        @type excType: string?
        @param excValue: Exception object if an exception occurred, or None.
        @type excValue: Exception
        @param traceback: Traceback object if an exception occurred, or None.
        @type traceback: traceback.
        '''
        if excType is not None:
            # Don't do anything special if 
            # exception occurred in the caller's with clause:
            pass;
        self.cursor.close();
        
        
class WordExplorer(object):
    '''
    Main class. Provides extraction of a frequency ordered JSON
    structure, given a source word and an underlying co-occurrence database.
    Python structures are recursive, as are the corresponding JSON structures:
      WordTree :=
        {"word" : <rootWord>,
         "followWordObjs" : [WordTree1, WordTree2, ...]
         }
    '''
    
    def __init__(self, dbPath):
        '''
        Create new WordExplorer that can be used for multiple tree creation requests.
        @param dbPath: Path to SQLite word co-occurrence file.
        @type dbPath: string
        '''
        self.cache = {};
        self.db = WordDatabase(dbPath);

    def getSortedFollowers(self, word):
        '''
        Return an array of follow-words for the given root word.
        The array is sorted by decreasing frequency. A cache
        is maintained to speed requests for root words after
        their first use, which must turn to the database. All
        After the first request, follow-ons will therefore be fast.   
        @param word: root word for the new WordTree.
        @type word: string
        '''

        try:
            frequencySortedWordArr = self.cache[word];
        except KeyError:
            # Not cached yet:
            wordArr = []; 
            with WordFollower(self.db, word) as followers:
                for followerWordPlusCount in followers:
                    wordArr.append(followerWordPlusCount);
            # Sort array in place, using element 1 (the count) as
            # sort key. Want largest count (most frequent follower) 
            # first:
            wordArr.sort(key=itemgetter(1), reverse=True);
            #print wordArr;
            frequencySortedWordArr = [];
            for wordPlusCount in wordArr:
                frequencySortedWordArr.append(wordPlusCount[0]);
            self.cache[word] = frequencySortedWordArr;
        return frequencySortedWordArr;
      
      
    def makeWordTree(self, word, wordTree=None, maxDepth=3):
        '''
        Return a Python WordTree structure in which the
        followWordObjs are sorted by decreasing frequency. This
        method is recursive, and is the main purpose of this class.
        @param word: root word for the new WordTree
        @type word: string
        @param wordTree: Dictionary to use for one 'word'/'followWordObjs.
        @type wordTree: {}
        @param maxDepth: How deep the tree should grow, that is how far along a 
                         word-follows chain the recursion should proceed.
        @type maxDepth: int
        @param frequencyRankCutoff: 
        @type frequencyRankCutoff:
        '''
        # Recursion bottomed out:
        if maxDepth == 0:
            return wordTree;
        if wordTree is None:
            # Use OrderedDict so that conversions to JSON show the 'word' key first:
            wordTree = OrderedDict();
        wordTree['word'] = word;
        wordTree['followWordObjs'] = []
        for followerWord in self.getSortedFollowers(word):
            # Each member of the followWordOjbs array is its own tree:
            followerTree = OrderedDict();
            newSubtree = self.makeWordTree(followerWord, followerTree, maxDepth-1);
            # Don't enter empty dictionaries into the array:
            if len(newSubtree) > 0:
                wordTree['followWordObjs'].append(newSubtree);
        return wordTree;
    
    def makeJSONTree(self, wordTree):
        '''
        Given a WordTree structure created by makeWordTree, return
        an equivalent JSON tree.
        @param wordTree: Word tree structure emanating from a root word.
        @type wordTree: {}
        '''
        return json.dumps(wordTree);
              
# ----------------------------   Testing   ----------------

if __name__ == "__main__":
    
    dbPath = os.path.join(os.path.realpath(os.path.dirname(__file__)), "Resources/testDb.db");
    
#    db = WordDatabase(dbPath);
#    with WordFollower(db, 'ant') as followers:
#        for followerWord in followers:
#            print followerWord;
    
    explorer = WordExplorer(dbPath);
    
#    print explorer.getSortedFollowers('ant');
#    print explorer.getSortedFollowers('echo');
#    # Cache works? (put breakpoint in getSortedFollowers try: statement to check):
#    print explorer.getSortedFollowers('ant');
            
#    print explorer.makeWordTree('ant');
#    print explorer.makeWordTree('echo');
    jsonTree = explorer.makeJSONTree(explorer.makeWordTree('echo'));
    print jsonTree;
    
        