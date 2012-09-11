#!/usr/bin/env python

import json;
from collections import deque;
from collections import OrderedDict;

from echo_tree import WORD_TREE_BREADTH;
from echo_tree import WORD_TREE_DEPTH;

class Evaluator(object):
    
    def __init__(self):
        pass
    
    def extractWordSet(self, jsonEchoTreeStr):
        pythonEchoTree = json.loads(jsonEchoTreeStr);
        flatTree  = self.extractWordSeqsHelper(pythonEchoTree);
        flatList  = flatTree.split();
        rootWord = flatList[0];
        flatSet = set(flatList[1:]);
        return (rootWord, flatSet);
    
    def extractWordSeqs(self, jsonEchoTreeStr):
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
            
# ---------------------------------- Testing ------------------------------------

if __name__ == '__main__':
    
    testJson = '{"word": "reliability", "followWordObjs": [{"word": "new", "followWordObjs": [{"word": "power", "followWordObjs": []}, {"word": "generation", "followWordObjs": []}, {"word": "business", "followWordObjs": []}, {"word": "product", "followWordObjs": []}, {"word": "company", "followWordObjs": []}]}, {"word": "issues", "followWordObjs": [{"word": "related", "followWordObjs": []}, {"word": "need", "followWordObjs": []}, {"word": "raised", "followWordObjs": []}, {"word": "such", "followWordObjs": []}, {"word": "addressed", "followWordObjs": []}]}, {"word": "legislation", "followWordObjs": [{"word": "passed", "followWordObjs": []}, {"word": "allow", "followWordObjs": []}, {"word": "introduced", "followWordObjs": []}, {"word": "require", "followWordObjs": []}, {"word": "provide", "followWordObjs": []}]}, {"word": "standards", "followWordObjs": [{"word": "conduct", "followWordObjs": []}, {"word": "set", "followWordObjs": []}, {"word": "needed", "followWordObjs": []}, {"word": "facilitate", "followWordObjs": []}, {"word": "required", "followWordObjs": []}]}, {"word": "problems", "followWordObjs": [{"word": "please", "followWordObjs": []}, {"word": "California", "followWordObjs": []}, {"word": "accessing", "followWordObjs": []}, {"word": "arise", "followWordObjs": []}, {"word": "occur", "followWordObjs": []}]}]}';
    
    evaluator = Evaluator();
    sentences = evaluator.extractWordSeqs(testJson);
    # Root word:
    print sentences.popleft();
    indents=[1,2,3,4];
    for i,wordDict in enumerate(reversed(sentences)):
        indent = indents[0];
        parentWord =  wordDict.keys()[0];
        print '\t'*indent + parentWord;
        for word in reversed(wordDict[parentWord]):
            indent = indents[1];
            print '\t'*indent + word;
            
    sentences = evaluator.extractWordSeqs(testJson);
    print str(evaluator.extractWordSet(testJson));        
        
        