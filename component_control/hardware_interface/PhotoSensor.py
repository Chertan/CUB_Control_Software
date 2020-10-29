import logging
import pigpio


class PhotoSensor:
    """Hardware interface class to handle the reading of photosensor input components

        Attributes: pin              - GPIO pin number of the sensor input line
                    true_value       - Input value read from the sensor that returns a value of True
                    rising_callback  - Stores the callback object attached to the sensor's rising edge
                    falling_callback - Stores the callback object attached to the sensor's falling edge
                    either_callback  - Stores the callback object attached to the sensor's rising or falling edge

        Methods: read_sensor()                    - Returns the current output of the sensor, as defined by true_value
                 set_rising_callback(<callback>)  - Sets the callback function <callback> for the rising edge
                 clear_rising_callback()          - Clears the currently attached callback function for the rising edge
                 set_falling_callback(<callback>) - Sets the callback function <callback> for the falling edge
                 clear_falling_callback()         - Clears the currently attached callback function for the falling edge
                 set_either_callback(<callback>)  - Sets the callback function <callback> for either edge
                 clear_either_callback()          - Clears the currently attached callback function for either edge
    """
    gpio = pigpio.pi()

    def __init__(self, in_pin, in_true_value):
        """Creates an object to interface with hardware for a photosensor input device

        :param in_pin: GPIO pin number of the sensor input line
        :param in_true_value: Input value read from the sensor that returns a value of True
        """
        self.pin = in_pin
        self.true_value = in_true_value

        # Setup Pin as input with Pull Up resistor
        PhotoSensor.gpio.set_mode(in_pin, pigpio.INPUT)
        PhotoSensor.gpio.set_pull_up_down(in_pin, pigpio.PUD_UP)
        logging.info(f"Setting up Photo Sensor INPUT on GPIO Pin: {self.pin}")

        # Initialise callback variables
        self.rising_callback = None
        self.falling_callback = None
        self.either_callback = None

    def read_sensor(self):
        """Returns the current value of the sensor input in relation to the sensor true_value

        :return: None
        """
        value = PhotoSensor.gpio.read(self.pin)
        if value == self.true_value:
            # Sensor pin is in true position
            out = True
        else:
            # Sensor pin is in false position
            out = False

        logging.info(f"Sensor on GPIO pin #{self.pin} current value of {value}, returning {out} ")

        return out

    def set_rising_callback(self, callback):
        """Sets the input function to be called whenever the sensor input has a rising edge

        :param callback: Function to be called on a rising edge
        :return: None
        """
        self.rising_callback = PhotoSensor.gpio.callback(self.pin, pigpio.RISING_EDGE, callback)

    def clear_rising_callback(self):
        """Clears the currently attached callback function for the sensor rising edge

        :return: None
        """
        if self.rising_callback is None:
            logging.warning(f"Attempted to clear rising callback on pin {self.pin}, but no callback present")
        else:
            self.rising_callback.cancel()
            logging.info(f"Cleared rising callback on pin {self.pin}")

    def set_falling_callback(self, callback):
        """Sets the input function to be called whenever the sensor input has a falling edge

        :param callback: Function to be called on a falling edge
        :return: None
        """
        self.falling_callback = PhotoSensor.gpio.callback(self.pin, pigpio.FALLING_EDGE, callback)

    def clear_falling_callback(self):
        """Clears the currently attached callback function for the sensor falling edge

        :return: None
        """
        if self.falling_callback is None:
            logging.warning(f"Attempted to clear falling callback on pin {self.pin}, but no callback present")
        else:
            self.falling_callback.cancel()
            logging.info(f"Cleared falling callback on pin {self.pin}")

    def set_either_callback(self, callback):
        """Sets the input function to be called whenever the sensor input has a rising or falling edge

        :param callback: Function to be called on a rising or falling edge
        :return: None
        """
        self.falling_callback = PhotoSensor.gpio.callback(self.pin, pigpio.EITHER_EDGE, callback)

    def clear_either_callback(self):
        """Clears the currently attached callback function for the sensor falling or rising edge

        :return: None
        """
        if self.either_callback is None:
            logging.warning(f"Attempted to clear either callback on pin {self.pin}, but no callback present")
        else:
            self.either_callback.cancel()
            logging.info(f"Cleared either callback on pin {self.pin}")
