#!/usr/bin/env python

import json;
from collections import deque;
from collections import OrderedDict;

from echo_tree.echo_tree import WORD_TREE_BREADTH;
from echo_tree.echo_tree import WORD_TREE_DEPTH;
from echo_tree.echo_tree import WordExplorer;

from echo_tree.make_database_from_emails import STOPWORDS;

class SentencePerformance(object):
    '''
    Stuct to hold measurement results of one sentence.
       - sentenceLen: number of words that are not stopwords.
       - failures: number of times a tree did not contain one of the words, and a new tree needed to 
                   be constructed by typing in the word.
       - outOfSeqs: number of times future word in the sentence was in an early tree.
       - depths: for each tree depth, how many of the sentence's words appeared at that depth.   
    '''
    
    def __init__(self, evaluator, sentenceNoStopwords, emailID=-1, sentenceID=None):
        self.evaluator = evaluator;
        self.sentenceNoStopwords = sentenceNoStopwords;
        self.emailID = emailID;
        self.sentenceID = sentenceID;
        
        self.sentenceLen = len(sentenceNoStopwords);
        # Count one failure for having to type in the first word:
        self.failures    = 1;
        self.outOfSeqs   = 0;
        self.depths      = {};
    
    def addFailure(self):
        '''
        Increment counter of occasions when a word was not found
        in the currently displayed tree.
        '''
        self.failures += 1;
        
    def addOutOfSeq(self):
        '''
        Increment count of occasions when a word was not found in the
        tree that was active when the word was to being considered, but
        was contained in a tree that was displayed in service
        of an earlier word in the sentence.        
        '''
        self.outOfSeqs += 1;
        
    def addWordDepth(self, depth):
        '''
        Given the depth of a tree at which a word was found,
        count one more such occurrence.
        @param depth: depth at which word was found in displayed tree.
        @type depth: int
        '''
        try:
            self.depths[depth] += 1;
        except KeyError:
            self.depths[depth] = 1;
            
    def getNetFailure(self):
        '''
        Return the difference between all failures and outOfSeqs.
        The latter are occasions when a word was not found in the
        tree that was active when the word was to be entered, but
        it was contained in a tree that was displayed in service
        of an earlier word in the sentence.
        '''
        return self.failures - self.outOfSeqs;
    
    def getNetSuccess(self):
        '''
        Return percentage of times a word was found in a currently
        displayed tree.
        '''
        return 100 - (self.getNetFailure() * 100.0 / self.sentenceLen);
        
    def getDepthCount(self, depth):
        '''
        Return the number of times a word in this sentence was found
        at the given depth. Takes care of cases when given depth was 
        never the site of a found word (returns 0).
        @param depth: depth in tree whose occurrence count is requested.
        @type depth: int
        '''
        try:
            return self.depths[depth];
        except KeyError:
            return 0;
        
    def getDepths(self):
        '''
        Create array of depth counts. The array will be as
        long as the deepest depth. Depths in between that were
        never site for a found word are properly entered as zero.
        '''
        deepest = self.evaluator.getMaxDepthAllSentences();
        self.allDepths = [];
        for oneDepth in range(1,deepest + 1):
            self.allDepths.append(self.getDepthCount(oneDepth));
        return self.allDepths;
    
    def getDeepestDepth(self):
        try:
            return max(self.depths.keys());
        except ValueError:
            # No entries in depths at all:
            return 0;
    
    def toString(self):
        '''
        Return human-readable performance of this sentence.
        '''
        netFailure = self.getNetFailure();
        netSuccess = self.getNetSuccess();
        depthReport = str(self.getDepths());
        
        return "SentenceLen: %d. Failures: %d. OutofSeq: %d. NetFailure: %d. NetSuccess: %.2f%%. Depths: %s" %\
            (self.sentenceLen, self.failures, self.outOfSeqs, netFailure, netSuccess, depthReport);
                        
    def toCSV(self):
        row =        str(self.emailID);
        row += ',' + str(self.sentenceID);
        row += ',' + str(self.sentenceLen);
        row += ',' + str(self.failures);
        row += ',' + str(self.outOfSeqs);
        row += ',' + str(self.getNetFailure());
        row += ',' + '%.2f' % self.getNetSuccess();
        for depth in range(1, self.evaluator.getMaxDepthAllSentences() + 1):
            row += ',' + str(self.getDepthCount(depth));
        return row;
        

class Evaluator(object):
    
    def __init__(self, dbPath):
        self.wordExplorer = WordExplorer(dbPath);
        self.initWordCaptureTally();
        
    def getMaxDepthAllSentences(self):
        '''
        Runs through all sentences this Evaluator instance has
        measured, and returns the deepest depth of all sentences:
        '''
        maxDepth = 0;
        for sentencePerf in self.performanceTally:
            maxDepth = max(sentencePerf.getDeepestDepth(), maxDepth);
        return maxDepth;
        
    def getCSVHeader(self):
        header = 'EmailID,SentenceID,SentenceLen,Failures,OutofSeq,NetFailure,NetSuccess';        
        for depthIndex in range(1,self.getMaxDepthAllSentences() + 1):
            header += ',Depth_' + str(depthIndex);
        return header;
    
    def toCSV(self):
        csv = self.getCSVHeader() + '\n';
        for sentencePerf in self.performanceTally:
            csv += sentencePerf.toCSV() + '\n';
        return csv;
            
    
    def extractWordSet(self, jsonEchoTreeStr):
        '''
        Given a JSON Echo Tree, return the root word and a flat set of
        all follow-on words.
        @param jsonEchoTreeStr: JSON EchoTree structure of any depth/breadth
        @type jsonEchoTreeStr: string
        '''
        pythonEchoTree = json.loads(jsonEchoTreeStr);
        flatTree  = self.extractWordSeqsHelper(pythonEchoTree);
        flatList  = flatTree.split();
        rootWord = flatList[0];
        flatSet = set(flatList[1:]);
        return (rootWord, flatSet);
    
    def getDepthFromWord(self, pythonEchoTree, word):
        '''
        Given a word, return its depth in the tree. Root postion is 0.
        @param pythonEchoTree: Python encoded EchoTree
        @type pythonEchoTree: Dict
        @param word: word to find in the EchoTree
        @type word: string
        @return: the depth at which the word occurs in the tree, or 0 if not present.
        @rtype: {int | None}
        '''
        return self.getDepthFromWordHelper(pythonEchoTree, word, depth=0);
    
    def getDepthFromWordHelper(self, pythonEchoTree, wordToFind, depth=0):
        if pythonEchoTree is None:
            return None;
        if pythonEchoTree['word'] == wordToFind: 
            return depth;
        for subtree in pythonEchoTree['followWordObjs']:
            newDepth = self.getDepthFromWordHelper(subtree, wordToFind, depth=depth+1);
            if newDepth is not None:
                return newDepth;
        return None;
    
    
    def extractSentences(self, jsonEchoTreeStr):
        '''
        Print all sentences that can be made from the EchoTree.
        @param jsonEchoTreeStr:
        @type jsonEchoTreeStr:
        '''
        #sentenceStructs = self.extractWordSeqs(jsonEchoTreeStr);
        pass
        
    
    def extractWordSeqs(self, jsonEchoTreeStr):
        '''
        Given a JSON EchoTree structure, return a structure representing all
        'sentences' generated by the tree via a depth-first walk. Example:
        root  pig    truffle
                     mud
              tree   deep
                     broad
        generates: 
            deque([root, OrderedDict([(tree, deque([broad, deep]))]), 
                         OrderedDict([(pig, deque([mud, truffle]))])])
        from which one can generate:
            - root tree broad
            - root tree deep
            - root pig mud
            - root pig truffle
            
        @param jsonEchoTreeStr: JSON encoded EchoTree
        @type jsonEchoTreeStr:string
        '''
        pythonEchoTree = json.loads(jsonEchoTreeStr);
        flatTree  = self.extractWordSeqsHelper(pythonEchoTree);
        flatQueue = deque(flatTree.split());
        # Number of words: breadth ** (depth-1) + 1
        numSibPops = WORD_TREE_BREADTH ** (WORD_TREE_DEPTH - 2);
        # Root word first:
        resDictQueue = deque([flatQueue[0]]);
        for dummy in range(numSibPops):
            sibs = deque([]);
            parentDict = OrderedDict();
            resDictQueue.append(parentDict);
            for dummy in range(WORD_TREE_BREADTH):
                sibs.append(flatQueue.pop());
            parentDict[flatQueue.pop()] = sibs;
        return resDictQueue;
    
    def extractWordSeqsHelper(self, pythonEchoTreeDict):
        '''
        Too-long example (it's what I had on hand:
        {u'word': u'reliability', 
         u'followWordObjs': [
                {u'word': u'new', 
                 u'followWordObjs': [
                     {u'word': u'power', 
                      u'followWordObjs': []}, 
                     {u'word': u'generation', 
                      u'followWordObjs': []}, 
                     {u'word': u'business', 
                      u'followWordObjs': []}, 
                     {u'word': u'product', 
                      u'followWordObjs': []}, 
                     {u'word': u'company', 
                      u'followWordObjs': []}]}, 
                {u'word': u'issues', 
                 u'followWordObjs': [
                     {u'word': u'related', 
                      u'followWordObjs': []}, 
                     {u'word': u'need', 
                      u'followWordObjs': []}, 
                     {u'word': u'raised', 
                      u'followWordObjs': []}, 
                     {u'word': u'such', 
                      u'followWordObjs': []}, 
                     {u'word': u'addressed', 
                      u'followWordObjs': []}]}, 
                {u'word': u'legislation', 
                 u'followWordObjs': [
                     {u'word': u'passed', 
                      u'followWordObjs': []}, 
                     {u'word': u'allow', 
                      u'followWordObjs': []}, 
                     {u'word': u'introduced', 
                      u'followWordObjs': []}, 
                     {u'word': u'require', 
                      u'followWordObjs': []}, 
                     {u'word': u'provide', 
                      u'followWordObjs': []}]}, 
                {u'word': u'standards', 
                 u'followWordObjs': [
                     {u'word': u'conduct', 
                      u'followWordObjs': []}, 
                     {u'word': u'set', 
                      u'followWordObjs': []}, 
                     {u'word': u'needed', 
                      u'followWordObjs': []}, 
                     {u'word': u'facilitate', 
                      u'followWordObjs': []}, 
                     {u'word': u'required', 
                      u'followWordObjs': []}]}, 
                {u'word': u'problems', 
                 u'followWordObjs': [
                     {u'word': u'please', 
                      u'followWordObjs': []}, 
                     {u'word': u'California', 
                      u'followWordObjs': []}, 
                     {u'word': u'accessing', 
                      u'followWordObjs': []}, 
                     {u'word': u'arise', 
                      u'followWordObjs': []}, 
                     {u'word': u'occur', 
                     u'followWordObjs': []}]}]}        
        
        @param pythonEchoTreeDict:
        @type pythonEchoTreeDict: dict
        '''
        res = '';
        word = pythonEchoTreeDict['word'];
        res += ' ' + word;
        if len(pythonEchoTreeDict['followWordObjs']) == 0:
            return res;
        for subtree in pythonEchoTreeDict['followWordObjs']:
            res += self.extractWordSeqsHelper(subtree);
        return res;
            
    def initWordCaptureTally(self):
        self.performanceTally = [];
        
    def tallyWordCapture(self, sentenceTokens, emailID=-1, sentenceID=None):
        for word in sentenceTokens:
            if word.lower() in STOPWORDS or word in [';', ',', ':', '!', '%']:
                sentenceTokens.remove(word);
        # Make a new SentencePerformance instance, passing this evaluator,
        # the array of stopword-free tokens, and the index in the self.performanceTally
        # array at which this new SentencePerformance instance will reside:
        if sentenceID is None:
            sentenceID = len(self.performanceTally);
        sentencePerf = SentencePerformance(self, sentenceTokens, emailID=emailID, sentenceID=sentenceID);
        
        # Start for real:
        tree = self.wordExplorer.makeWordTree(sentenceTokens[0]);
        treeWords = self.extractWordSet(self.wordExplorer.makeJSONTree(tree));
        for wordPos, word in enumerate(sentenceTokens[1:]):
            word = word.lower();
            wordDepth = self.getDepthFromWord(tree, word);
            if wordDepth is None:
                # wanted word is not in tree anywhere:
                sentencePerf.addFailure();
                # Is any of the future sentence words in the tree's word set?
                if wordDepth < len(sentenceTokens) - 1:
                    for futureWord in sentenceTokens[wordPos+1:]:
                        if futureWord in treeWords:
                            sentencePerf.addOutOfSeq();
                # Build a new tree by (virtually) typing in the word
                tree =  self.wordExplorer.makeWordTree(word);
                treeWords = self.extractWordSet(self.wordExplorer.makeJSONTree(tree));
                continue;
            # Found word in tree:
            sentencePerf.addWordDepth(wordDepth);
        
        # Finished looking at every toking in the sentence.
        self.performanceTally.append(sentencePerf);
    
# ---------------------------------- Testing ------------------------------------

if __name__ == '__main__':
    
    import os;
    import sys;
#    from subprocess import call;
    
    thisFileDir = os.path.realpath(os.path.dirname(__file__));
    try:
        stacksPos = thisFileDir.index("stacks")
    except ValueError:
        print "The 'stacks' directory not found above this file (that you're running). Assuming source tree of echo_tree_sentence_seg to be under stacks.";
        sys.exit();

    stacksDir = thisFileDir[0:stacksPos + len('stacks')];
    emailTokenizerDir = stacksDir + "/echo_tree_sentence_seg/src/EchoTreeTextProcessingJava/target";
    
    tokensTargetDir = stacksDir + '/echo_tree/src/echo_tree/Resources/EmailEchoTreeOverlapTests/EmailMsgTokens/';
    emailsSourceDir = stacksDir + '/echo_tree/src/echo_tree/Resources/EmailEchoTreeOverlapTests/EmailMsgs/';
    fullPathEmailFileList = []; 
    for fileName in os.listdir(emailsSourceDir):
        fullPathEmailFileList.append(os.path.join(emailsSourceDir, fileName));
        
#    # The automatic invocation of the Java based tokenizer isn't working. Get mangling of file names.
#    # Instead, run the following in a terminal:
#    #     java -jar emailTokenizer.jar foo ~/fuerte/stacks/echo_tree/src/echo_tree/Resources/EmailEchoTreeOverlapTests/EmailMsgTokens/ 
#    #                                      ~/fuerte/stacks/echo_tree/src/echo_tree/Resources/EmailEchoTreeOverlapTests/EmailMsgs/*.txt
#    # That will take files in Resource's EmailEchoTreeOverlapTests/EmailMsgs, tokenize them, and deposit token files
#    # in  ~/fuerte/stacks/echo_tree/src/echo_tree/Resources/EmailEchoTreeOverlapTests/EmailTokens with _Tokens added to
#    # the basename.
     
#    # The Java arg, and the jar name:
#    sysCallArgs = ['java', '-jar', emailTokenizerDir + '/emailTokenizer.jar'];
#    sysCallArgs.append(tokensTargetDir);
#    sysCallArgs.extend(fullPathEmailFileList);
#    
#    print str(sysCallArgs);
#    
#    call(sysCallArgs);

    
    
    
    dbPath = os.path.join(os.path.realpath(os.path.dirname(__file__)), "../Resources/EnronCollectionProcessed/EnronDB/enronDB.db");
    emailsPath = os.path.join(os.path.realpath(os.path.dirname(__file__)), "../Resources/EmailEchoTreeOverlapTests/EmailMsgs");
    emailsTokenDir = os.path.join(os.path.realpath(os.path.dirname(__file__)), "../Resources/EmailEchoTreeOverlapTests/EmailMsgTokens");
    evaluator = Evaluator(dbPath);
    
    # Unit tests:
    
#    testJson = '{"word": "reliability", "followWordObjs": [{"word": "new", "followWordObjs": [{"word": "power", "followWordObjs": []}, {"word": "generation", "followWordObjs": []}, {"word": "business", "followWordObjs": []}, {"word": "product", "followWordObjs": []}, {"word": "company", "followWordObjs": []}]}, {"word": "issues", "followWordObjs": [{"word": "related", "followWordObjs": []}, {"word": "need", "followWordObjs": []}, {"word": "raised", "followWordObjs": []}, {"word": "such", "followWordObjs": []}, {"word": "addressed", "followWordObjs": []}]}, {"word": "legislation", "followWordObjs": [{"word": "passed", "followWordObjs": []}, {"word": "allow", "followWordObjs": []}, {"word": "introduced", "followWordObjs": []}, {"word": "require", "followWordObjs": []}, {"word": "provide", "followWordObjs": []}]}, {"word": "standards", "followWordObjs": [{"word": "conduct", "followWordObjs": []}, {"word": "set", "followWordObjs": []}, {"word": "needed", "followWordObjs": []}, {"word": "facilitate", "followWordObjs": []}, {"word": "required", "followWordObjs": []}]}, {"word": "problems", "followWordObjs": [{"word": "please", "followWordObjs": []}, {"word": "California", "followWordObjs": []}, {"word": "accessing", "followWordObjs": []}, {"word": "arise", "followWordObjs": []}, {"word": "occur", "followWordObjs": []}]}]}';
    
#    # Sentences
#    sentences = evaluator.extractWordSeqs(testJson);
#    # Root word:
#    print sentences.popleft();
#    indents=[1,2,3,4];
#    for i,wordDict in enumerate(reversed(sentences)):
#        indent = indents[0];
#        parentWord =  wordDict.keys()[0];
#        print '\t'*indent + parentWord;
#        for word in reversed(wordDict[parentWord]):
#            indent = indents[1];
#            print '\t'*indent + word;
#            
#    # Sentence generation:
#    sentences = evaluator.extractWordSeqs(testJson);
#    print str(sentences);
#    print str(evaluator.extractWordSet(testJson));
#   
#    # Different-sized trees: 
#    from echo_tree.echo_tree import WordExplorer; 
#    wordExplorer = WordExplorer(dbPath);
#    deepTree = wordExplorer.makeWordTree('reliability', maxDepth=4);
#    deepJson = wordExplorer.makeJSONTree(deepTree);
#    deepSentences = evaluator.extractWordSeqs(deepJson);
#    print str(deepSentences);
#    
#    broadTree = wordExplorer.makeWordTree('reliability', maxBranch=6);
#    broadJson = wordExplorer.makeJSONTree(broadTree);
#    broadSentences = evaluator.extractWordSeqs(broadJson);
#    print str(broadSentences);
    
    # Depth measures for words:
#    pythonTree = json.loads(testJson);
#    print (str(pythonTree)); 
#    depth = evaluator.getDepthFromWord(pythonTree, 'reliability');
#    print str(depth) # 0
#    depth = evaluator.getDepthFromWord(pythonTree, 'new');
#    print str(depth); # 1
#    depth = evaluator.getDepthFromWord(pythonTree, 'product');
#    print str(depth); # 2
#    depth = evaluator.getDepthFromWord(pythonTree, 'issues');
#    print str(depth); # 1
#    depth = evaluator.getDepthFromWord(pythonTree, 'occur');
#    print str(depth); # 2
#    depth = evaluator.getDepthFromWord(pythonTree, 'foo');
#    print str(depth); # None

    evaluator.initWordCaptureTally();
    tokens = "this, demonstrates, a, couple, things, ;, it, appears, to, be, disruptive, technology, -LRB-, but, i, need, to, demo, it, to, be, sure, -RRB-, ;, it, shows, how, products, for, the, disabled, can, lead, t0, commercial, products, for, the, general, population, ;, it, really, stresses, how, technology, is, an, anti, dote, for, depression, among, the, disabled, ;, it, does, not, require, HEAD, movement, ,, only, EYE, some, draw, backs, ;, it, only, works, with, Windows, -LRB-, UGH, -RRB-, it, still, requires, a, computer, screen, 18, '', in, front, of, your, face, i, doubt, it, is, faster, than, my, current, headtracker, or, more, precise, -LRB-, but, i, need, to, play, with, one, to, be, sure, -RRB-".split(', '); 
    #tokens = ['this','demonstrates','a','couple','things'];
    evaluator.tallyWordCapture(tokens);
    print evaluator.performanceTally[0].toString();
    print evaluator.toCSV(); 
    