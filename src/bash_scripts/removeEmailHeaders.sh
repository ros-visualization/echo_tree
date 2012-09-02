#!/bin/bash

# Processes a directory of email files. For each file, creates a new
# file, from which the following lines are removed:
#
#    o Email headers, and lines containing email-header-type words,
#      like 'Content-type: ' even in the middle of the lines.
#
# The new files are named <originalName>_NoHeads.<originalExtension>
# Uses Unix sed for speed.


if [ $# -ne 1 ] 
then
  echo "Usage: removeEmailHeaders <directoryOfEmailFiles>"
  exit
fi

FILES=$1/*

for file in $FILES
do
    dirname=${file%/*}
    #echo "Dirname: $dirname"
    fileName=${file##*/}
    #echo "Filename: $fileName"
    fileNameNoExt=${fileName%%.*}
    #echo "Filename no ext: $fileNameNoExt"
    extension=${fileName#*.}
    #echo "Extension: $extension"

    outputName=${dirname}/${fileNameNoExt}_NoHeads.${extension}
    #echo $outputName

    # Get rid of email headers.
    # The -r turns on extended regex, which adds the
    # '+':
    sed -r '
      # Email headers (some only at start of line ('^'), 
      # some anywhere in a line:
      /Content-Transfer-Encoding: .*/ d
      /Return-path: .*/ d
      /^From: .*/ d
      /Full-name: .*/ d
      /Message-ID: .*/ d
      /^Date: .*/ d
      /^To: .*/ d
      /MIME-Version: .*/ d
      /Content-Type: .*/ d
      /X-Mailer: .*/ d

      # Email addresses:
      #   /[\da-zA-Z]+@[\da-zA-Z]+/ d
      ' <$file >$outputName
done
echo Done!
