#!/usr/bin/env python

from os import stat

import pymongo
import decoding_contour_next_link
import datetime
from dateutil import tz
import time
from decoding_contour_next_link import *

from datetime import datetime, timedelta, time
from pymongo import MongoClient

import json
from decoding_contour_next_link import HISTORY_DATA_TYPE

import os.path

class LatestActivity (object):

    def __init__(self, db="bg_db_test", *args, **kwargs):
        self.db=MongoClient(*args, **kwargs)[db]
    
    def get_max_bg_record(self):
        pipeline = [
            {
              "$match": {
                  "type": {
                      "$in": [
                          "BloodGlucoseReadingEvent",
                          "NormalBolusDeliveredEvent",
                          "BolusWizardEstimateEvent",
                          "BasalSegmentStartEvent",
                          "PumpEvent"
                      ]
                  }
              }
            },
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

    def statusDownload(self, mt):
        currenttimestamp=datetime.now().replace(tzinfo=None)
        status = mt.getPumpStatus();

        last_entry_cur = self.db.all_events.find({"type": "PumpStatusEvent"}).sort("timestamp", pymongo.DESCENDING).limit(1)
        try:
            last_entry = last_entry_cur.next()
        except StopIteration:
            last_entry = None
        print("Last entry: {}".format(last_entry))

        print("Writing: {}".format(status))
        to_write = {
            "type": "PumpStatusEvent",
            "timestamp": currenttimestamp,
            "hour": currenttimestamp.hour,
            "sensorBGL": status.sensorBGL
                if status.StatusCgm \
                    else None,
            "trendArrow": status.trendArrow,
            "trendArrowValue": status.trendArrowValue,
            "sensorBGLTimestamp": status.sensorBGLTimestamp,
            "activeInsulin": status.activeInsulin,
            "currentBasalRate": status.currentBasalRate,
            "tempBasalRate": status.tempBasalRate,
            "tempBasalPercentage": status.tempBasalPercentage,
            "tempBasalMinutesRemaining": status.tempBasalMinutesRemaining,
            "batteryLevelPercentage": status.batteryLevelPercentage,
            "insulinUnitsRemaining": status.insulinUnitsRemaining,
            "sensorStatus": status.sensorStatus,
            "sensorStatusValue": status.sensorStatusValue,
            "sensorCalibrationMinutesRemaining": status.sensorCalibrationMinutesRemaining \
                if status.StatusCgm \
                    else None,
            "sensorBatteryPercent": status.sensorBatteryPercent \
                if status.StatusCgm \
                    else None,
            "sensorControl": status.sensorControl,
            "sensorControlValue": status.sensorControlValue,
            "StatusCgm": status.StatusCgm,
            "StatusTempBasal": status.StatusTempBasal,
            "StatusInsulinDelivery": status.StatusInsulinDelivery,
            "StatusBolusingDual": status.StatusBolusingDual,
            "StatusBolusingSquare": status.StatusBolusingSquare,
            "StatusBolusingNormal": status.StatusBolusingNormal,
            "StatusSuspended": status.StatusSuspended,
            "lastBolusAmount": status.lastBolusAmount,
            "lastBolusTimestamp": status.lastBolusTimestamp,
            "bolusWizardBGL": status.bolusWizardBGL,
            "sensorRateOfChangePerMin": status.sensorRateOfChangePerMin,
        }
        self.db.all_events.insert_one(to_write)

        to_write = {
            "type": "PumpStatusEventRaw",
            "timestamp": currenttimestamp,
            "hour": currenttimestamp.hour,
            "statusRaw": status.wholePayloadHex
        }
        self.db.all_events.insert_one(to_write)

        # if there is a configuration for pushover, then we send some notifications
        if os.path.isfile(os.path.expanduser("~/.pushoverrc")):
            import pushover

            # ignore if sensor not present
            if status.StatusCgm:
                
                if status.sensorBGL & 0x200 == 0 \
                    and status.trendArrow != "Calibration needed":
                    
                    # high sugar value and no active insulin
                    if status.sensorBGL is not None \
                        and status.sensorBGL > 250 \
                        and (status.activeInsulin < 1.0
                            or (currenttimestamp - status.lastBolusTimestamp > datetime.timestamp(hours=1))):
                        print("Notifying high sugar level.")
                        ret = pushover.Client().send_message(
                            "High sugar {} and low active insulin {}".format(status.sensorBGL, status.activeInsulin),
                            title="High sugar level. Correction needed.",
                            url="https://paulonet.eu/bgmonitor/",
                            priority=1)
                        print(ret)

                    # low sugar value
                    if status.sensorBGL is not None \
                        and status.sensorBGL < 60 \
                        and status.sensorBGL + 15 * status.sensorRateOfChangePerMin < 70:
                        print("Notifying low sugar level.")
                        predicted = status.sensorBGL + int(15 * status.sensorRateOfChangePerMin)
                        ret = pushover.Client().send_message(
                            "Low sugar {}. In 15 minutes predicted {}.".format(status.sensorBGL, predicted if predicted >= 40 else '<40'),
                            title="Low sugar level.",
                            url="https://paulonet.eu/bgmonitor/",
                            priority=1)
                        print(ret)

                # calibration coming soon
                if status.sensorCalibrationMinutesRemaining > 0 \
                    and status.sensorCalibrationMinutesRemaining <= 10:
                    calibrationdatetime = currenttimestamp + timedelta(minutes=status.sensorCalibrationMinutesRemaining)
                    print("Notifying calibration needed soon.")
                    ret = pushover.Client().send_message(
                        "Calibration in {} minutes at {:%-H:%M}.".format(status.sensorCalibrationMinutesRemaining, calibrationdatetime),
                        title="Calibration soon",
                        url="https://paulonet.eu/bgmonitor/")
                    print(ret)

                # calibration time passed
                if status.sensorStatusValue & 0x04 != 0  \
                    and status.sensorCalibrationMinutesRemaining == 0 \
                    and status.trendArrow == "Unknown trend" \
                    and not (
                        last_entry is not None \
                        and last_entry["StatusCgm"] \
                        and last_entry["trendArrow"] == "Unknown trend"
                        and last_entry["sensorCalibrationMinutesRemaining"] == 0):
                    print("Notifying calibration needed NOW.")
                    ret = pushover.Client().send_message(
                        "Calibration already passed!",
                        title="Calibration needed!",
                        url="https://paulonet.eu/bgmonitor/",
                        priority=1)
                    print(ret)

                # calibration needed in the evening
                if datetime.now().time() > time(23, 00) \
                    and (datetime.now() + timedelta(minutes=status.sensorCalibrationMinutesRemaining)).time() < time(7, 00) \
                    and status.sensorStatusValue != 0x00 :
                    print("Evening calibration needed.")
                    ret = pushover.Client().send_message(
                        "Next calibration planned at {:%-H:%M}.".format((datetime.now() + timedelta(minutes=status.sensorCalibrationMinutesRemaining)).time()),
                        title="Evening calibration needed!",
                        url="https://paulonet.eu/bgmonitor/",
                        priority=1)
                    print(ret)

                # battery change needed in the evening
                if datetime.now().time() > time(22, 00) \
                    and status.batteryLevelPercentage <= 25:
                    print("Consider battery change.")
                    ret = pushover.Client().send_message(
                        "Current battery level: {}%.".format(status.batteryLevelPercentage),
                        title="Consider battery change.",
                        url="https://paulonet.eu/bgmonitor/",
                        priority=1)
                    print(ret)

    def historyDownload(self, mt):
        # download status first anyway
        self.statusDownload(mt)
        startdate=self.get_max_bg_record().replace(tzinfo=None) + timedelta(0,1)
        enddate=datetime.now().replace(tzinfo=None)
        if enddate - startdate > timedelta(days=1):
            enddate = startdate + timedelta(days=1)
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
        if self.checkIfRun():
            decoding_contour_next_link.downloadPumpSession(self.historyDownload)
        else:
            decoding_contour_next_link.downloadPumpSession(self.statusDownload)

if __name__ == '__main__':
    app = LatestActivity()
    app.run()
