
import RPi.GPIO as gpio
import time
import schedule
import datetime
import logging

from suntime import Sun
from geopy.geocoders import Nominatim



'''TODO LIST
-add ph, temperature (air, water), ec monitoring/logging
-add logged values to some server

-add server interaction with mobile client and rpi as backend
-add the camera??

'''

def lightOn(lightPin, logfile):
	# turn lights on, log on file, update suntimes for tomorrow
	gpio.output(lightPin, gpio.HIGH)
	with open(logfile, "a") as file1:
		nowTime = datetime.datetime.now()
		timeStr = str(nowTime)
		file1.write(f"Lights turned on at {timeStr} \n")


def lightOff(lightPin, logfile):
	# turn lights off, log on file
	gpio.output(lightPin, gpio.LOW)
	with open(logfile, "a") as file1:
		nowTime = datetime.datetime.now()
		timeStr = str(nowTime)
		file1.write(f"Lights turned off at {timeStr} \n")


def lightScheduleUpdate(sun, lightPin, timeZone, logfile):
	timeAfterSunrise = 2
	timeBeforeSunset = 2
	sunRise = sun.get_local_sunrise_time(timeZone)
	sunSet = sun.get_local_sunset_time(timeZone)
	lightOnTime = sunSet - datetime.timedelta(hours=timeBeforeSunset)
	lightOffTime = sunRise + datetime.timedelta(hours=timeAfterSunrise)
	
	schedule.clear('light_task')
	
	lightOnJob = schedule.every().day.at(f"{lightOnTime.hour:02}:{lightOnTime.minute:02}").do(lightOn, lightPin, logfile).tag("light_task")
	lightOffJob = schedule.every().day.at(f"{lightOffTime.hour:02}:{lightOffTime.minute:02}").do(lightOff, lightPin, logfile).tag("light_task")
	
	with open(logfile, "a") as file1:
		nowTime = datetime.datetime.now()
		timeStr = str(nowTime)
		file1.write(f"Sun times updated at {timeStr} \n")


def pumpOn(pumpOnInterval, waterPin, logfile):
	# turn pump on, schedule pump off in pumpOnInterval mins, log
	
	pumpOffJob = schedule.every(pumpOnInterval).minutes.do(pumpOff, waterPin, logfile).tag("pump_off_task")
	
	gpio.output(waterPin, gpio.HIGH)
	with open(logfile, "a") as file1:
		nowTime = datetime.datetime.now()
		timeStr = str(nowTime)
		file1.write(f"Pump turned on at {timeStr} \n")

def pumpOff(waterPin, logfile):
	schedule.clear('pump_off_task')
	
	gpio.output(waterPin, gpio.LOW)
	with open(logfile, "a") as file1:
		nowTime = datetime.datetime.now()
		timeStr = str(nowTime)
		file1.write(f"Pump turned off at {timeStr} \n")


def systemCheck(lightPin, waterPin):
	
	gpio.output(lightPin, gpio.HIGH)
	time.sleep(5)
	gpio.output(waterPin, gpio.HIGH)
	time.sleep(30)
	gpio.output(waterPin, gpio.LOW)
	time.sleep(10)
	gpio.output(lightPin, gpio.LOW)
	time.sleep(2)


def startup(lightPin, lightOnTime, lightOffTime, logfile):
	#check time and turn on/off the lights start the log
	nowTime = datetime.datetime.now()
	action = 0
	
	if ((nowTime.hour > lightOnTime.hour) or (nowTime.hour < lightOffTime.hour)):
		if((nowTime.minute > lightOnTime.minute) or (nowTime.minute < lightOffTime.minute)):
			gpio.output(lightPin, gpio.HIGH)
			action = 1

	with open(logfile, "a") as file1:
		timeStr = str(nowTime)
		file1.write(f"Program started at {timeStr} \n")
		if action:
			file1.write(f"Lights turned on at {timeStr} \n")
	

def measurements(logfile):
	# do temp, ph, ec measurements and log
	with open(logfile, "a") as file1:
		nowTime = nowTime = datetime.datetime.now()
		timeStr = str(nowTime)
		file1.write(f"Measurements made at {timeStr} \n")



if __name__ == "__main__":
	
	try:
		
		
		timeAfterSunrise = 2 # number of hours
		timeBeforeSunset = 2 # number of hours 
	
		pumpCycleTime = 3 # number of hours between pump turn ons
		pumpOnInterval = 30 # number of minutes pump stays on every pumpCycleTime hours
	
		measureInterval = 60 # number of minutes between measurements
	
		lightPin = 23
		waterPin = 24
		stopButtonPin = 25
		
	
		logfile = "./Data/logfile.txt"
		logging.basicConfig(filename=logfile)
		
		# Setup GPIO pins
		
		gpio.setmode(gpio.BCM)
		gpio.setup(lightPin, gpio.OUT, initial=gpio.LOW)
		gpio.setup(waterPin, gpio.OUT, initial=gpio.LOW)
		gpio.setup(stopButtonPin, gpio.IN, pull_up_down=gpio.PUD_DOWN)
	
		# Get the sunset and sunrise info
		geolocator = Nominatim(user_agent="geoapiExercises")
	
		place = "Saint Louis"
		location = geolocator.geocode(place)
	
		latitude = location.latitude
		longitude = location.longitude
		sun = Sun(latitude, longitude)
	
		timeZone = datetime.date.today()
		sunRise = sun.get_local_sunrise_time(timeZone)
		sunSet = sun.get_local_sunset_time(timeZone)
	
		lightOnTime = sunSet - datetime.timedelta(hours=timeBeforeSunset)
		lightOffTime = sunRise + datetime.timedelta(hours=timeAfterSunrise)
	
		systemCheck(lightPin, waterPin)
		startup(lightPin, lightOnTime, lightOffTime, logfile)
	
		# Set up the scheduling
	
		lightOnJob = schedule.every().day.at(f"{lightOnTime.hour:02}:{lightOnTime.minute:02}").do(lightOn, lightPin, logfile).tag("light_task")
		lightOffJob = schedule.every().day.at(f"{lightOffTime.hour:02}:{lightOffTime.minute:02}").do(lightOff, lightPin, logfile).tag("light_task")
	
		lightUpdateJob = schedule.every().day.at("23:45").do(lightScheduleUpdate, sun, lightPin, timeZone, logfile).tag("light_update_task")
	
		pumpOnJob = schedule.every(pumpCycleTime).hours.do(pumpOn, pumpOnInterval, waterPin, logfile).tag("pump_on_task")
	
		measureJob = schedule.every(measureInterval).minutes.do(measurements, logfile).tag("measurement_task")
	
	
	
		while True:
			schedule.run_pending()
			time.sleep(1)
			if gpio.input(stopButtonPin):
				break
		
	except:
		
		logging.exception('')
	
	finally:
		
		gpio.output(lightPin, gpio.LOW)
		gpio.output(waterPin, gpio.LOW)
		gpio.cleanup()
		schedule.clear()
		
