#!/bin/bash

# Run all the evaluations. Invokes runJob.sh to run each job.

if [ `hostname` == "rulk.stanford.edu" ]
then
    ECHO_TREE_SOURCE_TREE=/dfs/rulk/0/paepcke/fuerte/stacks/echo_tree
else
    ECHO_TREE_SOURCE_TREE=$HOME/fuerte/stacks/echo_tree
fi

# Setup up PYTHONPATH differently, depending on whether 
# operating on Rulk for the cluster, or on a normal machine:
export PATH=$ECHO_TREE_SOURCE_TREE/src/echo_tree:$PATH
export PYTHONPATH=$ECHO_TREE_SOURCE_TREE/src:$PYTHONPATH

$ECHO_TREE_SROUCE_TREE/src/echo_tree/evaluation/runJob.sh \
    $ECHO_TREE_SROUCE_TREE/...
