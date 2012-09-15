#!/bin/bash

# Run cluster to download and unzip all Google Books 2grams
# into /dfs/rulk/0/paepcke/Data/Google2Grams

for i in {0..99..4}
do
    # Every run grabs 4 of the 20gram files from Google:
    qsub /dfs/rulk/0/paepcke/fuerte/stacks/echo_tree/src/bash_scripts/google2gramLoading/download2GramFiles.sh $i 4
done