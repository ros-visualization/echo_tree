#!/bin/bash

# Run the workflow for creating a cleaned up Enron email 
# collection from the original Enron email tree. 
# Assumption: collection is in $HOME/Project/Dreslconsulting/Data/Enron/enron_mail_20110402/maildir/
# Result will be a series of file pairs: email1.txt, email1_NoHeads.txt, email2.txt, email2_NoHeads.txt, etc.
# in $HOME/fuerte/stacks/echo_tree/src/echo_tree/Resources/EnronCollectionProcessed.
# From there these files should be moved manually to the EnronCleaned and EnronRaw
# directories below (email<n>.txt to EnronRaw, email<n>_NoHeads.txt to EnronClean.)

../echo_tree/make_database.py $HOME/Project/Dreslconsulting/Data/Enron/enron_mail_20110402/maildir/ \
                              $HOME/fuerte/stacks/echo_tree/src/echo_tree/Resources/EnronCollectionProcessed/enronData.db -c
