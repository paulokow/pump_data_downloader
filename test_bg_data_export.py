import os
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
        status = PumpStatusResponseMessage(
            responsePayload=bytearray.fromhex('02013C5000000000000000000000000000002328278BDD283A000100000DAC000000000000000000AAE619001BBE8A190000000000030286764112A115F66700E01400000029000000000000000000000000000000000000000008C8000008C8')
            )

        drivermock.getPumpStatus.return_value = status

        with patch("pushover.Client", autospec=True) as client:
            open(os.path.expanduser("~/.pushoverrc"), 'a').close()
            client.return_value = MagicMock()
            client.return_value.send_message.return_value = { "ok": 1}
            testobj.statusDownload(drivermock)

            client.return_value.send_message.assert_called_once()

            client.return_value.send_message.reset_mock()
            testobj.statusDownload(drivermock)
            client.return_value.send_message.assert_not_called()

    def test_statusDownload_calibration_warning(self):
        events = [
            "02013C5000000000000000000000000000004268279ACC5145000100001194000000000000000000C15C320020CF6A190000002AF800828684ED53A115F6680060100000142C004A00000000000000000000000000000000000008FC000008FC",
            "02013C1000000000000000000000000000004268279ACC5145000100001482000000000000000000C350320020CD761900000027100000000000000000000000000000000000000000000000000000000000000000000000000008FC000008FC",
            "02013C5000000000000000000000000000004268279ACC5145000100001482000000000000000000C544320020CB8219000000232800868684EFABA115F66800601000000A2C002A00000000000000000000000000000000000008FC000008FC",
            "02013C5000000000000000000000000000004268279ACC5145000100001482000000000000000000C63E320020CA88190000001B58008A8684F0D7A115F6680060100000052C003700000000000000000000000000000000000008FC000008FC",
            "02013C1000000000000000000000000000004268279ACC5145000100001482000000000000000000C832320020C8941900000017700000000000000000000000000000000000000000000000000000000000000000000000000008FC000008FC",
            "02013C5000000000000000000000000000004268279ACC5145000100001482000000000000000000CA26320020C6A019000000138803028684F32FA115F66800E0140000002B000000000000000000000000000000000000000008FC000008FC",
        ]

        db=MongoClient(host="mongo", username="root", password="example").bg_db_test
        db.all_events.delete_many({})

        testobj = LatestActivity(host="mongo", username="root", password="example")
        
        drivermock = Mock(spec=Medtronic600SeriesDriver)
        status = PumpStatusResponseMessage()
        status.responsePayload = bytearray.fromhex('02013C5000000000000000000000000000002328278BDD283A000100000DAC000000000000000000AAE619001BBE8A190000000000030286764112A115F66700E01400000029000000000000000000000000000000000000000008C8000008C8')

        drivermock.getPumpStatus.side_effect = [
            PumpStatusResponseMessage(
                responsePayload=bytearray.fromhex(x)
            ) for x in events
        ]

        with patch("pushover.Client", autospec=True) as client:
            with patch("bg_data_export2.datetime") as time:
                time.now.return_value = datetime(2021, 1, 20, 13, 0, 9)
                open(os.path.expanduser("~/.pushoverrc"), 'a').close()
                client.return_value = MagicMock()
                client.return_value.send_message.return_value = { "ok": 1}
                
                # first download - no events
                testobj.statusDownload(drivermock)
                client.return_value.send_message.assert_not_called()
                client.return_value.send_message.reset_mock()

                # second download - no event (no sensor read)
                testobj.statusDownload(drivermock)
                client.return_value.send_message.assert_not_called()
                client.return_value.send_message.reset_mock()

                # third download - warning event (10 mins)
                testobj.statusDownload(drivermock)
                client.return_value.send_message.assert_called_once_with(
                    "Calibration in 10 minutes at 13:10.",
                    title="Calibration soon",
                    url="https://paulonet.eu/bgmonitor/"
                )
                client.return_value.send_message.reset_mock()

                # fourth download - warning event (5 mins)
                testobj.statusDownload(drivermock)
                client.return_value.send_message.assert_called_once_with(
                    "Calibration in 5 minutes at 13:05.",
                    title="Calibration soon",
                    url="https://paulonet.eu/bgmonitor/"
                )
                client.return_value.send_message.reset_mock()

                # sixth download - no event (no sensor read)
                testobj.statusDownload(drivermock)
                client.return_value.send_message.assert_not_called()
                client.return_value.send_message.reset_mock()

                # fifth download - alert event (calibration now)
                testobj.statusDownload(drivermock)
                client.return_value.send_message.assert_called_once()
                client.return_value.send_message.assert_called_once_with(
                    "Calibration already passed!",
                    title="Calibration needed!",
                    url="https://paulonet.eu/bgmonitor/",
                    priority=1)

if __name__ == '__main__':
    unittest.main()