#!/bin/bash

# Processes a directory of email files. For each file, creates a new
# file, from which the following lines are removed:
#
#    o Email headers, and lines containing email-header-type words,
#      like 'Content-type: ' even in the middle of the lines.
#    o Empty lines
#    o Quoted lines
#    o All email addresses (b/c not wanted as tokens)
#
# The new files are named <originalName>_NoHeads.<originalExtension>
# Uses Unix sed for speed. Files in the directory that match an 
# optional exclusion pattern are ignored.
# Example: pattern: '.*_NoHeads.*' ignores email2_NoHeads.txt


if [ $# -lt 1 ] 
then
  echo "Usage: removeEmailHeaders <directoryOfEmailFiles> [<exclusionRegExp>]"
  exit
fi

FILES=$1/*
if [ $# -gt 1 ]
then
    excludePattern=$2
fi

#echo "Exclude pattern: '$excludePattern'"

for file in $FILES
do
    # Is file to be excluded?
    if [ $excludePattern ] && [[ $file =~ $excludePattern ]]
    then 
	#echo Match
	continue
    fi
    echo "Cleaning $file..."
    dirname=${file%/*}
    #echo "Dirname: $dirname"
    fileName=${file##*/}
    #echo "Filename: $fileName"
    fileNameNoExt=${fileName%%.*}
    #echo "Filename no ext: $fileNameNoExt"
    extension=${fileName#*.}
    #echo "Extension: $extension"

    # Only process .txt files:
    if [ $extension != "txt" ]
    then
       continue
    fi

    outputName=${dirname}/${fileNameNoExt}_NoHeads.${extension}
    $echo $outputName

    # Get rid of email headers.
    # The -r turns on extended regex, which adds the
    # '+'. Each sed portion below looks for one pattern
    # on each email line, and deletes that line if it
    # matches the pattern:
    sed -r '
      # Email headers (some only at start of line ('^'), 
      # some anywhere in a line:
      /Content-Transfer-Encoding: .*/ d
      /Return-path: .*/ d
      /From: .*/ d
      /Full-name: .*/ d
      /Message-ID: .*/ d
      /^Date: .*/ d
      /^Sent: .*/ d
      /To: .*/ d
      /Cc: .*/ d
      /Bcc: .*/ d
      /MIME-Version: .*/ d
      /Content-Type: .*/ d
      /X-Mailer:.*/ d
      /X-From: .*/ d
      /X-To:.*/ d
      /X-cc:.*/ d
      /X-bcc:.*/ d
      /X-Folder:.*/ d
      /X-Origin:.*/ d
      /X-FileName:.*/ d
      /Mime-Version: .*/ d

      /.*-----Original Message-----.*/ d

      # Email addresses:
      #   /[\da-zA-Z]+@[\da-zA-Z]+/ d

      # Empty lines:
      /^$/ d      

      # Quoted lines:
      /^>/ d

      # Email addresses (leaves empty line if only
      # email addresses, commas, and whitespace are
      # present. Not sure how to fix:
      s/[\da-zA-Z._]+@[\da-zA-Z._]+[\s,]*//g

      # URLs:
      s/http:\/\/[$&+,/.,=?@a-zA-Z0-9]+[\s].*//g

      # Special chars:
      s/[\\*/#@_\-><(){}$]+//g

      # Sequences of more than one punctuation mark:
      # replace with just one:
      s/([.!?:,;])[.!?:,;]+/\1/g

      # Numbers:
      s/[[:digit:]]*//g

      ' <$file >$outputName

      
done
echo Done!
