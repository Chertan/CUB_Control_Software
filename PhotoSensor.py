import pigpio


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

