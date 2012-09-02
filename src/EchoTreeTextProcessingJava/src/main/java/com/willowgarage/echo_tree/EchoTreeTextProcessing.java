package com.willowgarage.echo_tree;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;

/**
 * Hello world!
 *
 */
/**
 * @author paepcke
 * Facilities for preparing an email collection for use.
 * Includes:
 * 		- ***
 */
public class EchoTreeTextProcessing { 
	
	public void makeSentences(String[] fileList) {
		for (String fileName : fileList) {
			File emailFile = new File(fileName);
			FileInputStream fd = null;
			try {
				fd = new FileInputStream(emailFile);
			} catch (FileNotFoundException e) {
				log(String.format("File %s not found in makeSentences", fileName));
			}
			int emailLen = (char) emailFile.length();
			byte[] charBuffer = new byte[emailLen]; 
			try {
				int lenRead = fd.read(charBuffer);
			} catch (IOException e) {
				log(String.format("Could open, but not read file %s in makeSentences", fileName));
			} 
		}
	}
	
	private void log(String msg) {
		System.out.println(msg);
	}
	
    public static void main( String[] args )
    {
        
    }
}
