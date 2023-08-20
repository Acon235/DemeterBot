import RPi.GPIO as gpio
import time
import schedule
import datetime
import logging
import configparser as cp

from suntime import Sun
from geopy.geocoders import Photon

'''TODO LIST
-add ph, temperature (air, water), ec monitoring
-add logged values to some server

-add server interaction with mobile client and rpi as backend
-add the camera??

'''


class PlantController:
    def __init__(self, config_file='config.ini'):
        # Parse the configuration file
        config = cp.ConfigParser()

        try:
            config.read(config_file)
        except cp.MissingSectionHeaderError:
            raise ValueError(f"{config_file} is not a valid config file")
        except cp.ParsingError:
            raise ValueError(f"Could not parse {config_file}")

        # Setup GPIO pins
        gpio.setmode(gpio.BCM)

        try:
            # Assign values from the config file to the attributes
            self.time_after_sunrise = config.getint('TimeSettings', 'timeAfterSunrise')  # number of hours
            self.time_before_sunset = config.getint('TimeSettings', 'timeBeforeSunset')  # number of hours

            self.pump_cycle_time = config.getint('PumpSettings', 'pumpCycleTime')  # number of hours between pump cycles
            self.pump_on_interval = config.getint('PumpSettings', 'pumpOnInterval')  # number of minutes pump stays on

            self.adjustment_interval = config.getint('AdjustmentSettings', 'adjustmentInterval')  # minutes between adjustments

            self.light_pin = config.getint('GPIOSettings', 'lightPin')
            self.water_pin = config.getint('GPIOSettings', 'waterPin')
            self.stop_button_pin = config.getint('GPIOSettings', 'stopButtonPin')

            # Add the GPIO pin numbers to your config file and load them here

            self.ph_sensor_pin_in = config.getint('GPIOSettings', 'phSensorPinIn')
            self.ph_sensor_pin_out = config.getint('GPIOSettings', 'phSensorPinOut')
            self.ec_sensor_pin = config.getint('GPIOSettings', 'ecSensorPin')
            self.temp_sensor_pin = config.getint('GPIOSettings', 'tempSensorPin')
            self.water_level_sensor_pin = config.getint('GPIOSettings', 'waterLevelSensorPin')
            self.humidity_sensor_pin = config.getint('GPIOSettings', 'humiditySensorPin')

            self.humidifier_pin = config.getint('GPIOSettings', 'humidifierPin')  # add GPIO pin for humidifier
            self.temperature_controller_pin = config.getint('GPIOSettings',
                                                            'temperatureControllerPin')  # add GPIO pin for temperature controller

            # Setup GPIO for sensors and controllers
            gpio.setup(self.light_pin, gpio.OUT, initial=gpio.LOW)
            gpio.setup(self.water_pin, gpio.OUT, initial=gpio.LOW)
            gpio.setup(self.stop_button_pin, gpio.IN, pull_up_down=gpio.PUD_DOWN)

            # gpio.setup(self.ph_sensor_pin_in, gpio.IN)
            # gpio.setup(self.ph_sensor_pin_out, gpio.OUT, initial=gpio.LOW)
            # Add the rest of the sensor and controller GPIO setup here as input or output.

            self.light_on_time = None
            self.light_off_time = None

            self.logfile = config.get('GeneralSettings', 'logfile')

            # Get location from the config file
            place = config.get('LocationSettings', 'place')

            # Get the sunset and sunrise info
            geolocator = Photon(user_agent="geoapiExercises")
            location = geolocator.geocode(place)

            latitude = location.latitude
            longitude = location.longitude
            self.sun = Sun(latitude, longitude)

            self.time_zone = datetime.date.today()

        except cp.NoSectionError as e:
            raise ValueError(f"Missing section in {config_file}: {e}")
        except cp.NoOptionError as e:
            raise ValueError(f"Missing key in {config_file}: {e}")

        # Setup the logger
        logging.basicConfig(filename=self.logfile)

    def log_message(self, message):
        with open(self.logfile, "a") as file:
            time_str = str(datetime.datetime.now())
            file.write(f"{time_str}: {message}\n")

    def light_on(self):
        # Turn lights on, log on file
        gpio.output(self.light_pin, gpio.HIGH)
        self.log_message("Lights turned on")

    def light_off(self):
        # Turn lights off, log on file
        gpio.output(self.light_pin, gpio.LOW)
        self.log_message("Lights turned off")

    def update_light_schedule(self):
        sun_rise = self.sun.get_local_sunrise_time(self.time_zone)
        sun_set = self.sun.get_local_sunset_time(self.time_zone)

        # Compute the light-on and light-off times.
        self.light_on_time = sun_set - datetime.timedelta(hours=self.time_before_sunset)
        self.light_off_time = sun_rise + datetime.timedelta(hours=self.time_after_sunrise)

        # Clear the previous light tasks.
        schedule.clear('light_task')

        # Setting a new schedule for turning the light on and off.
        schedule.every().day.at(self.light_on_time.strftime('%H:%M')).do(self.light_on).tag('light_task')
        schedule.every().day.at(self.light_off_time.strftime('%H:%M')).do(self.light_off).tag('light_task')

        self.log_message("Sun times updated")

    def pump_on(self):
        # Clear any existing pump_off tasks
        schedule.clear('pump_off_task')

        # Schedule pump off in pump_on_interval minutes
        schedule.every(self.pump_on_interval).minutes.do(self.pump_off).tag('pump_off_task')

        # Turn pump on and log
        gpio.output(self.water_pin, gpio.HIGH)
        self.log_message("Pump turned on")

    def pump_off(self):
        # clear the pump_off task
        schedule.clear('pump_off_task')

        # turn pump off and log
        gpio.output(self.water_pin, gpio.LOW)
        self.log_message("Pump turned off")

    def system_check(self):
        gpio.output(self.light_pin, gpio.HIGH)
        time.sleep(5)
        gpio.output(self.water_pin, gpio.HIGH)
        time.sleep(30)
        gpio.output(self.water_pin, gpio.LOW)
        time.sleep(10)
        gpio.output(self.light_pin, gpio.LOW)
        time.sleep(2)

    def startup(self):
        # check time and turn on/off the lights start the log
        now_time = datetime.datetime.now()

        # creating datetime objects for light_on_time and light_off_time
        light_on_datetime = now_time.replace(hour=self.light_on_time.hour, minute=self.light_on_time.minute)
        light_off_datetime = now_time.replace(hour=self.light_off_time.hour, minute=self.light_off_time.minute)

        # If current time is within light_on and light_off time, turn the light on
        if light_on_datetime <= now_time <= light_off_datetime:
            gpio.output(self.light_pin, gpio.HIGH)
            self.log_message("Lights turned on")

        self.log_message("Program started")

    def read_sensors(self):
        # Placeholder sensor readings, replace with actual sensor readings
        ph = self.ph_sensor.read()
        ec = self.ec_sensor.read()
        temp = self.temp_sensor.read()
        water_level = self.water_level_sensor.read()
        humidity = self.humidity_sensor.read()

        # Log the raw sensor readings
        self.log_message(
            f"PH: {ph} EC: {ec} Temp: {temp} Water level: {water_level} Humidity: {humidity}")

        return {'ph': ph, 'ec': ec, 'temp': temp, 'water_level': water_level, 'humidity': humidity}

    def adjust_nutrients(self, ph, ec):
        # Placeholder for adjusting nutrients, replace with actual nutrient adjustment
        adjusted_ph = ph  # Dummy value
        adjusted_ec = ec  # Dummy value

        self.log_message(f"Adjusted PH from {ph} to {adjusted_ph}")
        self.log_message(f"Adjusted EC from {ec} to {adjusted_ec}")

    def adjust_humidity(self, humidity):
        # Placeholder for adjusting humidity, replace with actual humidity adjustment
        adjusted_humidity = humidity  # Dummy value

        self.log_message(f"Adjusted humidity from {humidity} to {adjusted_humidity}")

    def adjust_temperature(self, temperature):
        # Placeholder for adjusting temperature, replace with actual temperature adjustment
        adjusted_temperature = temperature  # Dummy value

        self.log_message(f"Adjusted temperature from {temperature} to {adjusted_temperature}")

    def adjust_water_level(self, water_level):
        # Placeholder for adjusting water level, replace with actual water level adjustment
        adjusted_water_level = water_level  # Dummy value

        self.log_message(f"adjusted water level from {water_level} to {adjusted_water_level}")

    def make_adjustments(self):
        # Read the sensors.
        sensor_values = self.read_sensors()

        # Adjust systems based on sensor values.
        self.adjust_nutrients(sensor_values['ph'], sensor_values['ec'])
        self.adjust_humidity(sensor_values['humidity'])
        self.adjust_temperature(sensor_values['temp'])
        self.adjust_water_level(sensor_values['water_level'])

        self.log_message("All necessary adjustments made")


if __name__ == "__main__":

    plant = None

    try:
        # Initialize the plant controller with the config file.
        plant = PlantController('config.ini')

        # Perform system check and startup.
        plant.system_check()
        plant.update_light_schedule()

        # Set up the scheduling
        schedule.every().day.at("23:45").do(plant.update_light_schedule).tag("light_update_task")
        schedule.every(plant.pump_cycle_time).hours.do(plant.pump_on).tag("pump_on_task")
        schedule.every(plant.adjustment_interval).minutes.do(plant.make_adjustments).tag("adjustment_task")

        while True:
            schedule.run_pending()
            time.sleep(1)
            if gpio.input(plant.stop_button_pin):
                break

    except Exception as exc:
        logging.exception('Error occurred: %s', exc)

    finally:
        if plant is not None:
            gpio.output(plant.light_pin, gpio.LOW)
            gpio.output(plant.water_pin, gpio.LOW)

        gpio.cleanup()
        schedule.clear()
