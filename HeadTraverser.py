from StepperMotor import StepperMotor
from PhotoSensor import PhotoSensor
from CUBExceptions import *
import logging


class HeadTraverser:
    """Abstraction Class to represent the Head Traversal mechanism for the CUB

        Attributes: traverseStepper      - Stepper motor class to represent the Traversal stepper motor
                    traverseHomeSensor   - PhotoSensor class to represent the Photosensor used to detect the traversal
                                           home position
                    currentStep          - Tracks current position of head in number of steps from the home position

        Methods:    traverse_home()      - Returns brailler head to the home position
                    traverse_character() - Moves the brailler head by the distance between braille characters
                                           Has optional reverse parameter
                    traverse_column()    - Moves the brailler head by the distance between columns in braille cell
                                           Has optional reverse parameter
                    emergency_stop()     - Shuts down the traverser stepper motor to prevent future operation
    """
    # GPIO pins of the head traversal stepper motor
    TRAVDIR = 21
    TRAVSTEP = 20
    TRAVENA = 16

    # Motor speed parameters to be tuned during testing
    START_SPEED = 500
    MAX_SPEED = 1200
    RAMP_RATE = 15

    # Direction Selectors to be confirmed during testing
    POS_DIR = 1
    NEG_DIR = 0

    # Max page steps
    # Based of 300mm Travel length of head ( divided by 0.157mm per step) (1400)
    # Adjusted from testing down to 1200
    MAX_TRAV_STEPS = 1200

    # Number of motor steps between columns of a single braille character (2.5mm)
    # Based of a single step (1.8 degrees) equalling 0.157mm
    STEPS_BETWEEN_COLUMN = 16

    # Number of motor steps between two braille characters (4.5mm)
    # Based of a single step (1.8 degrees) equalling 0.157mm
    STEPS_BETWEEN_CHAR = 29

    # GPIO pin of the head home sensor
    TRAVPS = 4
    # GPIO Input for the sensor to return True
    PS_TRUE = 1

    def __init__(self):
        """Creates an abstraction object of the Head Traverser module for the CUB

        """
        # Define Tool stepper motor
        self.traverseStepper = StepperMotor(HeadTraverser.TRAVDIR, HeadTraverser.TRAVSTEP, HeadTraverser.TRAVENA,
                                            HeadTraverser.START_SPEED, HeadTraverser.MAX_SPEED, HeadTraverser.RAMP_RATE)
        logging.info(f"Setting up Traverser with STEP Pin: {HeadTraverser.TRAVSTEP}")

        # Photo interrupter sensor reads 0 when beam is cut
        self.traverseHomeSensor = PhotoSensor(HeadTraverser.TRAVPS, HeadTraverser.PS_TRUE)
        logging.info(f"Setting up Traverser Home Sensor on Pin: {HeadTraverser.TRAVPS}")

        self.currentStep = HeadTraverser.MAX_TRAV_STEPS

    def startup(self):
        """Runs a startup test of the Head Traverser module

        :return: None
        """
        try:
                count = self.traverse_home()

                if count == 2 * HeadTraverser.MAX_TRAV_STEPS:
                    logging.error("Unable to return the Embosser Head to the home position")
                    raise InitialisationError(self.__class__, "Unable to return the Embosser Head to the home position")

                self.__movement_test()
        except InitialisationError:
            raise
        except KeyboardInterrupt:
            self.emergency_stop()
            raise CUBClose(__name__, "Closing due to Keyboard interrupt")

    def __del__(self):
        """Deconstruct to ensure outputs are disabled at exit

        :return: None
        """
        self.emergency_stop()

    def __movement_test(self):
        """Complete a movement test of the Head Traversal Module
        Moves forward and backwards by half the maximum and reports any difference in expected steps

        :return: None
        """
        self.traverseHomeSensor.set_rising_callback(self.__home_callback)

        self.traverseStepper.move_steps(round(HeadTraverser.MAX_TRAV_STEPS / 2), HeadTraverser.POS_DIR)

        count = self.traverseStepper.move_steps(round(HeadTraverser.MAX_TRAV_STEPS / 2), HeadTraverser.NEG_DIR)

        if self.traverseHomeSensor.read_sensor():
            logging.info(f"Tool Movement Test Completed. Expected Steps = {HeadTraverser.MAX_TRAV_STEPS/2}, "
                         f"Steps taken = {count}")
        else:
            exp = count
            count = self.traverseStepper.move_steps(HeadTraverser.MAX_TRAV_STEPS - count, HeadTraverser.NEG_DIR)
            logging.info(f'Tool Movement Test Completed. Expected Steps = {HeadTraverser.MAX_TRAV_STEPS/2}, '
                         f'Actual Steps = {exp + count}')

            self.traverseHomeSensor.clear_rising_callback()

    def __home_callback(self, gpio, level, tick):
        """Callback function called when the home photosensor detects the tool head in the home position

        :param gpio: Pin that triggered callback
        :param level: Level of the pin that triggered callback
        :param tick: Timing value to represent when the trigger ocured
        :return: None
        """
        # Logging commented to prevent unnecessary overhead in the callback to ensure quick reponse
        # Uncomment to aid in debugging
        # logging.info("Traverser Callback Triggered")
        self.traverseStepper.stop()

    def emergency_stop(self):
        """Stops the traversal motor to a state that requires a hard restart of the program

        :return: None
        """
        self.traverseStepper.e_stop()

    def traverse_home(self):
        """Traverse the head back to the home position of the brailler

        :return: count: Number of steps taken to return home
        """
        if self.traverseHomeSensor.read_sensor():
            logging.info(f"Tool Already Home. Steps taken = 0")
            count = 0
        else:
            # Rotate backwards until the head it detected at the home position
            self.traverseHomeSensor.set_rising_callback(self.__home_callback)

            count = self.traverseStepper.move_steps(self.currentStep, HeadTraverser.NEG_DIR)

            if self.traverseHomeSensor.read_sensor():
                logging.info(f"Tool Returned Home. Steps taken = {count}")
            else:
                exp = 0
                while not self.traverseHomeSensor.read_sensor():
                    exp += count
                    count = self.traverseStepper.move_steps(20, HeadTraverser.NEG_DIR)
                    logging.info(f"Tool Returned Home. Expected Steps = {exp}, Actual Steps = {exp + count}")

                    self.traverseHomeSensor.clear_rising_callback()

        self.currentStep = 0

        return count

    def traverse_column(self, reverse=False):
        """Traverses the distance between two columns of a single braille cell

        :param reverse: Optional parameter to reverse direction of traversal
        :return: None
        """
        if reverse:
            self.traverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_COLUMN, HeadTraverser.NEG_DIR)
            self.currentStep -= HeadTraverser.STEPS_BETWEEN_COLUMN
        else:
            self.traverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_COLUMN, HeadTraverser.POS_DIR)
            self.currentStep += HeadTraverser.STEPS_BETWEEN_COLUMN

    def traverse_character(self, reverse=False):
        """Traverse the head by the spacing between braille cells

        :param reverse: Optional parameter to reverse direction of traversal
        :return: None
        """
        if reverse:
            self.traverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_CHAR, HeadTraverser.NEG_DIR)
            self.currentStep -= HeadTraverser.STEPS_BETWEEN_CHAR
        else:
            self.traverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_CHAR, HeadTraverser.POS_DIR)
            self.currentStep += HeadTraverser.STEPS_BETWEEN_CHAR
