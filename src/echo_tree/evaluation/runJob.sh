#!/bin/bash

# Run a single evaluation somewhere on the cluster, or on a a normal machine.
# A single evaluation is one call to echo_tree_eval.py with one token file.
# Expect PYTHONPATH to be set up by the caller.
#
# $1: csvFilePath
# $2: dbFilePath
# $3: tokenFilePath

#PBS -N /dfs/rulk/0/paepcke/fuerte/stacks/echo_tree/src/echo_tree/evaluation/echo_tree_eval.py
#PBS -l nodes=1:ppn=1

/dfs/rulk/0/paepcke/fuerte/stacks/src/echo_tree/evaluation/echo_tree_eval.py $1 $2 $3
