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
            with patch("bg_data_export2.datetime") as time:
                time.now.return_value = datetime(2021, 1, 20, 13, 0, 9)

                open(os.path.expanduser("~/.pushoverrc"), 'a').close()
                client.return_value = MagicMock()
                client.return_value.send_message.return_value = { "ok": 1}
                testobj.statusDownload(drivermock)

                client.return_value.send_message.assert_called_once()

                client.return_value.send_message.reset_mock()
                testobj.statusDownload(drivermock)
                client.return_value.send_message.assert_not_called()

    def test_statusDownload_low_BG(self):
        db=MongoClient(host="mongo", username="root", password="example").bg_db_test
        db.all_events.delete_many({})

        testobj = LatestActivity(host="mongo", username="root", password="example")
        
        drivermock = Mock(spec=Medtronic600SeriesDriver)
        status = PumpStatusResponseMessage(
            responsePayload=bytearray.fromhex('02013C6000000000000000000000000000004A38278D901C4800120000109A000000000A001A0000CA266400160C88190000005DC000358677AA09A115F6670A00100001D626FE7C00000000000000000000000000000000000008D4000008D4')
            )

        drivermock.getPumpStatus.return_value = status

        with patch("pushover.Client", autospec=True) as client:
            with patch("bg_data_export2.datetime") as time:
                time.now.return_value = datetime(2021, 1, 20, 13, 0, 9)

                open(os.path.expanduser("~/.pushoverrc"), 'a').close()
                client.return_value = MagicMock()
                client.return_value.send_message.return_value = { "ok": 1}
                testobj.statusDownload(drivermock)

                client.return_value.send_message.assert_called_once_with(
                    'Low sugar 53. In 15 minutes predicted <40.',
                    priority=1,
                    title='Low sugar level.',
                    url='https://paulonet.eu/bgmonitor/'
                )

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

    def test_statusDownload_first_calibration(self):
        events = [
            "02013C5000000000000000000000000000000BB82799FA6E4100010000186A000000000000000001CEE4640022E8861900000003E8030186842870A115F66800E00400000F3D000000000000000000000000000000000000000008FB000008FB",
            "02013C5000000000000000000000000000000BB82799FA6E41000100001676000000000000000001D0D8640022E6921900000003E803018684299CA115F66800E00400000A3D000000000000000000000000000000000000000008FB000008FB",
            "02013C5000000000000000000000000000000BB82799FA6E41000100001676000000000000000001D2CC640022E49E1900000003E8030186842AC8A115F66800E0040000053D000000000000000000000000000000000000000008FB000008FB",
            "02013C5000000000000000000000000000000BB82799FA6E41000100001676000000000000000001D4C0640022E2AA190000000000030286842BF4A115F66800E0040000003D000000000000000000000000000000000000000008FC000008FC",
        ]

        db=MongoClient(host="mongo", username="root", password="example").bg_db_test
        db.all_events.delete_many({})

        testobj = LatestActivity(host="mongo", username="root", password="example")
        
        drivermock = Mock(spec=Medtronic600SeriesDriver)

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

                # first download - no event (15 mins)
                testobj.statusDownload(drivermock)
                client.return_value.send_message.assert_not_called()
                client.return_value.send_message.reset_mock()

                # second download - warning event (10 mins)
                testobj.statusDownload(drivermock)
                client.return_value.send_message.assert_called_once_with(
                    "Calibration in 10 minutes at 13:10.",
                    title="Calibration soon",
                    url="https://paulonet.eu/bgmonitor/"
                )
                client.return_value.send_message.reset_mock()

                # third download - warning event (5 mins)
                testobj.statusDownload(drivermock)
                client.return_value.send_message.assert_called_once_with(
                    "Calibration in 5 minutes at 13:05.",
                    title="Calibration soon",
                    url="https://paulonet.eu/bgmonitor/"
                )
                client.return_value.send_message.reset_mock()

                # fourth download - alert event (calibration now)
                testobj.statusDownload(drivermock)
                client.return_value.send_message.assert_called_once()
                client.return_value.send_message.assert_called_once_with(
                    "Calibration already passed!",
                    title="Calibration needed!",
                    url="https://paulonet.eu/bgmonitor/",
                    priority=1)

if __name__ == '__main__':
    unittest.main()