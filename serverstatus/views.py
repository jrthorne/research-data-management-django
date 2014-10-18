from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404
from models import *

import time
import os
import datetime

#1 Kilobyte = 1,024 Bytes
#1 Megabyte = 1,048,576 Bytes
#1 Gigabyte = 1,073,741,824 Bytes
#1 Terabyte = 1,099,511,627,776 Bytes

KILOBYTE		= 1024
MEGABYTE		= 1048576
GIGABYTE		= 1073741824
TERABYTE		= 1099511627776


##########################################
def dateFromString(dateString, format, useTime):
	strippedTime	= time.strptime(dateString, format)
	myTime			= time.mktime(strippedTime)
	if useTime:
		retVal		= datetime.datetime.fromtimestamp(myTime)
		retVal		= retVal.date()
	else:
		retVal		= datetime.date.fromtimestamp(myTime)
		#retVal		= retVal.date()
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
			newLog.space     = 	int(spaceNumber)
			newLog.number_of_files = int(files) 
			
			#### NOTE SAVE HERE ONLY
			newLog.save()
			
    	
	emlFile.close();
	return


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
    