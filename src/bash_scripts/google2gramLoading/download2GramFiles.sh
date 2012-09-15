#!/bin/bash

# Retrieves several 2-gram files from Google Books n-gram site.
# The URLs are of the form <baseURL>-0.csv.zip
#                          <baseURL>-1.csv.zip
# etc. First file is:
#   http://commondatastorage.googleapis.com/books/ngrams/books/googlebooks-eng-all-2gram-20090715-0.csv.zip
# Files will be deposited in /dfs/rulk/0/paepcke/Data/Google2Grams, and will be unzipped there.


# Parameters:
# $1: index of first file to get in the sequence
# $2: number of files to get

if [ $# -ne 2 ]
then
  echo "Usage: $0 <fileIndexStartNum> <howManyFiles>"
  exit;
fi

#PBS -N /dfs/rulk/0/paepcke/fuerte/stacks/echo_tree/src/bash_scripts/google2gramLoading/download2GramFiles.sh
#PBS -l nodes=1:ppn=1

urlRoot=http://commondatastorage.googleapis.com/books/ngrams/books/googlebooks-eng-all-2gram-20090715-
destDir=/dfs/rulk/0/paepcke/Data/Google2Grams
fileNameRoot="googlebooks-eng-all-2gram-20090715-"

#urlRoot="http://infolab.stanford.edu/~paepcke/tests-"
#destDir=${HOME}/tmp/Test
#fileNameRoot="tests-"

for (( fileNum=$1 ; fileNum<$1+$2 ; fileNum++ ))
do
   wget --quiet --directory-prefix=${destDir} $urlRoot${fileNum}.csv.zip
   unzip -d $destDir $destDir/${fileNameRoot}$fileNum.csv.zip > /dev/null
done