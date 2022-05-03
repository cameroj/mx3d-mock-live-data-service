#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from websocket_server import WebsocketServer

import csv
import json
import os
import pickle
import pytz
import random
import threading
import time


utc = pytz.utc
		
def clamp(value, range_min, range_max):
	
	return max(min(value, range_max), range_min)


class MockSensor():

	"""
	This mock sensor generates readings in a specified range at a specified
	interval. The readings fluctuate up and down over time, but never go
	outside the range. The current value can be queried at any time.
	"""

	def __init__(self, range_min, range_max, update_interval_in_seconds):

		# Download data from MX3D bridge 

		self.range_min = float(range_min)
		self.range_max = float(range_max)
		self.range_size = self.range_max - self.range_min
		self.value = self.range_min + self.range_size / 2.0 # Initial value
		self.update_interval_in_seconds = float(update_interval_in_seconds)
		self.stopped = False

		self.thread = threading.Thread(target=self.loop )
		self.thread.start()


	def updateValue(self):

		# Modify the sensor value up or down by some random amount, remaining 
		# within the range.
		average_delta = 0.02
		delta = random.uniform(
			-(self.range_size * average_delta),
			self.range_size * average_delta)
		self.value = clamp(self.value + delta, self.range_min, self.range_max)


	def loop(self):

		while (not self.stopped):

			self.updateValue()
			time.sleep(self.update_interval_in_seconds)


	def stop(self):

		self.stopped = True


def convert_utc_time_to_string(utc_time):

	"""

	Express a UTC time in the format Data360 recognizes.

	Args:
		utc_time: datetime.datetime: A date and time in UTC.

	Returns:
		(str) The date and time expressed in the format Data360 recognizes.

	"""

	assert(isinstance(utc_time, datetime))

	return utc_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class Reading():

	def __init__(self, point_id, timestamp, value):

		self.point_id = point_id
		self.timestamp = timestamp
		self.value = value


class ReplaySensor():

	"""
	This sensor plays back readings from a specified sensor over a specified
	time range. 
	"""

	def __init__(
			self, 
			csv_file_path):

		self.csv_file_path = csv_file_path
		assert(os.path.isfile(self.csv_file_path))

		self.point_id = None

		# Load readings from local file
		self.readings = self.load_readings(self.csv_file_path)
		self.next_reading_index = 0


	def load_readings(self, csv_file_path):

		readings = []
		
		with open(csv_file_path) as file:
		
			csv_reader = csv.reader(file)
			header = next(csv_reader)

			self.point_id = header[1]

			for row in csv_reader:

				timestamp = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S.%f')

				value = row[1]

				if value == '':
					value = None

				reading = Reading(self.point_id, timestamp, value)
				readings.append(reading)

		return readings


	def first_reading_timestamp(self):

		return self.readings[0].timestamp


	def last_reading_timestamp(self):

		return self.readings[-1].timestamp


	def next_reading_timestamp(self):

		try:

			return self.readings[self.next_reading_index].timestamp

		except:

			return None


	def get_next_reading(self):

		# Return the next reading from the set of readings obtained from 
		# Data360. If we've reached the end of the list of readings, we start
		# over from the beginning.

		reading = self.readings[self.next_reading_index]
		self.next_reading_index = self.next_reading_index + 1

		if self.next_reading_index == len(self.readings):

			self.next_reading_index = 0

		return reading


def main():

	try:

		replay_sensors = []

		print("Setting up replay sensors...")

		csv_file_paths = [
				#'TEST1_1hr_10Hz_data.csv', 'TEST2_1hr_10Hz_data.csv'
				'A01Y_1hr_10Hz_data.csv',
				'A02Y_1hr_10Hz_data.csv',
				'A06Y_1hr_10Hz_data.csv',
				'A07Y_1hr_10Hz_data.csv',
				'LC01_1hr_10Hz_data.csv',
				'LC02_1hr_10Hz_data.csv',
				'LC03_1hr_10Hz_data.csv',
				'LC04_1hr_10Hz_data.csv',
				'SG21_1hr_10Hz_data.csv',
				'SG23_1hr_10Hz_data.csv',
				'T06_1hr_10Hz_data.csv'
			]

		for csv_file_path in csv_file_paths:

			print("    " + csv_file_path)

			replay_sensors.append(ReplaySensor(csv_file_path))

		first_reading_time = replay_sensors[0].last_reading_timestamp()
		last_reading_time = replay_sensors[0].first_reading_timestamp()

		for replay_sensor in replay_sensors:

			if replay_sensor.first_reading_timestamp() < first_reading_time:

				first_reading_time = replay_sensor.first_reading_timestamp() 

			if replay_sensor.last_reading_timestamp() > last_reading_time:

				last_reading_time = replay_sensor.last_reading_timestamp() 


		print('First reading time: ' + str(first_reading_time))
		print('Last reading time: ' + str(last_reading_time))



		print("Starting websocket server...")
		# This constructs a server capable of sending messages through a
		# websocket. Clients can connect to the websocket on localhost:5046 or
		# 0.0.0.0:5046. Messages can be whatever the application wants to send.
		websocket_server = WebsocketServer(
			host = "0.0.0.0", 
			port = 5045)
		websocket_server_thread = \
			threading.Thread(target = websocket_server.run_forever)
		websocket_server_thread.start()

		print("Serving readings...")

		replay_time = first_reading_time

		while (True):

			timestamp = datetime.now(utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

			reading_dict = {}
			reading_dict["timestamp"] = timestamp

			for replay_sensor in replay_sensors:

				if replay_sensor.next_reading_timestamp() != replay_time:

					# This replay sensor does not have a reading associated
					# with the next time step.
					continue

				reading = replay_sensor.get_next_reading()
				#print(convert_utc_time_to_string(reading.timestamp))


				if (reading.value is not None):

					reading_dict["value"] = float(reading.value)
					reading_dict["pointId"] = replay_sensor.point_id

					json_message = json.dumps(
						reading_dict,
						separators=(", ", ": "),
						sort_keys=True)

					assert(isinstance(json_message, str))

					websocket_server.send_message_to_all(json_message)

			replay_time += timedelta(milliseconds = 100)

			if replay_time > last_reading_time:

				# Once we play back all readings from all sensors, we loop
				# back to the start and do it all again.
				replay_time = first_reading_time

			time.sleep(0.1)

	except KeyboardInterrupt:

		# Clean up after Ctrl-C
		websocket_server.shutdown_gracefully()
			
	print("\nExiting.\n")


if __name__ == '__main__':

	main()
