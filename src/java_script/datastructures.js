function WordObj() {
  this.word = "keyboard";  // An example word
  this.followWords = [];   // array of WordObj instances, ordered by
  		           // frequency
  // The methods:
  this.getNextLevelWordObjs = getNextLevelWordObjs;
  this.getNextLevelWords    = getNextLevelWords;
}


function getNextLevelWordObjs(rootWord) {
  return rootWord.followWords;
}

function getNextLevelWords(rootWord) {
  var wordArr = [];
  for (wordObj in rootWord.getNextLevelWordObjs()) {
      wordArr.push(wordObj.word);
  }
  return wordArr;
}

var myWord = new WordObj();
var initialWord = myWord.word;
var followWords = myWord.getNextLevelWords();
var followWordObjs = myWord.getNextLevelWordObjs();
