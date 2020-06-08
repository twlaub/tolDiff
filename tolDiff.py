from __future__ import print_function  # Fix print function for python 2
import sys        # Used for std file operations etc.
import os         # used for strerror(), path parsing and path manipulations
import platform   # Used to get python version info
import argparse   # Gets command line arguments and options
import re         # Used for replacing optics files path in NORSE input
import math       # Needed for math.isclose()

"""
Written (mostly) by Thomas W. Laub

Python script to do toleranced diffing of program text output files.

Usage can be discerned using the -h or --help option.

This script will take two input files and diff them subject to specfified
numerical tolerances: absolute and/or relative. Both tolerances have default
values of 0.0. Both tolerances must be exceeded for a diff to be recognized.
Output is written to stdout unless and output file is specified.

Tends to ignore whitespace on lines with numerical matches because it only
checks for numerical differences on lines already marked as different by the
regular diff algorithm. It does so by breaking the line up into fields separated
by whitespace Hence the whitespace is ignored.
"""



################################
# Begin Hunt–McIlroy diff algorithm functions
################################
'''
The next three functions were written by Joren Dorff at the
URL: https://gist.github.com/jorendorff/5040491
It is an implementation of the Hunt–McIlroy algorithm and is explained here:
http://pynash.org/2013/02/26/diff-in-50-lines.html as a primitive `diff` in
50 lines of Python.

I have modified it so that the output matches the output of GNU diff in format
and returned the results in a list instead of printing them.
'''

def longest_matching_slice(a, a0, a1, b, b0, b1):
    sa, sb, n = a0, b0, 0

    runs = {}
    for i in range(a0, a1):
        new_runs = {}
        for j in range(b0, b1):
            if a[i] == b[j]:
                k = new_runs[j] = runs.get(j-1, 0) + 1
                if k > n:
                    sa, sb, n = i-k+1, j-k+1, k
        runs = new_runs

    assert a[sa:sa+n] == b[sb:sb+n]
    return sa, sb, n

def matching_slices(a, a0, a1, b, b0, b1):
    sa, sb, n = longest_matching_slice(a, a0, a1, b, b0, b1)
    if n == 0:
        return []
    return (matching_slices(a, a0, sa, b, b0, sb) +
            [(sa, sb, n)] +
            matching_slices(a, sa+n, a1, b, sb+n, b1))

def get_diff(a, b):
    '''
    a and b are lists of the two files to be diffed (with any newlines removed)
    '''
    diffList = []
    ia = ib = 0
    slices = matching_slices(a, 0, len(a), b, 0, len(b))
    for sa, sb, n in slices:
        if ( ia == (sa-1) ):
            diffList.append( "{:d}c{:d}".format((ia+1),(ib+1)) )
        else:
            diffList.append( "{:d},{:d}c{:d},{:d}".format((ia+1),sa,(ib+1),sb) )
        for line in a[ia:sa]:
            diffList.append ( "< " + line )
        diffList.append ( "---" )
        for line in b[ib:sb]:
            diffList.append ( "> " + line )
        ia = sa + n
        ib = sb + n
    return diffList

################################
# End Hunt–McIlroy diff algorithm functions
################################


def processSectionHeader(tempList):
    '''
    Extract start, stop, and number of lines from diff section header
    '''
    if ( debug ): print( "\nprocessSectionHeader::tempList: ",tempList )
    iStartOld = 0
    iStopOld = 0
    iStartNew = 0
    iStopNew = 0
    numLines = 0
    if ( len(tempList) == 4 ):
       iStartOld = int( tempList[0] )
       iStopOld =  int( tempList[1] )
       numLinesOld = iStopOld - iStartOld + 1
       iStartNew = int( tempList[2] )
       iStopNew = int( tempList[3] )
       numLinesNew = iStopNew - iStartNew + 1
       if ( debug ):
           print( "       processSectionHeader::tempList:iStartOld = {:d}".format( iStartOld ) )
           print( "        processSectionHeader::tempList:iStopOld = {:d}".format( iStopOld ) )
           print( "     processSectionHeader::tempList:numLinesOld = {:d}".format( numLinesOld ) )
           print( "      processSectionHeader::tempList: iStartNew = {:d}".format( iStartNew ) )
           print( "        processSectionHeader::tempList:iStopNew = {:d}".format( iStopNew ) )
           print( "     processSectionHeader::tempList:numLinesNew = {:d}".format( numLinesNew ) )
    else:
       iStartOld = int( tempList[0] )
       iStartNew = int( tempList[1] )
       numLinesOld = 1
       numLinesNew = 1
       if ( debug ):
           print( "       processSectionHeader::tempList:iStartOld = {:d}".format( iStartOld ) )
           print( "       processSectionHeader::tempList:iStartNew = {:d}".format( iStartNew ) )
           print( "     processSectionHeader::tempList:numLinesOld = {:d}".format( numLinesOld ) )
    return iStartOld, iStopOld, numLinesOld, iStartNew, iStopNew, numLinesNew

def processDiffSectionRemovals(diffSection,removeString):
    processedDiffSection = []
    for line in diffSection:
        if ( line[0:10] == removeString ): continue # Remove this
        processedDiffSection.append( line )
    return processedDiffSection

def isFloat(n):
    '''
    Checks to see if string is a floating point number
    '''
    if ( isInteger(n) ): return False
    try:
        float(n)
    except ValueError:
        return False
    else:
        return True

def isInteger(n):
    '''
    Checks to see if string is an integer
    '''
    try:
        int(n)
    except ValueError:
        return False
    else:
        return True

def isNumber(n):
    return ( isFloat(n) or isInteger(n) )

################################
# Define the main function
################################

def main():

    ################################
    # Parse command line arguments
    ################################
    parser = argparse.ArgumentParser()
    parser.add_argument( "OldFile", help="Old or reference text output file from a program containing text and numerical values." )
    parser.add_argument( "NewFile", help="New or changed text output file from a program containing text and numerical values." )
    parser.add_argument( "-d","--debug", help="Print debugging information to stdout.", action="store_true" )
    parser.add_argument( "-t","--defaultTolerances", help="FSets default absolute and relative tolerances to 1.E-15 and 1.E-8, respectively", action="store_true" )
    parser.add_argument( "-a","--absolute", help="Absolute tolerance value. Default is 0.0, overrides default tolerances", action="store" )
    parser.add_argument( "-r","--relative", help="Relative tolerance value. Default is 0.0, overrides default tolerances", action="store" )
    parser.add_argument( "-f","--file", help="Name of the output file. Default is stdout", action="store" )
    parser.add_argument( "-i","--integers", help="Flag indicating integers are also checked", action="store_true" )
    args = parser.parse_args()

    # Get cwd
    rundir = os.getcwd()

    # Check for debug option first so it can be used during command line parameter checks
    global debug  # Make debug a global variable so it can be used in functions
    if ( args.debug ):
        debug=True
    else:
        debug=False

    # Initialize input error counter
    ErrorNum = 0

    # Get text file names and error check
    oldFile = args.OldFile
    if ( not os.path.exists(oldFile) ):
        print( "ERROR: {0:s} does not exist.".format(oldFile) )
        ErrorNum += 1

    newFile = args.NewFile
    if ( not os.path.exists(newFile) ):
        print( "ERROR: {0:s} does not exist.".format(newFile) )
        ErrorNum += 1

    # If no tolerances specified, these will be the default
    noTol = True
    absTol = 0.0
    relTol = 0.0

    # Check for default tolerance flag
    defaultTolerances = False
#    if ( args.defaultTolerances ): defaultTolerances = True
    if ( args.defaultTolerances ):
        defaultTolerances = True
        noTol = False
        absTol = 1.E-15
        relTol = 1.E-8
        if ( debug ):  print( "main::setting default tolerances" )
    if ( debug ):
        print( "main::defaultTolerances: ",defaultTolerances )
        print( "main::absTol: ",absTol )
        print( "main::relTol: ",relTol )

    # Get Integer flag
    if ( args.integers ):
        intTol = True
    else:
        intTol = False

    # Get output file name and open either file set handle to sys.stdout
    if ( args.file ):
        diffFileName = args.file
        diffFile = open( diffFileName,'w' )
    else:
        diffFile = sys.stdout

    # Get Absolute tolerance value, no default set in argparse so it won't override any existing values
    absTolSet = False
    if ( args.absolute ):
        absTol = args.absolute
        absTolSet = True
        noTol = False
    if ( debug ):
        print( "main::After check of args.absolute" )
        print( "main::absTol: ",absTol )
        print( "main::relTol: ",relTol )

    # Get Absolute tolerance value, no default set in argparse so it won't override any existing values
    relTolSet = False
    if ( args.relative ):
        relTol = args.relative
        relTolSet = True
        noTol = False
    if ( debug ):
        print( "main::After check of args.relative" )
        print( "main::absTol: ",absTol )
        print( "main::relTol: ",relTol )

    # Convert toleraces to floats
    absTol = float(absTol)
    relTol = float(relTol)
    if ( debug ):
        print( "main::After tolerance conversion to floats" )
        print( "main::absTol: ",absTol )
        print( "main::relTol: ",relTol )

    # Report input errors and exit
    if ( ErrorNum > 0 ):
        print( "\nErrors detected in input." )
        ErrorNum += 1
        exit(ErrorNum)

    # Set and print script version
    numDiffVer = "0.1.0"
    if ( debug ): print( "main::{0:s} version: {1:s}".format( os.path.basename(sys.argv[0]), numDiffVer ) )

    # Get platform and python in use, makes a difference in console input
    pyver = platform.python_version()
    if ( debug): print( "main::Python version: {0:s}".format( pyver ) )
    platformType = platform.system()
    if ( debug): print( "main::Platform type: {0:s}".format( platformType ) )

    # Echo input
    if ( debug ):
        sys.stdout.write( "\n")
        sys.stdout.write( "main::Input and flags:\n")
        sys.stdout.write( "  {:35s} {:s}\n".format( "main::Old text file:", oldFile ) )
        sys.stdout.write( "  {:35s} {:s}\n".format( "main::New text file:", newFile ) )
        sys.stdout.write( "  {:35s} {:s}\n".format( "main::Default tolerance option:", str(defaultTolerances) ) )
        sys.stdout.write( "  {:35s} {:s}\n".format( "main::Absolute tolerance reset:", str(absTolSet) ) )
        sys.stdout.write( "  {:35s} {:<12.4e}\n".format( "main::Absolute tolerance:", absTol ) )
        sys.stdout.write( "  {:35s} {:s}\n".format( "main::Relative tolerance reset:", str(relTolSet) ) )
        sys.stdout.write( "  {:35s} {:<12.4e}\n".format( "main::Relative tolerance:", relTol ) )
        sys.stdout.write( "  {:35s} {:s}\n".format( "main::Integer option:", str(intTol) ) )
        sys.stdout.write( "  {:35s} {:s}\n".format( "main::noTol:", str(noTol) ) )
        sys.stdout.write( "  {:35s} {:s}\n".format( "main::Debug option:", str(debug) ) )
        sys.stdout.write( "  {:35s} {:s}\n".format( "main::Diff File name:", diffFileName ) )


    # NOTE: Python 3 requires the function form of print: print().
    #       Python 2 will work with the function form but will print the parentheses.

    ################################
    # Read input text files, removing newlines as you go
    ################################
    oldfile = open(oldFile,"r")
    with open(oldFile) as oldf:
        oldTextLines = [ line.rstrip('\n') for line in oldf.readlines() ]
    newfile = open(newFile,"r")
    with open(newFile) as newf:
        newTextLines = [ line.rstrip('\n') for line in newf.readlines() ]
    oldfile.close()
    newfile.close()

    ################################
    # Diff the files
    ################################
    diffList = get_diff( oldTextLines, newTextLines )
    if ( debug ):
        print ( "\nmain::diffList:" )
        for line in diffList:
            sys.stdout.write( line + "\n" )

    # If there are no tolerances set just write the diff
    if ( noTol ):
        for line in diffList:
            diffFile.write( line + "\n" )
        if diffFile is not sys.stdout: diffFile.close()
        exit()

    ################################
    # Process the diffs
    ################################

    # Count the diff sections
    nDiffSections = 0
    newSection = False
    sectionLineNumbers = []

    iLine = 0
    while iLine < len(diffList):
#    for iLine in range( len(diffList) ):  # Maybe this should be a while loop since changing iLine in loop???

        if ( debug ): print( "\n\nmain::diffList[{:d}]:{:s}".format( iLine,diffList[iLine] ) )

        if ( isInteger(diffList[iLine][0]) ):    # New diff sections begin with an integer in the first column

            if ( debug ):
                print( "+++++++++++++++++++++++ Found section separator ++++++++++++++++++++++++" )
                print( " main::diffList[{:d}]:{:s}".format( iLine,diffList[iLine] ) )

            nDiffSections += 1
            sectionLineNumbers.append( iLine )
            newSection = True

            # process the diff section header
            temp = re.split( "c|,", diffList[iLine] ) # split text at lowercase c and comma
            iStartOld,iStopOld,numLinesOld,iStartNew,iStopNew,numLinesNew = processSectionHeader( temp )

        else:

            if ( newSection ):

                ################################
                # Process an entire diff section
                ################################

                newSection = False
                # Extract the old and new parts of this diff section
                if ( debug ):
                    print( " main::Section {:d}".format( nDiffSections ) )
                    print( "   main::Old file section" )
                    print( "   main::firstOldDiffLine:",diffList[iLine] )
                oldDiffSection = diffList[iLine:iLine+numLinesOld]
                if ( debug ):
                    for line in oldDiffSection:
                        print( "   main::OldDiffSection:",line )

                # Move to the new file part of this section
                iLine += (numLinesOld + 1)  # The plus one is to skip the separator between old and new diffs
                if ( debug ):
                    print( "   main::New file section" )
                    print( "   main::firstNewDiffLine:",diffList[iLine] )
                newDiffSection = diffList[iLine:iLine+numLinesNew]
                if ( debug ):
                    for line in newDiffSection:
                        print( "   main::NewDiffSection:",line )

                # Process the extracted diff sections
                for iOldLine in range( len(oldDiffSection) ):    # for each line in oldDiffSection compare to each line in newDiffSection
                    oldLine = oldDiffSection[iOldLine]
                    oldLineSplit = oldLine.split()[1:] # remove leading angle brackets
                    if ( debug ): print( "      main::oldLineSplit:", oldLineSplit )
                    oldFields = len(oldLineSplit)
                    for iNewLine in range( len(newDiffSection) ):
                        if ( newDiffSection[iNewLine][0:9] == "xxREMOVExx" ): continue # This line already determined same w/in tolerances and removed
                        newLine = newDiffSection[iNewLine]
                        isLineDiff = False
                        if ( debug ): print( "         main::isLineDiff:", isLineDiff )
                        newLineSplit = newLine.split()[1:] # remove leading angle brackets
                        if ( debug ): print( "         main::oldLineSplit:", oldLineSplit )
                        newFields = len(newLineSplit)
                        if ( not (oldFields == newFields) ):   # Different number of fields --> true diff; check next new line
                            isLineDiff = True # not necessary
                            if ( debug ): print( "      main::number of fields NOT equal, isLineDiff", isLineDiff )
                            continue      # to next newLine
                        else:                                          # Same number of fields, so check fields
                            if ( debug ): print( "         main::number of fields equal, isLineDiff", isLineDiff )
                            for oldField,newField in zip(oldLineSplit,newLineSplit):             # Check each field for equality
                                if ( debug ): print ( "         main::oldField,newField:", oldField, newField )
#                                if ( not (oldField == newField) ):  # Fields are not equal, check if they are floating point numbers (integers would be equal)
                                if ( oldField != newField ):  # Fields are not equal, check if they are floating point numbers (integers would be equal)
                                    isNum = False
                                    if ( intTol ):
                                        isNum = ( isNumber(oldField) and isNumber(newField) )
                                    else:
                                        isNum = ( isFloat(oldField) and isFloat(newField) )
                                    if ( debug ): print( "         main::isNum", isNum )
                                    if ( not isNum ):
                                        isLineDiff = True
                                        if ( debug ): print( "         main::Both NOT numbers, isLineDiff:",isLineDiff )
                                    else:    # Both fields are numbers so do a tolerance check
                                        if ( debug ): print( "         main::Both ARE numbers, isLineDiff:",isLineDiff )
                                        # diffFlag is True if differences, False if within tolerances
                                        diffFlag = ( not math.isclose( float(oldField), float(newField), abs_tol=absTol, rel_tol=relTol ) )
                                        if ( debug ): print( "         main::diffFlag: ",diffFlag )
                                        if ( not diffFlag ): continue # on to next set of fields
                                        isLineDiff = True
                                        if ( debug ): print( "         main::isLineDiff", isLineDiff )

                        if ( debug ): print( "      main::isLineDiff:", isLineDiff )
                        if ( isLineDiff ): continue # to next newLine
                        # If not a line diff mark both old and new for removal and break back to oldLine loop
                        if ( debug ): print( "      main:: Not a difference" )
                        if ( debug ):
                            print( "   main::Found lines w/in tolerances." )
                            print( "   main::Removing: ",oldDiffSection[iOldLine] )
                            print( "   main::Removing: ",newDiffSection[iNewLine] )
                        oldDiffSection[iOldLine] = "xxREMOVExx"+oldDiffSection[iOldLine]
                        newDiffSection[iOldLine] = "xxREMOVExx"+newDiffSection[iNewLine]
                        break # out of newLine loop to next oldLine

                # Process Old Diff Section to remove lines w/in tolerances
                if ( debug ): print( "   main::Processed Old file section" )
                processedOldDiffSection = processDiffSectionRemovals(oldDiffSection,"xxREMOVExx")

                # Process New Diff Section to remove lines w/in tolerances
                if ( debug ): print( "   main::Processed New file section" )
                processedNewDiffSection = processDiffSectionRemovals(newDiffSection,"xxREMOVExx")

                # Write processed Old Diff Section
                if ( len(processedOldDiffSection) > 0 ):
                    diffFile.write( "********* Around line {:d}\n".format( iStartOld ) )
                    for line in processedOldDiffSection: diffFile.write( line  + "\n" )

                # Write processed New Diff Section
                if ( len(processedNewDiffSection) > 0 ):
                    diffFile.write( "--------- Around line {:d}\n".format( iStartNew ) )
                    for line in processedNewDiffSection: diffFile.write( line + "\n" )

                # Move to end of new diff section
                iLine += (numLinesNew - 1) # only to ending line of new section, last line of while loop will also increment

        ################################
        # End of diff section processing
        ################################


        iLine += 1  # increment iLine
    ################################
    # End of diff processing
    ################################

    if ( debug ):
        print( "\nmain::nDiffSections = {:d}".format( nDiffSections ) )
        print( sectionLineNumbers )

    if diffFile is not sys.stdout: diffFile.close()

    if ( debug ): print( "\nmain::Diff'd {0:s} and {1:s}".format( newFile,oldFile ) )

################################
# End of main function
################################

# Invoke main function if running script standalone
if ( __name__ == "__main__" ): main()

