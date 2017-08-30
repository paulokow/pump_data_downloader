#!/bin/bash
export LOGFILE="PumpScan.log"
export PYTHONPATH=./decoding-contour-next-link
echo "SCRIPT>> Staring..." >> $LOGFILE
date >> $LOGFILE
./virtualenv/bin/python -u bg_data_export2.py  >> $LOGFILE 2>&1
echo "SCRIPT>> Done!" >> $LOGFILE
