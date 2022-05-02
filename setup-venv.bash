#!/usr/bin/env bash

virtualenv --python=python3 venv
source venv/bin/activate

pip3 install python-dateutil
pip3 install pytz
pip3 install websocket_server
