#!/usr/bin/python

#######################################################################################################################################
#                                                                                                                                     #
#    assembled_DBR_filtering.py: comparison of degenerate base regions (DBRs) in assembled RADseq data for PCR duplicate detection    #
#    Copyright (C) 2016 Kelly Anne Pierce (kellyannepierce@gmail.com)                                                                 #
#                                                                                                                                     #
#######################################################################################################################################

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from collections import defaultdict
from collections import Counter
from subprocess import call, Popen, PIPE
import subprocess
import os, os.path
from os import linesep, path, R_OK, X_OK
import sys
import json
import re
import itertools
#import numpy as np
import time
import pdb
import heapq
import warnings
import multiprocessing as mp
from logging import debug, critical, error, info
import string
import gzip

# To do
# 1. Check that SAM files contain a map for all the sequences so that FASTQ filtering doesn't leave some bad quality data behind
#    Alternatively, instead of tracking tags to remove, track tags to keep
# 2. Make this work for data that span multiple libraries by calling the function separately for each library following the template below:
#    DBR_filter(assembled_dir = '/path/to/assembly_library1',
#               dict_in = '/path/to/dbr_dict_library1',
#               out_seqs = '/path/to/filtered_library1.fastq',
#               n_expected = 2)

def checkFile(filename):
    '''
    return true if this is a file and is readable on the current filesystem
    '''
    try:
        if os.path.exists(os.path.abspath(filename)) and os.path.isfile(os.path.abspath(filename)) and os.access(os.path.abspath(filename), R_OK):
            return True
        fullPath = string.join(os.getcwd(), filename[1:])
        return os.path.exists(fullPath) and os.path.isfile(fullPath) and os.access(fullPath, R_OK)
    except IOError:
        return False

def parallel_DBR_dict(in_dir, seqType, dbr_start, dbr_stop, test_dict = False, save = None):
    #if not checkDir(in_dir):
    #    raise IOError("Input is not a directory: %s" % in_dir)
    if seqType == 'read2':
        warnings.warn('Expect directory containing only Read 2 files; any other files present in %s will be incorporated into DBR dictionary.' % in_dir)
    elif seqType == 'pear':
        warnings.warn('Expect directory containing only merged Read 1 and Read 2 files; any other files present in %s will be incorporated into DBR directory' % in_dir)
    else:
        raise IOError("Input sequence type specified as %s. Options are 'pear' or 'read2'." % seqType)
    file_list = os.listdir(in_dir)
    dbrProcess = [mp.Process(target=DBR_dict, args=(in_dir+in_file, 
                                                    dbr_start,
                                                    dbr_stop,
                                                    test_dict,
                                                    save)) for in_file in file_list]
     
    for dP in dbrProcess:
        dP.start()
    for dP in dbrProcess:
        dP.join()

def DBR_dict(in_file, dbr_start, dbr_stop, test_dict = False, save = None):
    # DBR is in read 2
    # if merged, it will be the last -2 to -9 (inclusive) bases, starting with base 0 and counting from the end
    # if not merged, it will be bases 2 to 9
    if not checkFile(in_file):
        raise IOError("where is the input file: %s" % in_file)
    info('Creating {ID: dbr} dictionary from %s.' % in_file)
    #dbr = {}
    revDBR = {}
    #fq_line = 1
    fq_line = 0
    if in_file.endswith('gz'):
        openFxn = gzip.open
    else:
        openFxn = open
    with openFxn(in_file, 'r') as db:
        for line in db:
            #if fq_line == 1:
            if fq_line %4 == 0
                ID = re.split('(\d[:|_]\d+[:|_]\d+[:|_]\d+)', line)[1]
                #fq_line = 2
                fq_line += 1 #increment 1 line
            #elif fq_line == 2:
            elif fq_line %4 == 2
                seq = list(line) # split the sequence line into a list
                tag = ''.join(seq[dbr_start:dbr_stop])
                #dbr[ID] = tag
                if ID in revDBR.get(tag):
                    revDBR[tag].add(ID)
                else:
                    revDBR[tag] = ID
                #fq_line = 3
                fq_line += 3 #increment 3 lines to next set of 4
            #elif fq_line == 3:
            #    fq_line = 4
            #elif fq_line == 4:
            #    fq_line = 1
    if test_dict:
        print 'Checking DBR dictionary format.'
        x = itertools.islice(dbr.iteritems(), 0, 4)
        for key, value in x:
            print key, value
        #print dbr['8:1101:15808:1492'] # this is the first entry in /home/antolinlab/Downloads/CWD_RADseq/pear_merged_Library12_L8.assembled.fastq
    if save:
        if not os.path.exists(save):
            os.makedirs(save)
        fq_name = os.path.splitext(in_file)[0]
        fq_dbr_out = fq_name + save + '.json'
        print 'Writing dictionary to ' + fq_dbr_out
        with open(fq_dbr_out, 'w') as fp:          
            #json.dump(dbr, fp)
            json.dump(revDBR, fp)

def parallel_DBR_count(in_dir, dbr_start, dbr_stop, save = None, saveType = 'json'):
    #if not checkDir(in_dir):
    #    raise IOError("Input is not a directory: %s" % in_dir)
    infiles = os.listdir(in_dir)
    dbrCountProcess = [mp.Process(target=DBR_count, args=(os.path.join(in_dir+in_file), 
                                                          dbr_start,
                                                          dbr_stop,
                                                          save,
                                                          saveType)) for in_file in infiles]
     
    for dc in dbrCountProcess:
        dc.start()
    for dc in dbrCountProcess:
        dc.join()

def DBR_count(in_file, dbr_start, dbr_stop, save = None, saveType = None):
    # DBR is in read 2
    # if merged, it will be the last -2 to -9 (inclusive) bases, starting with base 0 and counting from the end
    # if not merged, it will be bases 2 to 9
    if not checkFile(in_file):
        raise IOError("where is the input file: %s" % in_file)
    info('Creating {dbr : count} dictionary from %s.' % in_file)
    dbr = {}
    fq_line = 1
    if in_file.endswith('gz'):
        openFxn = gzip.open
    else:
        openFxn = open
    with openFxn(in_file, 'r') as db:
        for line in db:
            if fq_line == 1:
                fq_line = 2
            elif fq_line == 2:
                dbr_value = line[dbr_start:dbr_stop]
                if dbr_value in dbr:
                    dbr[dbr_value]+=1
                else:
                    dbr[dbr_value]=1
                fq_line = 3
            elif fq_line == 3:
                fq_line = 4
            elif fq_line == 4:
                fq_line = 1
    if saveType:
        if not os.path.exists(save):
            os.makedirs(save)
        fq_base = os.path.splitext(os.path.split(in_file)[1])[0]
        #fq_name = os.path.splitext(in_file)[0]
        if saveType == 'json':
            fq_dbr_out = save + fq_base + '.json'
            print 'Writing dictionary to ' + fq_dbr_out
            with open(fq_dbr_out, 'w') as fp:          
                json.dump(dbr, fp)
        elif saveType == 'text':
            fq_dbr_out = save + fq_base + '.txt'
            with open(fq_dbr_out, 'w') as fp:
                for key, value in dbr.items():
                    fp.write(key + ',' + str(value) + '\n')

phred_dict = {'"':1.0,"#":2.0,"$":3.0,"%":4.0,"&":5.0,"'":6.0,"(":7.0,")":8.0,"*":9.0,"+":10.0,
              ",":11.0,"-":12.0,".":13.0,"/":14.0,"0":15.0,"1":16,"2":17.0,"3":18.0,"4":19.0,"5":20.0,
              "6":21.0,"7":22.0,"8":23.0,"9":24.0,":":25.0,";":26,"<":27.0,"+":28.0,">":29.0,"?":30.0,
              "@":31.0,"A":32.0,"B":33.0,"C":34.0,"D":35.0,"E":36,"F":37.0,"G":38.0,"H":39.0,"I":40.0,
              "J":41.0,"K":42.0}
# conversion reference: http://drive5.com/usearch/manual/quality_score.html

''' stuff from the pilot library
dict_in = '/home/antolinlab/Desktop/CSU_ChronicWasting/PilotAnalysis/initial_qualFilter_dbr_dict'
assembled_dir = '/home/antolinlab/Desktop/CSU_ChronicWasting/PilotAnalysis/Assembled'
out_seqs = '/home/antolinlab/Desktop/CSU_ChronicWasting/PilotAnalysis/DBR_filtered_sequences.fastq'
barcode_file = '/home/antolinlab/Desktop/CSU_ChronicWasting/PilotAnalysis/pilot_barcode_file'
'''

def qual_median(QUAL, phred_dict):
    
    listQUAL = list(QUAL)
    list_intQUAL =[]
    for q in listQUAL:
        list_intQUAL.append(phred_dict[q])
    #return np.median(list_intQUAL)
    #pdb.set_trace()
    list_intQUAL.sort() # this modifies the list in place -- you can't assign it to a new variable. alt, qsort = sorted(list_intQUAL) if we need the original list preserved for some reason
    qlen = len(list_intQUAL)
    if qlen % 2 == 0: # even length list -- take the average of the two middle values
        median_qual = (list_intQUAL[(qlen/2)-1]+list_intQUAL[(qlen/2)])/2
    else: # odd length list -- take the middle value (list length / 2 will be automatically rounded up by python integer division)
        median_qual = list_intQUAL[qlen/2]
    return median_qual
    
def find_SampleID(filename, r):
    #sampleID_match = re.match(".*(\d{3}[a-z]?).*", filename)
    # this revision is VERY specific to my technical replicates
    # TODO: find a way to pass the regex capture group as an argument so that this (and related functions) are more flexible
    #sampleID_match = re.match(".*(\d{1,3}T?).*", filename)
    sampleID_match = re.match(r, filename)
    if sampleID_match:
        sampleID = sampleID_match.groups()[0]
        return sampleID
    else:
        return None
    
def find_LibraryID(filename):
    #libraryID_match = re.match(".*(Library\d{2,3}).*", filename)
    libraryID_match = re.match(".*(Library\d{1,3}[A|B]?).*", filename)
    if libraryID_match: # if we get a match (this allows the script to proceed if a file has a mismatched name)
        libraryID = libraryID_match.groups()[0] # extract the library ID match
        return libraryID 
    else:
        return None

def find_BarcodeFile(library, directory):
    if library:
        if os.path.isdir(directory):
            bcs = os.listdir(directory)
            for b in bcs:
                if library in b:
                    bcf = directory + '/' + b
                    return bcf
        else: # if it's just a single file
            if os.path.isfile(directory):
                return directory
            else:
                return None
    else:
        return None
    
def find_DBRdictionary(library, directory):
    if library: # library can also be returned as 'None' for files with improper naming
        if os.path.isdir(directory):
            dcs = os.listdir(directory)
            for d in dcs:
                if library in d:
                    dcf = directory + '/' + d
                    return dcf
        else: # if it's just a single file
            if os.path.isfile(directory):
                return directory
            else:
                return None
    else:
        return None
                
def DBR_Filter(assembled_dir, # the SAM files for the data mapped to pseudoreference
               out_dir, # the output file, full path, ending with .fasta
               n_expected, # the number of differences to be tolerated
               barcode_dir, # the barcodes for individuals in the library referenced in dict_in
               dict_dir, # a single dictionary of DBRs (for one library only)
               sample_regex, # regular expression to find the sample ID
               barcode_file=None, # if just a single library is being used, can directly pass the barcode file
               test_dict=True, # optionally print testing info to stdout for checking the dictionary construction
               phred_dict=phred_dict, # dictionary containing ASCII quality filter scores to help with tie breaks
               samMapLen=None): # expected sequence length will help when primary reads are still not perfectly aligned with reference
    
    # addition: grep the name of the file in the assembled_dir for a number in column 1 of the barcode file
    # get the barcode and append it to the front of the sequence
    # if we don't do this, the demultiplexing won't work for phase 2
    # alternatively we can just give a new barcode, but then we'd need to track a secondary barcode file for all the individuals
    # that sounds not-fun
    
    #pdb.set_trace()
    #logfile = os.path.splitext(out_seqs)[0] + '_logfile.csv'
    logfile = out_dir + '/DBR_filtered_sequences_logfile.csv'
    
    # for each sample -- each file in assembled_dir is a sam file for a single sample
    for i in os.listdir(assembled_dir):
            
        if 'unmatched' not in i: # skip the SAM files with sequences that didn't match
            
            print i
            
            # extract the sample ID with a regex
            sampleID = find_SampleID(i, sample_regex) # find the sample ID, potentially with some extra characters to distinguish from library ID
            
            # extract the library ID with a regex
            libraryID = find_LibraryID(i)
            
            # use the library ID to find the right barcode file
            bcf = find_BarcodeFile(libraryID, barcode_dir)
            
            # use the library ID to find the right DBR dictionary
            dict_in = find_DBRdictionary(libraryID, dict_dir)
            
            if sampleID and libraryID and bcf and dict_in: # if all of these != None
            
                print 'sample', sampleID 
                print 'library', libraryID
                print 'barcode file', bcf 
                print 'dictionary file', dict_in
            
                if not os.path.exists(out_dir):
                    os.makedirs(out_dir)
            
                out_seqs_final = out_dir + '/DBR_filtered_sequences_' + libraryID + '_' + sampleID + '.fastq'
            
                #os.path.isfile(fname)
    
                with open(out_seqs_final, 'a') as out_file:
                    
                    #bc_dict = {} # define empty container for barcode dictionary
            
                    #with open(bcf, 'r') as bc:
                    #    for line in bc:
                    #        row=line.split()
                    #        bc_dict[row[0]]=row[1]
            
                        print 'Opening DBR dictionary ' + dict_in  
                        with open(dict_in, 'r') as f:
                            dbr = json.load(f)
                            
                            #original_barcode = bc_dict[sampleID]
                            #print original_barcode
                            # suggestion on error checking: 
                            # normally i capture the .match() value and say 'if object:"
                            # "else: print('did not match correctly')
                            
                            # initialize an empty dictionary with each iteration of the for-loop
                            assembly_dict_2 = {}
                            assembly_dict_3 = defaultdict(list)
                            
                            # print some info to track progress
                            path=os.path.join(assembled_dir, i)
                            print 'Creating filtering dictionaries from ' + path
                            
                            # get the sample number for use later
                            #number = re.split('(\d)', i)[1] # enclose the regex in parentheses to keep it in the output
                            
                            # start counter for the number of primary reads
                            n_primary = 0
                            
                            delete_list = []
                            keep_list = []
                            
                            # open the sam file and process its contents
                            with open(path, 'r') as inFile:
                                for line in inFile:
                                    if not line.startswith("@"): # ignore the header lines
                                        fields = line.split("\t")
                                        
                                        # extract the info for the dictionary for each line
                                        QNAME = re.split('(\d[:|_]\d+[:|_]\d+[:|_]\d+)', fields[0])[1] # FASTQ ID = QNAME column in sam file
                                        FLAG = fields[1] # bitwise flag with map info; == 0 if primary read
                                        RNAME = fields[2] # ref sequence name -- where did the sequence map?
                                        POS = fields[3] # position of map
                                        MAPQ = fields[4] # mapping quality
                                        CIGAR = fields[5] # additional mapping info
                                        SEQ = fields[9] # the actual sequence
                                        QUAL = fields[10] # sequence quality score
                                        
                                        # extract the DBR corresponding to the QNAME for each row
                                        dbr_value = dbr.get(QNAME) 
                                        
                                        # after trimming, the sequences are 116 bases long
                                        # the POS for all matched sequences should be 1 because we used a pseudoreference build from our RADtags
                                        # if all 116 bases match, POS = 1 and CIGAR = 116M (meaning 116 bases match the reference)
                                        # repetitive regions may map to multiple regions but not exactly -- this would cause the same sequence ID to be present > 1x in the dictionary
                                        # sequences present >1x in the dictionary break the count of DBRs, and cause problems with filtering downstream
                                        # the inexact matches of repetitive regions can be detected by POS != 1 or CIGAR != 116M
                                        # a more flexible/broader use way of filtering would be to do a REGEX search on the CIGAR score and report the number of digits preceeding the M
                                        # then you could only keep the entry that has the largest number of matches (but M can show up multiple times in the CIGAR score if separated by an insertion, so think about this more)
                                        # I had thought that filtering on POS == 1 will keep only the good matches, but it is possible to have multiple matches to POS == 1 with different levels of clipping
                                        
                                        # A MORE GENERAL SOLUTION THAT SHOULD WORK FOR A VARIETY OF CIRCUMSTANCES:
                                        # bitwise FLAG == 0 means that the read is the PRIMARY READ. There will only be one of these per sequence, so only mapped primary reads should be considered.
                                        if FLAG == '0':
                                            if samMapLen:
                                                if len(SEQ) == samMapLen: #if we specify an expected sequence length in the samfile
                                                    # tally the new primary read
                                                    #n_primary += 1
                                                
                                                    # WE NEED TWO DICTIONARIES TO REPRESENT ALL THE RELATIONSHIP BETWEEN RNAME, QNAME, dbr_value, QUAL, AND count
                                                    # build a dictionary with structure {DBR: (locus: count)}                    
                                                    if RNAME in assembly_dict_2:
                                                        if dbr_value in assembly_dict_2.get(RNAME):
                                                            assembly_dict_2[RNAME][dbr_value]=assembly_dict_2[RNAME][dbr_value]+1
                                                        else:
                                                            assembly_dict_2.setdefault(RNAME, {})[dbr_value]=1
                                                    else:
                                                        assembly_dict_2.setdefault(RNAME, {})[dbr_value]=1 # add the new DBR and its associated locus and count
                                    
                                                    # build a dictionary with structure {RNAME: {DBR:[[QNAME, QUAL]]}}        
                                                    if RNAME in assembly_dict_3:
                                                        if dbr_value in assembly_dict_3.get(RNAME):
                                                            assembly_dict_3[RNAME][dbr_value].append([QNAME, QUAL, SEQ])
                                                        else:
                                                            assembly_dict_3.setdefault(RNAME, {})[dbr_value]=[[QNAME, QUAL, SEQ]]
                                                    else:
                                                        assembly_dict_3.setdefault(RNAME, {})[dbr_value]=[[QNAME, QUAL, SEQ]]
                                                    # tally the new primary read
                                                    n_primary += 1
                                            else: #if we're not using stacks to re-assemble and we don't care about expected lengths...
                                                # WE NEED TWO DICTIONARIES TO REPRESENT ALL THE RELATIONSHIP BETWEEN RNAME, QNAME, dbr_value, QUAL, AND count
                                                # build a dictionary with structure {DBR: (locus: count)}                    
                                                if RNAME in assembly_dict_2:
                                                    if dbr_value in assembly_dict_2.get(RNAME):
                                                        assembly_dict_2[RNAME][dbr_value]=assembly_dict_2[RNAME][dbr_value]+1
                                                    else:
                                                        assembly_dict_2.setdefault(RNAME, {})[dbr_value]=1
                                                else:
                                                    assembly_dict_2.setdefault(RNAME, {})[dbr_value]=1 # add the new DBR and its associated locus and count
                                
                                                # build a dictionary with structure {RNAME: {DBR:[[QNAME, QUAL]]}}        
                                                if RNAME in assembly_dict_3:
                                                    if dbr_value in assembly_dict_3.get(RNAME):
                                                        assembly_dict_3[RNAME][dbr_value].append([QNAME, QUAL, SEQ])
                                                    else:
                                                        assembly_dict_3.setdefault(RNAME, {})[dbr_value]=[[QNAME, QUAL, SEQ]]
                                                else:
                                                    assembly_dict_3.setdefault(RNAME, {})[dbr_value]=[[QNAME, QUAL, SEQ]]
                                                # tally the new primary read
                                                n_primary += 1
                                    
                                # NOW THAT DICTIONARIES ARE MADE, REMOVE DUPLICATE SEQUENCES BASED ON DBR COUNTS
                                # for each assembled locus, get the associated dbr_value and count
                                print 'Checking DBR counts against expectations.'
                                total_removed = 0
                                for RNAME, value in assembly_dict_2.iteritems():
                                    #print 'RNAME', RNAME
                                    # ignore the data where the reference is "unmapped" -- RNAME = '*'
                                    if RNAME != '*':
                                        # get all the DBRs and counts that went into that locus in that sample
                                        for subvalue in value.iteritems():
                                            #print 'Subvalue', subvalue
                                            dbr_value = subvalue[0] 
                                            count = subvalue[1]
                                            qname_qual = assembly_dict_3[RNAME][dbr_value] #this is a list of lists: [[QNAME, QUAL, SEQ], [QNAME, QUAL, SEQ], ...]
                                            if count > n_expected:
                                                ##################################################
                                                ## THIS IS WHERE THE FILTERING HAPPENS           #
                                                ##################################################
                                                #print 'count', count, 'n exp', n_expected
                                                # the other dictionary contains the full quality information for each RNAME:DBR pair (this will be multiple entries of sequence IDs and qualities
                                                #print RNAME, dbr_value, len(qname_qual)
                                                #print qname_qual
                                                ID_quals = {} # we'll make yet another dictionary to store the QNAME and the median QUAL
                                                for i in qname_qual:
                                                    id_val=i[0] # this is the QNAME (Illumina ID)
                                                    id_seq=i[2] # the full sequence
                                                    id_qual=i[1] # the full quality
                                                    ID_quals[id_val] = (qual_median(i[1], phred_dict), id_seq, id_qual)
                                                n_remove = count - n_expected
                                                total_removed += n_remove
                                                to_keep = heapq.nlargest(n_expected, ID_quals, key=lambda x:ID_quals[x])
                                                #to_keep = max(ID_quals, key=lambda x:ID_quals[x]) 
                                                for k in to_keep:
                                                    keep = ID_quals[k] # get the full data for the highest median sequences
                                                    #write out the data to keep, appending the original barcode to the beginning of the sequence
                                                    out_file.write('@'+k+'\n'+ keep[1]+'\n+\n'+ keep[2]+'\n')
                                            else: # if count <= n_expected, we can just keep every entry associated with that RNAME
                                                for i in qname_qual:
                                                    out_file.write('@'+i[0]+'\n'+i[2]+'\n+\n'+i[1]+'\n') # see above for i[index] definitions
                                                
                                with open(logfile,'a') as log:
                                    log.write(sampleID+','+str(total_removed)+','+str(n_primary)+','+time.strftime("%d/%m/%Y")+','+(time.strftime("%H:%M:%S"))+'\n')
                                    print 'Removed ' + str(total_removed) + ' PCR duplicates out of ' + str(n_primary) + ' primary mapped reads.'                                                    
                                        
                                if test_dict: # check construction by printing first entries to screen
                                    print 'Checking dictionary format (version 3).'
                                    x = itertools.islice(assembly_dict_3.iteritems(), 0, 4)
                                    for keyX, valueX in x:
                                        print keyX, valueX
                                    print 'Checking dictionary format (version 2).'
                                    y = itertools.islice(assembly_dict_2.iteritems(), 0, 4)
                                    for keyY, valueY in y:
                                        print keyY, valueY
        

#TODO: why does DBR_filter need to write out a single fastq file -- why redo all that demultiplexing??
'''
# OTHER METRICS FOR DESCRIBING OVERALL SEQUENCE QUALITY (QUAL = ASCII character string)

# counter object (from collections import Counter)
countQUAL = Counter(QUAL)

# frequency table of ASCII characters
freqQUAL = countQUAL.most_common()

# most frequently observed ASCII character
modeQUAL = countQUAL.most_common(1)

# most frequently observed integer score
intQUAL = phred_dict[modeQUAL[0][0]]

# list of integer qualities
listQUAL = list(QUAL) # split the ASCII string into a list
list_intQUAL = []
for q in listQUAL:
    list_intQUAL.append(phred_dict[q])
    
# median quality
medQUAL = np.median(list_intQUAL)
'''