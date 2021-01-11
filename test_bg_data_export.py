import unittest
try:
    from unittest.mock import Mock, patch, MagicMock
except ImportError:
    from mock import Mock, patch, MagicMock

from bg_data_export2 import LatestActivity
from decoding_contour_next_link.read_minimed_next24 import Medtronic600SeriesDriver, PumpStatusResponseMessage

from datetime import datetime, time, timedelta

from pymongo import MongoClient

class TestBGDataExport(unittest.TestCase):

    def test_statusDownload(self):
        db=MongoClient(host="mongo", username="root", password="example").bg_db_test
        db.all_events.delete_many({})

        testobj = LatestActivity(host="mongo", username="root", password="example")
        
        drivermock = Mock(spec=Medtronic600SeriesDriver)
        status = Mock(spec=PumpStatusResponseMessage)
        status.sensorBGL = 300
        status.trendArrow = "Calibration needed"
        status.trendArrowValue = 0xE0
        status.sensorBGLTimestamp = datetime.now()
        status.activeInsulin = 0.7
        status.currentBasalRate = 0.65
        status.tempBasalRate = None
        status.tempBasalPercentage = 150
        status.tempBasalMinutesRemaining = 10
        status.batteryLevelPercentage = 50
        status.insulinUnitsRemaining = 10
        status.sensorStatus = "OK"
        status.sensorStatusValue = 0x14
        status.sensorCalibrationMinutesRemaining = 0
        status.sensorBatteryPercent = 100
        status.sensorControl = "0x00"
        status.sensorControlValue = 0x00
        status.StatusCgm = True
        status.StatusTempBasal = False
        status.StatusInsulinDelivery = True
        status.StatusBolusingDual = False
        status.StatusBolusingSquare = False
        status.StatusBolusingNormal = False
        status.StatusSuspended = False
        status.lastBolusAmount = 0.8
        status.lastBolusTimestamp = datetime.now() + timedelta(hours=-1)
        status.bolusWizardBGL = None
        status.sensorRateOfChangePerMin = None
        status.wholePayloadHex = ""

        drivermock.getPumpStatus.return_value = status

        with patch("pushover.Client", autospec=True) as client:
            client.return_value = MagicMock()
            client.return_value.send_message.return_value = { "ok": 1}
            testobj.statusDownload(drivermock)

            client.return_value.send_message.assert_called_once()

            client.return_value.send_message.reset_mock()
            testobj.statusDownload(drivermock)
            client.return_value.send_message.assert_not_called()


if __name__ == '__main__':
    unittest.main()