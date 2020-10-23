from DCOutputDevice import *
from PhotoSensor import *
from CUBExceptions import *
import logging
import time


class Embosser:
    """Abstraction Class to represent the Embossing mechanism for the CUB

        Attributes: embosser           - DC Output Device interface object for the Embossing mechanism
                    embosserHomeSensor - PhotoSensor interface object for the embosser home sensor
                    startTime          - Time reference at the initialisation of the embosser, used to record timings

        Methods:    activate()       - Activates the Embosser
                    emergency_stop() - Shuts down the embosser to prevent future operation
    """
    # GPIO pins for embossing mechanism
    COILENA = 19
    COILDIR = 26

    # Coil Direction Selectors (To allow bi directional)
    DOWN_DIR = 1
    UP_DIR = 0

    # Flag to set if using magnet polarity to push embosser away
    DUAL_DIR = False

    # Total duration of the pulse, combined for dual direction operation
    PULSE_LEN = 0

    # GPIO pin of the embossing home sensor
    COILPS = 4
    # GPIO Input for the sensor to return True
    PS_TRUE = 1

    def __init__(self):
        """Creates an abstraction object of the Embosser module for the CUB

        """
        self.embosser = DCOutputDevice(Embosser.COILDIR, Embosser.COILENA)
        self.embosserHomeSensor = PhotoSensor(Embosser.COILPS, Embosser.PS_TRUE)

        logging.info(f"Setting Embosser with Enable on GPIO Pin: {Embosser.COILENA}")

        self.embosserHomeSensor.set_falling_callback(self.__leave_callback())
        self.embosserHomeSensor.set_rising_callback(self.__home_callback())

        self.start = time.time()

    def __home_callback(self, gpio, level, tick):
        """Callback function called when the home photosensor detects the embossing plate returning to the home position

        :param gpio: Pin that triggered callback
        :param level: Level of the pin that triggered callback
        :param tick: Timing value to represent when the trigger ocured
        :return: None
        """
        current = self.start - time.time()
        logging.debug(f"Embosser returned to home position at t+{current} seconds")

    def __leave_callback(self, gpio, level, tick):
        """Callback function called when the home photosensor detects the embossing plate leaving the home position

        :param gpio: Pin that triggered callback
        :param level: Level of the pin that triggered callback
        :param tick: Timing value to represent when the trigger ocured
        :return: None
        """
        current = self.start - time.time()
        logging.debug(f"Embosser left home position at t+{current} seconds")

    def activate(self):
        """Activates the embosser to complete a single embossing action

        :return: None
        """
        if Embosser.DUAL_DIR:
            self.embosser.swap_pulse(Embosser.DOWN_DIR, duration=(Embosser.PULSE_LEN/2))
        else:
            self.embosser.pulse(Embosser.DOWN_DIR, duration=Embosser.PULSE_LEN)

        current = self.start - time.time()
        logging.debug(f"Embosser Activation at t+{current} seconds for a length of {Embosser.PULSE_LEN}")

    def emergency_stop(self):
        """Stops the embossing mechanism to a state that requires a hard restart of the program

        :return: None
        """
        self.embosser.e_stop()
