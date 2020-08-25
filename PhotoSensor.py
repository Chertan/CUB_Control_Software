import pigpio

# Class: PhotoSensor
# Desc: Hardware interface class to handle the reading of photosensor components
# Params: in_pin is the gpio pin number of the sensor
#         in_true_value is the gpio value for which the sensor will return true
#
# Functions: read_sensor() - Returns True or False depending on the current output of the sensor


class PhotoSensor:
    gpio = pigpio.pi()

    def __init__(self, in_pin=None, in_true_value=0):
        self.pin = in_pin
        self.trueValue = in_true_value

        PhotoSensor.gpio.set_pull_up_down(in_pin, pigpio.PUD_UP)

    def read_sensor(self):
        if PhotoSensor.gpio.read(self.pin) == self.trueValue:
            # Sensor pin is in true position
            temp = True
        else:
            # Sensor pin is in false position
            temp = False

        return temp
