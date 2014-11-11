from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404
from models import *

from xml.etree import ElementTree as ET

import time
import os
import datetime
import os, sys
from stat import *
import shutil
import csv



# to allow searching of xml keys, the prefexis need to have reference in the namespaces
NAMESPACES              = {}
NAMESPACES['foxml']     = 'info:fedora/fedora-system:def/foxml#'
NAMESPACES['dc']        = "http://purl.org/dc/elements/1.1/"
NAMESPACES['ms21']      = "http://www.unsw.edu.au/lrs/ms21/ontology/"

# The keys we are looking for
KEYS                    = ['dc:subject' ,'dc:description','ms21:estimatedVolume',
'ms21:estimatedVolumeUnit','ms21:storageNamespace','ms21:storageStatus','ms21:status',
'ms21:dataStorageRequired','ms21:dataStorageAffiliation','ms21:dataStorageAffiliationSchool',
'ms21:hasAward']
EXTRATAGS               = ['pid:','status:', 'storageStatus:storageStatus:']

# the mapping of the keys to database values. If this is a list, the first element is the KEYS
# index, the second is the EXTRATAGS index
rdmp_id 				= [0,0]
dc_status				= [1,1]
dc_storage_status		= [1,2]
estimated_volume		= 2
storage_namespace		= 4
ms21_storage_status     = 5
ms21_status             = 6
data_storage_required   = 7
affiliation             = 8
school                  = 9
has_award               = 10
# used to get the estimated volume size in bytes
volume_unit             = 3

# to store the values found by recursively traversing the XML tree
VALUES                  = {}


#1 Kilobyte = 1,024 Bytes
#1 Megabyte = 1,048,576 Bytes
#1 Gigabyte = 1,073,741,824 Bytes
#1 Terabyte = 1,099,511,627,776 Bytes

KILOBYTE        = 1024
MEGABYTE        = 1048576
GIGABYTE        = 1073741824
TERABYTE        = 1099511627776


##########################################
def dateFromString(dateString, format, useTime):
    strippedTime    = time.strptime(dateString, format)
    myTime            = time.mktime(strippedTime)
    if useTime:
        retVal        = datetime.datetime.fromtimestamp(myTime)
        retVal        = retVal.date()
    else:
        retVal        = datetime.date.fromtimestamp(myTime)
        #retVal        = retVal.date()
    # end if
    
    return retVal
# end dateFromString

##########################################
def runReport(file,readfolder):
    filename = readfolder + file
    
    fileLogsRecorded = RDSlog.objects.filter(import_file_name=filename)
    if fileLogsRecorded.count() > 0:
        return
    # end if 
    
    emlFile = open(filename, 'r')
    
    for line in emlFile: 
        
        if "RDS Storage Report Short run on " in line:
            theDate = line.replace("RDS Storage Report Short run on ","")
            theDate = theDate.strip("\r\n")
            theDate = theDate.replace("EST ", "")
            
        elif "DMP" in line:
            RDMP = line.strip('DMP # \r\n')
            cache = next(emlFile).strip('Cache used: ')
            cache = cache.strip("\r\n")
            space = next(emlFile).strip('Space used: ')
            files = next(emlFile).strip('Number of Files: \r\n')
            spaceLength = len(space)
            space.replace(" ", "")
            spaceNumber = float(space[:-3])
            spaceUnit = space[-3:-2]
            spaceUnit.strip(' ')
            
            
            spaceUnit.splitlines()
            if spaceUnit == 'K':
                    spaceNumber = spaceNumber * KILOBYTE
            elif spaceUnit == 'M':
                    spaceNumber = float(spaceNumber) * MEGABYTE
            elif spaceUnit == 'T':
                    spaceNumber = float(spaceNumber) * TERABYTE
            elif spaceUnit == 'G':
                    spaceNumber = spaceNumber * GIGABYTE
            else:
                spaceNumber = 0
            
            # now make the log
            newLog = RDSlog(import_file_name=filename)
            newLog.run_date  = dateFromString(theDate,"%a %b %d %H:%M:%S %Y", True)
            newLog.plan      = RDMP
            newLog.cahce     = cache
            newLog.space     =     int(spaceNumber)
            newLog.number_of_files = int(files) 
            
            #### NOTE SAVE HERE ONLY
            newLog.save()
            
        
    emlFile.close();
    return

##########################################
def walktree(top, writeto):
    '''recursively descend the directory tree rooted at top,
       calling the callback function for each regular file
       and copy the files where they can be renamed for convenience'''

    for f in os.listdir(top):
        pathname = os.path.join(top, f)
        mode = os.stat(pathname)[ST_MODE]
        if S_ISDIR(mode):
            # It's a directory, recurse into it
            walktree(pathname, writeto)
        elif S_ISREG(mode):
            # It's a file, call the callback function
            #callback(pathname)
            dst = os.path.join(writeto, f)
            #print dst
            shutil.copy2(pathname,dst)
                        
        else:
            # Unknown file type, print a message
            print 'Skipping %s' % pathname

def visitfile(file):
    print 'visiting', file
    #shutil.copy2(file,"rdmp/info1")

''' Rename the files that I copied to rdmp_files to have sensible names'''
def renameRDMP(folder):
    start = '<dc:subject>pid: '
    end = '</dc:subject>'
    for f in os.listdir(folder):
        if 'rdmp' in f:
            #print f
            rdmpFile = open(folder+f, 'r')
            for line in rdmpFile:
                if start in line:
                    #print line
                    # Don't have colons in the filename. Causes problems.
                    a = removeTags(start,end,line).replace(':', '_') + '.xml'
                    #print f,     a
                    os.rename(folder+f, folder+a)
        else:
            os.remove(folder+f)
            
def findelements(elem, level=0):
    print "Finding Elements at level %d" %(level) 
    if len(elem): # check all of elem's children
        for k in KEYS:
            values = elem.findall(k, NAMESPACES)
            for v in values:
                vk  = k
                for et in EXTRATAGS:
                    if et in (v.text or ''):
                        vk = k + et
                       
                VALUES[vk]       = v.text or ''
                print "Finding Elements at level %d with value %s" %(level, VALUES[vk]) 
        
        for child in elem:
            findelements(child, level+1)
    
    return
# end findelements  

def extractFromRDMP(folder):
        values = dict(VALUES)
        for f in os.listdir(folder):
            print "READING: " + folder+f
            # only read xml files
            if f[-4:] != ".xml":
                continue
                
            
            fp = open(folder+f, 'r')
            #parser = ET.XMLParser(encoding="utf-8")
            #tree = ET.fromstring(fp.read(), parser=parser)
            tree = ET.parse(folder+f)
            root = tree.getroot()
            findelements(root)
            
            # convert estimated volume to bytes
            RDMPvolume      = VALUES[KEYS[estimated_volume]] 
            RDMPvolumeUnit  = VALUES[KEYS[volume_unit]] 
            spaceUnit 		= RDMPvolumeUnit[0].upper()
            # is RDMP a number?
            if len(RDMPvolume) < 15:
            	try:
            		RDMPvolume = float(RDMPvolume)
            	except ValueError:
            		RDMPvolume = 0
            	# end try
            else:
            	RMDPvolume = 0
            	
            if spaceUnit == 'K':
                    volumeSpace = int(RDMPvolume * KILOBYTE)
            elif spaceUnit == 'M':
                    volumeSpace = int(RDMPvolume * MEGABYTE)
            elif spaceUnit == 'T':
                    volumeSpace = int(RDMPvolume * TERABYTE)
            elif spaceUnit == 'G':
                    volumeSpace = int(RDMPvolume * GIGABYTE)
            else:
                volumeSpace = 0
            storageRequired = VALUES[KEYS[data_storage_required]]
            if storageRequired == 'yes':
                boolStorageRequired = True
            elif storageRequired == 'no':
                boolStorageRequired = False
            else:
                boolStorageRequired = None
            
            try:
                boolHasAward = (VALUES[KEYS[has_award]].upper() == "YES")
            except KeyError:
                boolHasAward = False
                
            rdmpID           = convertID(VALUES[\
                                KEYS[rdmp_id[0]]+EXTRATAGS[rdmp_id[1]]])
            dcStorageStatus  = VALUES[\
                                KEYS[dc_storage_status[0]]+EXTRATAGS[dc_storage_status[1]]]
            
            
            newLog            = Rdmp_info(rdmp_id   = rdmpID, 
                            dc_status               = VALUES[\
                                KEYS[dc_status[0]]+EXTRATAGS[dc_status[1]]], 
                            dc_storage_status       = dcStorageStatus[len('storageStatus:storageStatus: '):],
                            estimated_volume        = volumeSpace,
                            storage_namespace       = VALUES[KEYS[storage_namespace]],
                            ms21_storage_status     = VALUES[KEYS[ms21_storage_status]],
                            ms21_status             = VALUES[KEYS[ms21_status]],
                            data_storage_required   = boolStorageRequired,
                            affiliation             = VALUES[KEYS[affiliation]],
                            school                  = VALUES[KEYS[school]],
                            has_award               = boolHasAward)
            newLog.save()                    

        

def convertID(rdmpID):
    numberID = rdmpID.strip('rdmp:')
    digits = len(numberID)
    padding = ''
    #print digits
    if digits == 1:
        padding = '000000'
    if digits == 2:
        padding = '00000'
    if digits == 3:
        padding = '0000'
    if digits == 4:
        padding = '000'
    retval = 'D'+padding+numberID
    return retval
                    
                
def removeTags(start,end,line):
    a =  (line.split(start))[1].split(end)[0]
    return a

def removeTags2(start,end,line):
    if start    in line:
        a =  (line.split(start))[1].split(end)[0]
        return a
    else:
        return 'a'

##########################################
# Create your views here.
def importRDSlog(request):
    readFolder = '/www/LTRDS/code/email/'

    print 'Start Reading Files'
    for file in os.listdir(readFolder):
        if file.endswith(".eml"):
            runReport(file,readFolder)
    print 'Reading Files Complete'
    
    return HttpResponseRedirect('/admin')

##########################################
def importRDMPinfo(requeest):
    readFolder = '/www/LTRDS/code/rdmp/'
    writeFolder = '/www/LTRDS/code/rdmp_files/'

    print 'Start Reading RDMP Files' 
    # copy files to a temporary place where we can rename thme
    #walktree(readFolder,writeFolder)
    # rename the files to the rdmp_X
    #renameRDMP(writeFolder)
    # Read all these xml files, and get the data from them
    extractFromRDMP(writeFolder)
    print 'Extracted data from RDMP Files Complete'
    
    return HttpResponseRedirect('/admin')