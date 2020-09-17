# Class: PhotoSensor
# Desc: Hardware interface class to handle the reading of photosensor components
# Params: in_pin is the gpio pin number of the sensor
#         in_true_value is the gpio value for which the sensor will return true
#
# Functions: read_sensor() - Returns True or False depending on the current output of the sensor

import logging
import pigpio


class PhotoSensor:
    gpio = pigpio.pi()

    def __init__(self, in_pin=None, in_true_value=0):
        self.pin = in_pin
        self.trueValue = in_true_value

        PhotoSensor.gpio.set_pull_up_down(in_pin, pigpio.PUD_UP)
        logging.info(f"Setting up Photo Sensor on GPIO Pin: {self.pin}")

    def read_sensor(self):
        value = PhotoSensor.gpio.read(self.pin)
        if value == self.trueValue:
            # Sensor pin is in true position
            out = True
        else:
            # Sensor pin is in false position
            out = False

        logging.info(f"Sensor on GPIO pin #{self.pin} current value of {value}, returning {out} ")

        return out
