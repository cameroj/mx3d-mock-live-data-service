# mx3d-mock-live-data-service
Reads sensor readings from .csv files, and replays them at 10Hz through a 
websocket as if they are coming live from a sensor. 
This project is currently hard-coded to read from specific .csv files provided 
as part of the 2022 MX3D Bridge Datathon, but could be modified to get readings 
from other .csv files and play them back at a different rate. The files
intended for use with this script are `A01Y_1hr_10Hz_data.csv`,
`A02Y_1hr_10Hz_data.csv`, `LC01_1hr_10Hz_data.csv`, `SG21_1hr_10Hz_data.csv`,
and `T06_1hr_10Hz_data.csv`.

To try:

1. Set up a Python virtual environment with:<br>`> setup-venv.bash`
2. Run the server:<br>`> ./mx3d-mock-live-data-service.py`
3. In a web browser, open `client.html`, and press the "Go" button

The example web page (`client.html`) displays a scrolling graph of sensor
readings from whichever sensor is the first one a reading is received from.
