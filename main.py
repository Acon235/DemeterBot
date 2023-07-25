import RPi.GPIO as gpio
import time
import schedule
import datetime
import logging
import configparser

from suntime import Sun
from geopy.geocoders import Nominatim

'''TODO LIST
-add ph, temperature (air, water), ec monitoring
-add logged values to some server

-add server interaction with mobile client and rpi as backend
-add the camera??

'''


def log_message(message, logfile):
    with open(logfile, "a") as file:
        time_str = str(datetime.datetime.now())
        file.write(f"{time_str}: {message}\n")


def light_on(light_pin, logfile):
    # turn lights on, log on file
    gpio.output(light_pin, gpio.HIGH)
    log_message("Lights turned on", logfile)


def light_off(light_pin, logfile):
    # turn lights off, log on file
    gpio.output(light_pin, gpio.LOW)
    log_message("Lights turned off", logfile)


def update_light_schedule(sun, light_pin, time_zone, time_after_sunrise, time_before_sunset, logfile):
    sun_rise = sun.get_local_sunrise_time(time_zone)
    sun_set = sun.get_local_sunset_time(time_zone)

    # Compute the light-on and light-off times.
    light_on_time = sun_set - datetime.timedelta(hours=time_before_sunset)
    light_off_time = sun_rise + datetime.timedelta(hours=time_after_sunrise)

    # Clear the previous light tasks.
    schedule.clear('light_task')

    # Setting a new schedule for turning the light on and off.
    schedule.every().day.at(light_on_time.strftime('%H:%M')).do(light_on, light_pin, logfile).tag('light_task')
    schedule.every().day.at(light_off_time.strftime('%H:%M')).do(light_off, light_pin, logfile).tag('light_task')

    log_message("Sun times updated", logfile)


def pump_on(pump_on_interval, water_pin, logfile):
    # clear any existing pump_off tasks
    schedule.clear('pump_off_task')

    # schedule pump off in pump_on_interval minutes
    schedule.every(pump_on_interval).minutes.do(pump_off, water_pin, logfile).tag('pump_off_task')

    # turn pump on and log
    gpio.output(water_pin, gpio.HIGH)
    log_message("Pump turned on", logfile)


def pump_off(water_pin, logfile):
    # clear the pump_off task
    schedule.clear('pump_off_task')

    # turn pump off and log
    gpio.output(water_pin, gpio.LOW)
    log_message("Pump turned off", logfile)


def system_check(light_pin, water_pin):
    gpio.output(light_pin, gpio.HIGH)
    time.sleep(5)
    gpio.output(water_pin, gpio.HIGH)
    time.sleep(30)
    gpio.output(water_pin, gpio.LOW)
    time.sleep(10)
    gpio.output(light_pin, gpio.LOW)
    time.sleep(2)


def startup(light_pin, light_on_time, light_off_time, logfile):
    # check time and turn on/off the lights start the log
    now_time = datetime.datetime.now()

    # creating datetime objects for light_on_time and light_off_time
    light_on_datetime = now_time.replace(hour=light_on_time.hour, minute=light_on_time.minute)
    light_off_datetime = now_time.replace(hour=light_off_time.hour, minute=light_off_time.minute)

    # If current time is within light_on and light_off time, turn the light on
    if light_on_datetime <= now_time <= light_off_datetime:
        gpio.output(light_pin, gpio.HIGH)
        log_message("Lights turned on", logfile)

    log_message("Program started", logfile)


def measurements(logfile):
    # do temp, ph, ec measurements and log
    log_message("Measurements made", logfile)


if __name__ == "__main__":

    try:

        # Load the configuration.
        config = configparser.ConfigParser()
        config.read('config.ini')

        # Parse the configuration.
        time_after_sunrise = config.getint('TimeSettings', 'timeAfterSunrise')  # number of hours
        time_before_sunset = config.getint('TimeSettings', 'timeBeforeSunset')  # number of hours
        pump_cycle_time = config.getint('PumpSettings', 'pumpCycleTime')  # number of hours between pump cycles
        pump_on_interval = config.getint('PumpSettings', 'pumpOnInterval')  # number of minutes pump stays on
        measure_interval = config.getint('MeasurementSettings', 'measureInterval')  # minutes between measurements
        light_pin = config.getint('GPIOSettings', 'lightPin')
        water_pin = config.getint('GPIOSettings', 'waterPin')
        stop_button_pin = config.getint('GPIOSettings', 'stopButtonPin')
        logfile = config.get('GeneralSettings', 'logfile')

        # Set up the log file.
        logging.basicConfig(filename=logfile)

        # Parse location data.
        place = config.get('LocationSettings', 'place')
        geolocator = Nominatim(user_agent="geoapiExercises")
        location = geolocator.geocode(place)
        sun = Sun(location.latitude, location.longitude)

        # Setup GPIO pins
        gpio.setmode(gpio.BCM)
        gpio.setup(light_pin, gpio.OUT, initial=gpio.LOW)
        gpio.setup(water_pin, gpio.OUT, initial=gpio.LOW)
        gpio.setup(stop_button_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)

        # Perform system check and startup.
        system_check(light_pin, water_pin)
        update_light_schedule(sun, light_pin, datetime.date.today(), time_after_sunrise, time_before_sunset, logfile)

        # Set up the scheduling
        schedule.every().day.at("23:45").do(update_light_schedule, sun, light_pin, datetime.date.today(),
                                            time_after_sunrise, time_before_sunset, logfile).tag("light_update_task")
        schedule.every(pump_cycle_time).hours.do(pump_on, pump_on_interval, water_pin, logfile).tag("pump_on_task")
        schedule.every(measure_interval).minutes.do(measurements, logfile).tag("measurement_task")

        while True:
            schedule.run_pending()
            time.sleep(1)
            if gpio.input(stop_button_pin):
                break

    except Exception as e:
        logging.exception('Error occurred: %s', e)

    finally:
        gpio.output(light_pin, gpio.LOW)
        gpio.output(water_pin, gpio.LOW)
        gpio.cleanup()
        schedule.clear()

