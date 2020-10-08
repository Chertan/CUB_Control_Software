# Class: HeadTraverser
# Desc: Abstraction Class to represent the Embossing Mechanism for the CUB
#
# Functions:    traverse_home() - Returns brailler head to the home position (
#               tool_select(tool) - Moved the tool
from DCOutputDevice import DCOutputDevice
import logging
import pigpio
import time


class Embosser:

    gpio = pigpio.pi()

    # GPIO pins for embossing mechanism
    COILENA = 19
    COILDIR = 26

    # Coil Direction Selectors (To allow bi directional)
    DOWN_DIR = 1
    UP_DIR = 0

    # Flag to set if using magnet polarity to push embosser away
    DUAL_DIR = False

    # GPIO pin of the embossing home sensor
    COILPS = 4
    # GPIO Input for the sensor to return True
    PS_TRUE = 0

    def __init__(self):
        self.coil = DCOutputDevice(Embosser.COILDIR, Embosser.COILENA)

        logging.info(f"Setting Embosser with Enable on GPIO Pin: {Embosser.COILENA}")

        Embosser.gpio.callback(Embosser.COILPS, pigpio.FALLING_EDGE, self.__home_callback())

        Embosser.gpio.callback(Embosser.COILPS, pigpio.RISING_EDGE, self.__leave_callback())

        self.start = time.time()

    def __home_callback(self):
        current = self.start - time.time()
        logging.debug(f"Embosser returned to home position at t+{current} seconds")

    def __leave_callback(self):
        current = self.start - time.time()
        logging.debug(f"Embosser left home position at t+{current} seconds")

    def activate(self):
        if Embosser.DUAL_DIR:
            self.coil.swap_pulse(Embosser.DOWN_DIR)
        else:
            self.coil.pulse(Embosser.DOWN_DIR)

        current = self.start - time.time()
        logging.debug(f"Embosser Activation at t+{current} seconds")

    def emergency_stop(self):
        self.coil.e_stop()
