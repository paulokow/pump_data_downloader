#!/usr/bin/env python

import decoding_contour_next_link
import datetime
from dateutil import tz
import time
from decoding_contour_next_link import *

from datetime import datetime, timedelta
from pymongo import MongoClient

import json
from decoding_contour_next_link import HISTORY_DATA_TYPE


class LatestActivity (object):

    def __init__(self):
        self.db=MongoClient().bg_db_test
    
    def get_max_bg_record(self):
        pipeline = [
            {
              "$group": {
                "_id": "$item",
                "date": { "$max": "$timestamp"}
              }
            }
          ]
        ret = datetime(2010,1,1)
        max_list=list(self.db.all_events.aggregate(pipeline))
        if len(max_list) > 0:
            rec = max_list[0]
            ret = rec["date"]
        else:
            print "Nothing found in All Events DB"
            
        return ret

    def getConfig(self):
        self.config = self.db.bg_config2.find_one();
        if self.config == None:
            self.config = {
#            "_id": None,
                "lastPumpRead": datetime.min
            }

    def historyDownload(self, mt):
        enddate=datetime.now().replace(tzinfo=None)
        startdate=self.get_max_bg_record().replace(tzinfo=None) + timedelta(0,1)
        print "Download from {0} to {1}".format(startdate.isoformat(), enddate.isoformat())

        
        print "Getting history info"
        historyInfo = mt.getPumpHistoryInfo(startdate, enddate, HISTORY_DATA_TYPE.PUMP_DATA)
        print "History start {0}".format(historyInfo.datetimeStart)
        print "History end {0}".format(historyInfo.datetimeEnd)
        print "Hisotry size {0}".format(historyInfo.historySize)
        
        print "Getting history"
        history_pages = mt.getPumpHistory(historyInfo.historySize, startdate, enddate, HISTORY_DATA_TYPE.PUMP_DATA)
    
        events = mt.processPumpHistory(history_pages, HISTORY_DATA_TYPE.PUMP_DATA)

        print "Getting sensor history info"
        historyInfoS = mt.getPumpHistoryInfo(startdate, enddate, HISTORY_DATA_TYPE.SENSOR_DATA)
        print "History sensor start {0}".format(historyInfoS.datetimeStart)
        print "History sensor end {0}".format(historyInfoS.datetimeEnd)
        print "Hisotry sensor size {0}".format(historyInfoS.historySize)
        
        print "Getting history"
        history_pagesS = mt.getPumpHistory(historyInfoS.historySize, startdate, enddate, HISTORY_DATA_TYPE.SENSOR_DATA)
    
        eventsS = mt.processPumpHistory(history_pagesS, HISTORY_DATA_TYPE.SENSOR_DATA)

        eventsAll = sorted(events + eventsS, key = lambda event: event.timestamp)

        print "# All events:"
        for ev in eventsAll:
            #print ev.timestamp, datetime.utcfromtimestamp(time.mktime(ev.timestamp.timetuple()))
            if  ev.timestamp.replace(tzinfo=None) > startdate:
                if isinstance(ev, BloodGlucoseReadingEvent):
                    print "Writing: ", ev
                    to_write = {
    	                "type": "BloodGlucoseReadingEvent",
    	                "timestamp": ev.timestamp.replace(tzinfo=None),
    	                "hour": ev.timestamp.hour,
    	                "value": ev.bgValue,
    	                "real": True,
    	                }
                    self.db.all_events.insert_one(to_write)
                if isinstance(ev, SensorGlucoseReading):
                    print "Writing: ", ev
                    to_write = {
                        "type": "BloodGlucoseReadingEvent",
                        "timestamp": ev.timestamp.replace(tzinfo=None),
                        "hour": ev.timestamp.hour,
                        "value": ev.sg,
                        "real": True,
                        "sensor": True
                        }
                    self.db.all_events.insert_one(to_write)                                        
                elif isinstance(ev, NormalBolusDeliveredEvent):
                    print "Writing: ", ev
                    to_write = {
    	                "type": "NormalBolusDeliveredEvent",
    	                "timestamp": ev.timestamp.replace(tzinfo=None),
    	                "hour": ev.timestamp.hour,
    	                "delivered": ev.deliveredAmount,
    	                "programmed": ev.programmedAmount,
    	                }
                    self.db.all_events.insert_one(to_write)
                elif isinstance(ev, BolusWizardEstimateEvent):
                    print "Writing: ", ev
                    to_write = {
                        "type": "BolusWizardEstimateEvent",
                        "timestamp": ev.timestamp.replace(tzinfo=None),
                        "hour": ev.timestamp.hour,
                        "bgInput": ev.bgInput,
                        "carbInput": ev.carbInput,
                        "carbRatio": ev.carbRatio,
                        "correctionEstimate": ev.correctionEstimate,
                        "bolusWizardEstimate": ev.bolusWizardEstimate,
                        "estimateModifiedByUser": ev.estimateModifiedByUser,
                        "finalEstimate": ev.finalEstimate
                        }
                    self.db.all_events.insert_one(to_write)
                elif isinstance(ev, BasalSegmentStartEvent):
                    print "Writing: ", ev
                    to_write = {
                        "type": "BasalSegmentStartEvent",
                        "timestamp": ev.timestamp.replace(tzinfo=None),
                        "hour": ev.timestamp.hour,
                        "rate": ev.rate,
                        "patternName": ev.patternName,
                        }
                    self.db.all_events.insert_one(to_write)
                elif isinstance(ev, InsulinDeliveryStoppedEvent):
                    print "Writing: ", ev
                    to_write = {
                        "type": "PumpEvent",
                        "timestamp": ev.timestamp.replace(tzinfo=None),
                        "hour": ev.timestamp.hour,
                        "eventtype": ev.__class__.__name__,
                        "description": ev.suspendReasonText,
                        }
                    self.db.all_events.insert_one(to_write)
                elif isinstance(ev, InsulinDeliveryRestartedEvent):
                    print "Writing: ", ev
                    to_write = {
                        "type": "PumpEvent",
                        "timestamp": ev.timestamp.replace(tzinfo=None),
                        "hour": ev.timestamp.hour,
                        "eventtype": ev.__class__.__name__,
                        "description": ev.resumeReasonText,
                        }
                    self.db.all_events.insert_one(to_write)
                elif isinstance(ev, AlarmNotificationEvent):
                    print "Writing: ", ev
                    to_write = {
                        "type": "PumpEvent",
                        "timestamp": ev.timestamp.replace(tzinfo=None),
                        "hour": ev.timestamp.hour,
                        "eventtype": ev.__class__.__name__,
                        "description": "Alarm notification",
                        }
                    self.db.all_events.insert_one(to_write)
                elif isinstance(ev, AlarmClearedEvent):
                    print "Writing: ", ev
                    to_write = {
                        "type": "PumpEvent",
                        "timestamp": ev.timestamp.replace(tzinfo=None),
                        "hour": ev.timestamp.hour,
                        "eventtype": ev.__class__.__name__,
                        "description": "Alarm notification cleared",
                        }
                    self.db.all_events.insert_one(to_write)
                elif isinstance(ev, SensorAlertSilenceStartedEvent):
                    print "Writing: ", ev
                    to_write = {
                        "type": "PumpEvent",
                        "timestamp": ev.timestamp.replace(tzinfo=None),
                        "hour": ev.timestamp.hour,
                        "eventtype": ev.__class__.__name__,
                        "description": "Sensor alarm silence start",
                        }
                    self.db.all_events.insert_one(to_write)
                elif isinstance(ev, SensorAlertSilenceEndedEvent):
                    print "Writing: ", ev
                    to_write = {
                        "type": "PumpEvent",
                        "timestamp": ev.timestamp.replace(tzinfo=None),
                        "hour": ev.timestamp.hour,
                        "eventtype": ev.__class__.__name__,
                        "description": "Sensor alarm silence end",
                        }
                    self.db.all_events.insert_one(to_write)
                
#	        else:
#	            print "Skipping: ", ev.timestamp, ev.timestamp.replace(tzinfo=None), " <= ", startdate

        #print json.dumps(record, indent=2)
        print "# End events"

        self.config['lastPumpRead'] = datetime.utcnow()
        if u'_id' in self.config:
            self.db.bg_config2.replace_one(filter={u'_id': self.config[u'_id']}, replacement=self.config, upsert=True)
            print 'Config updated', self.config
        else:
            self.db.bg_config2.insert_one(self.config)
            print 'New config saved', self.config

    def init(self):
        self.getConfig()
        print 'Last successful check run:', self.config['lastPumpRead']
        print "Config: ", self.config
        
    def checkIfRun(self):
        dl = datetime.utcnow() - self.config['lastPumpRead']
        if dl.days == 0 and dl.seconds < (60 * 60):
            print 'Short time since last run:', dl
            return False
        else:
            return True
    
    def run(self):
        self.init()
        if (self.checkIfRun()):
            decoding_contour_next_link.downloadPumpSession(self.historyDownload)

if __name__ == '__main__':
    app = LatestActivity()
    app.run()
