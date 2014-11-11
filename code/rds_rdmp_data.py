#!/usr/bin/env python
####################################################################
Filename            = 'rds_rdmp_data.py'# J1.2
# Written:          10-10-2014
# By:               Jason Thorne
# Description:      Information regarding the Research Data Management
# System is exported to .elm files on the server infplfs0XX (XX=04 to 10).
# This script runs on the server and performs three tasks:
# import: read the eml files, parses the
# text to extract information, dumps the informatino in to an sqlite3
# database file.
# export:  uses the sqlite3 database to extract the information to CSV
# transfer: email the latest csv file to the email address in TOADDR
####################################################################
# updates: 
# JX.X|dd-mm-yyyy|who| Description
# J1.1|08-11-2014|JRT| Import the info table
# J1.2|11-11-2014|JRT| Renamed from mv csvFromElmLogger.py to
# rds_rdmp_data.py
####################################################################
Version             = 'J1.2'
####################################################################

import sqlite3
import sys
import time
import os
import datetime
import smtplib
from email.mime.text import MIMEText
import os, sys
from stat import *
import shutil
from xml.etree import ElementTree as ET

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
READFOLDER      = '/Data/maint/Reporting/prd/reports/'
EXPORTDIR       = '/home/nfs/z3007136_sa/rdscsv/'
EXPORTPREFIX    = 'rdslog_'
MYTABLE         = 'serverstatus_rdslog'
INFOTABLE       = 'serverstatus_rdmp_info'
DBFILE          = "db.sqlite3"
FROMADDR        = 'root@infplfs010.sc.it.unsw.edu.au'
TOADDR          = 'j.thorne@unsw.edu.au'
# export did include transfer, as we need to know the name of the 
# export file to transfer it. instead we just transfer the latest
# file, but there is more of a window for error doing it this way
THECOMMANDS     = ['import', 'export', 'transfer', 'info']
CMDIMPORT       = 0
CMDEXPORT       = 1
CMDTRANSFER     = 2
CMDINFO         = 3


##########################################
def dateFromString(dateString, format, useTime):
    strippedTime    = time.strptime(dateString, format)
    myTime            = time.mktime(strippedTime)
    if useTime:
        retVal        = datetime.datetime.fromtimestamp(myTime)
    else:
        retVal        = datetime.date.fromtimestamp(myTime)
    # end if
    
    return retVal
# end dateFromString

##########################################
def runReport(file, myCursor):
    # only log files with .elm extension
    if file[:-4] != '.elm':
        print "ERROR - Not an eml file: %s" %file
        return
    # end if

    filename = READFOLDER + file
    
    # How many times has this file been logged before?
    sqlCom = 'select count(*) from %s where import_file_name=?' %MYTABLE
    
    myCursor.execute(sqlCom, (file,))
    myRec = myCursor.fetchone()
    noTimesRecorded = int(myRec[0])
    
    # if more than 0 times, then don't log it again
    if noTimesRecorded > 0:
        #print "%s has been recorded %s times" %(filename, noTimesRecorded)
        return
    # end if 
    
    emlFile = open(filename, 'r')
    print "processing %s" %filename
    # the fields to insert
    sqlFields = "run_date, plan, cache, space, number_of_files, import_file_name"
    
    for line in emlFile:      
        if "RDS Storage Report Short run on " in line:
            theDate = line.replace("RDS Storage Report Short run on ","")
            theDate = theDate.strip("\r\n")
            theDate = theDate.replace("EST ", "")
        elif "RDS Storage Report -Long run on " in line:
            theDate = line.replace("RDS Storage Report -Long run on ","")
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
            spaceUnit = space[-2:-1]
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
            
            run_date         = dateFromString(theDate,"%a %b %d %H:%M:%S %Y", True)
            sqlValues = (run_date, RDMP, cache, int(spaceNumber), int(files), file)
            
            sqlCom = 'insert into %s (%s) values (?,?,?,?,?,?)' % (MYTABLE, sqlFields)
            myCursor.execute(sqlCom, sqlValues)
        # end if search term in line
    # next line
    
    # print how many logs recorded for this file
    sqlCom = 'select count(*) from %s where import_file_name=?' %MYTABLE
    
    myCursor.execute(sqlCom, (filename,))
    myRec = myCursor.fetchone()
    noTimesRecorded = int(myRec[0])
    
    print "%d logs were recorded for %s" %(noTimesRecorded, filename)
        
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
    print elem.tag
    if 'nonDigitalData' in elem.tag:
        print "IN HERE"
    i = 0
    if len(elem): # check all of elem's children
        for k in KEYS:
            values = elem.findall(k, NAMESPACES)
            i += 1
            print "A", i
            for v in values:
                vk  = k
                i += 1
                print "B", i
                for et in EXTRATAGS:
                    if et in (v.text or ''):
                        vk = k + et
                        print "C", i
                        i += 1
                       
                VALUES[vk]       = v.text or ''
                print "Finding Elements at level %d with value %s" %(level, VALUES[vk]) 
        
        for child in elem:
            findelements(child, level+1)
    
    return
# end findelements  

def extractFromRDMP(folder, myCursor):
        
        
        for f in os.listdir(folder):
            print "READING: " + folder+f
            # only read xml files
            if f[-4:] != ".xml":
                continue
  
            #parser = ET.XMLParser(encoding="utf-8")
            #tree = ET.fromstring(fp.read(), parser=parser)
            tree = ET.parse(folder+f)
            root = tree.getroot()
            findelements(root)
            
            # convert estimated volume to bytes
            RDMPvolume      = VALUES[KEYS[estimated_volume]] 
            RDMPvolumeUnit  = VALUES[KEYS[volume_unit]] 
            try:
                spaceUnit 	= RDMPvolumeUnit[0].upper()
            except IndexError:
                spaceUnit   = ''
                
            # is RDMP a number?
            if len(RDMPvolume) < 15:
            	try:
            		RDMPvolume = float(RDMPvolume)
            	except ValueError:
            		RDMPvolume = 0
            	# end try
            else:
            	RDMPvolume = 0
            	
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
            
            
            """newLog            = Rdmp_info(rdmp_id   = rdmpID, 
                            dc_status               =  
                            dc_storage_status       = 
                            estimated_volume        = 
                            storage_namespace       = 
                            ms21_storage_status     = 
                            ms21_status             = 
                            data_storage_required   = 
                            affiliation             = 
                            school                  = 
                            has_award               = )
            newLog.save() """
            sqlFields = "rdmp_id, dc_status, dc_storage_status, estimated_volume, storage_namespace, "
            sqlFields += "ms21_storage_status, ms21_status, data_storage_required, "
            sqlFields += "affiliation, school, has_award"
            sqlCom = 'insert into %s (%s) values (?,?,?,?,?,?,?,?,?,?,?)' % (INFOTABLE, sqlFields)
            sqlValues = (rdmpID, 
                        VALUES[KEYS[dc_status[0]]+EXTRATAGS[dc_status[1]]],
                        dcStorageStatus[len('storageStatus:storageStatus: '):],
                        str(volumeSpace),
                        VALUES[KEYS[storage_namespace]],
                        VALUES[KEYS[ms21_storage_status]],
                        VALUES[KEYS[ms21_status]],
                        boolStorageRequired,
                        VALUES[KEYS[affiliation]],
                        VALUES[KEYS[school]],
                        boolHasAward)
            myCursor.execute(sqlCom, sqlValues)

# end  extractFromRDMP      

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
if __name__ == "__main__":
    # get the command line argument
    if len(sys.argv) <= 1:
        print "Usage:>%s %s" %(sys.argv[0], str(THECOMMANDS))
        exit(1)
    # end if
    
    theCom = sys.argv[1:]
    
    if THECOMMANDS[CMDIMPORT] in theCom:
        myCon      = sqlite3.connect(DBFILE)
        myCursor   = myCon.cursor()
    
        print 'Start Reading Files'
        for file in os.listdir(READFOLDER):
            runReport(file, READFOLDER, myCursor)
            myCon.commit()
        print 'Reading Files Complete'
        
        myCon.close()
    # end if
    
    if THECOMMANDS[CMDEXPORT] in theCom:
        # name the exported csv file with the date
        myNow           = datetime.datetime.now()
        myNowStr        = myNow.strftime("%Y%m%d%H%M%S")
        exportFile      = EXPORTPREFIX + myNowStr + ".csv"

        # now use the command line for the sqlite3 export. I would prefer
        # to use the python interface, but I can't get the slqite mode
        # specific commands to execute
        osCom           = 'echo -e ".mode csv\n.header on\n.out ' + EXPORTDIR + exportFile
        osCom           += '\nselect * from %s;" | sqlite3 %s' %(MYTABLE, DBFILE)
        os.system(osCom)

    if THECOMMANDS[CMDTRANSFER] in theCom:
        # and transfer the file by email
        me              = FROMADDR
        you             = TOADDR

        # The file to transfer is the newst file preceded with rdslog_
        logFiles        = os.listdir(EXPORTDIR)
        # find the newest log file
        exportFile      = None
        logTime         = 0
        for i in logFiles:
            # exportprefix is at the beginning of log files
            if i.find(EXPORTPREFIX) == 0:
                # The position of the time in the filename
                timpos  = len(EXPORTPREFIX) + 1
                thisLogTime = int(i[timpos:-4])
                if thisLogTime > logTime:
                    exportFile = i
                    logTime = thisLogTime
                # end if
            # end if
        # next i

        if exportFile == None:
            msg             = MIMEText('The cron job was run, but no log file found')
            msg['Subject']  = 'No log file found'
        else:
            fp              = open(EXPORTDIR + exportFile, 'rb')
            # create a plain text message attachment
            msg             = MIMEText(fp.read())
            fp.close()
            lt              = str(logTime)
            niceTime        = lt[4:6] + '/' + lt[2:4] + '/20' + lt[:2]
            niceTime        += ' ' + lt[6:8] + ':' + lt[8:10] + ':' + lt[-2:]
            msg['Subject']  = 'RDS Report csv file made %s' %niceTime
        # end if
        msg['From']     = me
        msg['To']       = you

        s               = smtplib.SMTP('localhost')
        s.sendmail(me, [you], msg.as_string())
        s.quit()
    # endif
    
    if THECOMMANDS[CMDINFO] in theCom:
        readFolder = '/www/LTRDS/code/rdmp/'
        writeFolder = '/www/LTRDS/code/rdmp_files/'
    
        print 'Start Reading RDMP Files' 
        # copy files to a temporary place where we can rename thme
        #walktree(readFolder,writeFolder)
        # rename the files to the rdmp_X
        #renameRDMP(writeFolder)
        
        myCon      = sqlite3.connect(DBFILE)
        myCursor   = myCon.cursor()
    
        # Read all these xml files, and get the data from them
        extractFromRDMP(writeFolder, myCursor)
        myCon.commit()
        myCon.close()
        print 'Extracted data from RDMP Files Complete'
    # end info
 # end if __main__   
