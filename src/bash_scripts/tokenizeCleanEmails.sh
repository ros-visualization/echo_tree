#!/bin/bash

# After createCleanEnronCollection.sh has run we expect 
# $HOME/fuerte/stacks/echo_tree/src/echo_tree/Resources/EnronCollectionProcessed/EnronCleaned
# to contain all cleaned email chunks in files email<nn>_NoHeads.txt. This script
# runs these files through the Java Stanford NLP sentence segmenter and tokenizer.
# The result will be a set of new chunk files called email<nn>_Sentences.txt in
# $HOME/fuerte/stacks/echo_tree/src/echo_tree/Resources/EnronCollectionProcessed/EnronTokenized

if [ ! -d $HOME/fuerte/stacks/echo_tree/src/echo_tree/Resources/EnronCollectionProcessed/EnronTokenized ]
then
    mkdir $HOME/fuerte/stacks/echo_tree/src/echo_tree/Resources/EnronCollectionProcessed/EnronTokenized
fi


java -jar emailTokenizer.jar com.willowgarage.echo_tree.EmailTokenizer \
                      ../echo_tree/Resources/EnronCollectionProcessed/EnronTokenized \
                      ../echo_tree/Resources/EnronCollectionProcessed/EnronCleaned/*.txt
