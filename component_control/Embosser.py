from component_control.hardware_interface.DCOutputDevice import *
from component_control.hardware_interface.PhotoSensor import *
import logging
import time

# Flag to enable or disable simulation of outputs
# Allows for testing of system software without needing devices connected
SIMULATE = False


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
    PULSE_LEN = 0.01

    # GPIO pin of the embossing home sensor
    COILPS = 4
    # GPIO Input for the sensor to return True
    PS_TRUE = 1

    def __init__(self, simulate=False):
        """Creates an abstraction object of the Embosser module for the CUB

        """
        Embosser.SIMULATE = simulate

        self.embosser = DCOutputDevice(Embosser.COILDIR, Embosser.COILENA)
        self.embosserHomeSensor = PhotoSensor(Embosser.COILPS, Embosser.PS_TRUE)

        logging.info(f"Setting Embosser with Enable on GPIO Pin: {Embosser.COILENA}")

        self.embosserHomeSensor.set_falling_callback(self.__leave_callback)
        self.embosserHomeSensor.set_rising_callback(self.__home_callback)

        self.start = time.time()
        self.start_check = False
        self.leave_check = False

    def __del__(self):
        """Deconstructor to ensure output is turned off before exit

        :return: None
        """
        self.embosser.e_stop()

    def startup(self):
        if SIMULATE:
            logging.info("Simulating startup of Embosser...")
            out = "ACK"
        else:
            if self.embosserHomeSensor.read_sensor():
                self.activate()
                if self.leave_check:
                    if self.home_check:
                        out = "ACK"
                    else:
                        out = "Embosser did not return to Home Position"
                else:
                    out = "Embosser did not leave Home Position"
            else:
                out = "Embosser not detected at Home Position at Initialisation"
        return out

    def __home_callback(self, gpio, level, tick):
        """Callback function called when the home photosensor detects the embossing plate returning to the home position

        :param gpio: Pin that triggered callback
        :param level: Level of the pin that triggered callback
        :param tick: Timing value to represent when the trigger ocured
        :return: None
        """
        current = self.start - time.time()
        self.home_check = True
        logging.debug(f"Embosser returned to home position at t+{current} seconds")

    def __leave_callback(self, gpio, level, tick):
        """Callback function called when the home photosensor detects the embossing plate leaving the home position

        :param gpio: Pin that triggered callback
        :param level: Level of the pin that triggered callback
        :param tick: Timing value to represent when the trigger ocured
        :return: None
        """
        current = self.start - time.time()
        self.leave_check = True
        logging.debug(f"Embosser left home position at t+{current} seconds")

    def activate(self, length=PULSE_LEN):
        """Activates the embosser to complete a single embossing action

        :param length: Optional parameter that indicates the length of the output pulse
        :return: None
        """
        if SIMULATE:
            logging.debug(f"Simulating Embosser Activation...")
        else:
            current = self.start - time.time()
            logging.debug(f"Embosser Activation at t+{current} seconds for a length of {length}")
            if Embosser.DUAL_DIR:
                self.embosser.swap_pulse(Embosser.DOWN_DIR, duration=(length/2))
            else:
                self.embosser.pulse(Embosser.DOWN_DIR, duration=length)

    def emergency_stop(self):
        """Stops the embossing mechanism to a state that requires a hard restart of the program

        :return: None
        """
        if not SIMULATE:
            self.embosser.e_stop()
