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
        status = PumpStatusResponseMessage()
        status.responsePayload = bytearray.fromhex('02013C5000000000000000000000000000002328278BDD283A000100000DAC000000000000000000AAE619001BBE8A190000000000030286764112A115F66700E01400000029000000000000000000000000000000000000000008C8000008C8')

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


if __name__ == '__main__':
    unittest.main()