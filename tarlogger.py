import sys
import os.path
import time
import RPi.GPIO as GPIO
import requests
import json

from influxdb import InfluxDBClient

with open('tarlogger.conf') as conf_file:
	configuration_data = json.load(conf_file)

INFLUX = {
	"host": configuration_data["influx"]["host"],
	"port": configuration_data["influx"]["port"],
	"username": configuration_data["influx"]["username"],
	"password": configuration_data["influx"]["password"],
	"database": configuration_data["influx"]["database"]
}

TELEGRAM = {
	"bot_token": configuration_data["telegram"]["bot_token"],
	"chat_id": configuration_data["telegram"]["chat_id"]
}

SLACK = {
	"hook": configuration_data["slack"]["hook"]
}

SENSOR = configuration_data["sensor"]

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
temp_sensor ='/sys/bus/w1/devices/{0}/w1_slave'.format(SENSOR.get("sensor"))

influx = InfluxDBClient(INFLUX.get("host"), INFLUX.get("port"), 
			INFLUX.get("username"), INFLUX.get("password"), 
			INFLUX.get("database"))
influx.create_database(INFLUX.get("database"))

GPIO.setmode(GPIO.BOARD)
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

last_button_state = 0
temperature = 0

status = ['Lab closed - temperature {0}C','Lab open - temperature {0}C']

def raw_to_c(raw):
	return float(raw) / 1000.0

def read_temp():
	global temperature
	file = open(temp_sensor,'r')
	lines = file.readlines()
	file.close()
	temp_line = [l for l in lines if 't=' in l]
	ext_temp_c_raw = temp_line[0].replace('=', ' ').split()[-1]
	return raw_to_c(ext_temp_c_raw)

def do_telegram_alert(lab_status):
	response = requests.post(
		url='https://api.telegram.org/bot{0}/sendMessage'.format(TELEGRAM.get("bot_token")),
		data={'chat_id': TELEGRAM.get("chat_id"), 'text': status[lab_status].format(temperature)}
	).json()

def do_slack_alert(lab_status):
	response = requests.post(
		url='https://hooks.slack.com/services/{0}'.format(SLACK.get("hook"),
		json={'text': status[lab_status].format(temperature)}
	)

def read_button():
	global last_button_state
	button_state = GPIO.input(18)
	if button_state != last_button_state:
		do_telegram_alert(button_state)
		do_slack_alert(button_state)
	last_button_state = button_state
	return button_state

try:
	while True:
		temperature = read_temp()
		button = read_button()
		temp_json = [{
			"measurement": "lab_temp",
			"tags": {
				"device": temp_sensor
			},
			"fields": {
				"value": temperature
			}
		},{
			"measurement": "lab_switch",
			"tags": {
				"device": "switch"
			},
			"fields": {
				"value": button
			}
		}]
		print("Temp: ", temperature, " Button: ", button)
		influx.write_points(temp_json)
		time.sleep(10)

except KeyboardInterrupt:
	print("Exiting...")
	sys.exit()

