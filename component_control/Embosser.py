from component_control.hardware_interface.DCOutputDevice import *
from component_control.hardware_interface.PhotoSensor import *
import logging
import time


class Embosser:
    """Abstraction Class to represent the Embossing mechanism for the CUB

        Attributes: embosser           - DC Output Device interface object for the Embossing mechanism
                    embosserHomeSensor - PhotoSensor interface object for the embosser home sensor
                    startTime          - Time reference at the initialisation of the embosser, used to record timings

        Methods:    activate()       - Activates the Embosser
                    emergency_stop() - Shuts down the embosser to prevent future operation

        Future Works:   Movement check could be put in place for all activations rather than just the test
                        It is as is currently as it is to detect power issues/placement issues that are not
                        likely to change during operation
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
    # Current safe value for further testing with finalised power supply
    PULSE_LEN = 0.1

    # GPIO pin of the embossing home sensor
    COILPS = 7
    # GPIO Input for the sensor to return True
    PS_TRUE = 1

    def __init__(self, simulate=False):
        """Creates an abstraction object of the Embosser module for the CUB

        """
        # Flag to enable or disable simulation of outputs
        # Allows for testing of system software without needing devices connected
        self.SIMULATE = simulate
        if self.SIMULATE:
            logging.info("Setting up Embosser as Simulated Component.")

        self.embosser = DCOutputDevice(Embosser.COILDIR, Embosser.COILENA)
        self.embosserHomeSensor = PhotoSensor(Embosser.COILPS, Embosser.PS_TRUE)

        logging.info(f"Setting Embosser with Enable on GPIO Pin: {Embosser.COILENA}")

        self.embosserHomeSensor.set_falling_callback(self.__leave_callback)
        self.embosserHomeSensor.set_rising_callback(self.__home_callback)

        self.start = time.time()
        self.home_check = False
        self.leave_check = False

    def startup(self):
        """Runs startup routine for the Embosser component. Completes an activation and ensures the embosser left its position
        and returned

        """
        if self.SIMULATE:
            logging.debug("Simulating startup of Embosser...")
            time.sleep(Embosser.PULSE_LEN * 2)
            out = "ACK"
        else:
            if self.embosserHomeSensor.read_sensor():
                self.activate()
                time.sleep(Embosser.PULSE_LEN)
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
        current = time.time() - self.start
        self.home_check = True
        logging.debug(f"Embosser returned to home position at t+{current} seconds")

    def __leave_callback(self, gpio, level, tick):
        """Callback function called when the home photosensor detects the embossing plate leaving the home position

        :param gpio: Pin that triggered callback
        :param level: Level of the pin that triggered callback
        :param tick: Timing value to represent when the trigger ocured
        :return: None
        """
        current = time.time() - self.start
        self.leave_check = True
        logging.debug(f"Embosser left home position at t+{current} seconds")

    def activate(self, length=PULSE_LEN):
        """Activates the embosser to complete a single embossing action

        :param length: Optional parameter that indicates the length of the output pulse
        :return: None
        """
        if self.SIMULATE:
            logging.info(f"Simulating Embosser Activation...")
            time.sleep(Embosser.PULSE_LEN)
        else:
            current = self.start - time.time()
            logging.info(f"Embosser Activation at t+{current} seconds for a length of {length}")
            if Embosser.DUAL_DIR:
                self.embosser.swap_pulse(Embosser.DOWN_DIR, duration=(length/2))
            else:
                self.embosser.pulse(Embosser.DOWN_DIR, duration=length)
                time.sleep(Embosser.PULSE_LEN)

    def emergency_stop(self):
        """Stops the embossing mechanism to a state that requires a hard restart of the program

        :return: None
        """
        if not self.SIMULATE:
            self.embosser.e_stop()

    def close(self):
        """Stops the embossing mechanism ready for program exit

        :return: None
        """
        if not self.SIMULATE:
            self.embosser.stop()
