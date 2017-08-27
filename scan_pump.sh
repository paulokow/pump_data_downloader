#!/bin/bash
export LOGFILE="PumpScan.log"
export PYTHONPATH=./decoding-contour-next-link
echo "SCRIPT>> Staring..." >> $LOGFILE
date >> $LOGFILE
./virtualenv/bin/python -u bg_data_export2.py 2>&1 >> $LOGFILE
echo "SCRIPT>> Done!" >> $LOGFILE
