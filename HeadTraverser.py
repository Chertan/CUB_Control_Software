# Class: HeadTraverser
# Desc: Abstraction Class to represent the Head Traversal mechanism for the CUB
#
# Functions:    traverse_home() - Returns brailler head to the home position
#               tool_select(tool) - Moved the tool

from StepperMotor import StepperMotor
from PhotoSensor import PhotoSensor
import logging
import pigpio


class HeadTraverser:
    gpio = pigpio.pi()

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
    PS_TRUE = 0

    def __init__(self):
        # Define Tool stepper motor
        self.TraverseStepper = StepperMotor(HeadTraverser.TRAVDIR, HeadTraverser.TRAVSTEP, HeadTraverser.TRAVENA,
                                            HeadTraverser.START_SPEED, HeadTraverser.MAX_SPEED)

        logging.info(f"Setting up Traverser with STEP Pin: {HeadTraverser.TRAVSTEP}")

        # Photo interrupter sensor reads 0 when beam is cut
        self.TraverseHomeSensor = PhotoSensor(HeadTraverser.TRAVPS, HeadTraverser.PS_TRUE)

        logging.info(f"Setting up Traverser Home Sensor on Pin: {HeadTraverser.TRAVPS}")

        self.currentStep = HeadTraverser.MAX_TRAV_STEPS
        self.traverse_home()

        self.__movement_test()

    #
    def __movement_test(self):

        self.TraverseStepper.move_steps(round(HeadTraverser.MAX_TRAV_STEPS/2), HeadTraverser.POS_DIR)

        callback = HeadTraverser.gpio.callback(HeadTraverser.TRAVPS, pigpio.FALLING_EDGE, self.__home_callback)

        count = self.TraverseStepper.move_steps(round(HeadTraverser.MAX_TRAV_STEPS / 2), HeadTraverser.NEG_DIR)

        if self.TraverseHomeSensor.read_sensor():
            logging.info(f"Tool Movement Test Completed. Expected Steps = {HeadTraverser.MAX_TRAV_STEPS/2}, "
                         f"Steps taken = {count}")
        else:
            exp = count
            count = self.TraverseStepper.move_steps(HeadTraverser.MAX_TRAV_STEPS, HeadTraverser.NEG_DIR)
            logging.info(f'Tool Movement Test Completed. Expected Steps = {HeadTraverser.MAX_TRAV_STEPS/2}, '
                         f'Actual Steps = {exp + count}')

        callback.cancel()

    # Callback function called by pigpio library when the home photosensor is drawn low
    def __home_callback(self):
        self.TraverseStepper.stop()

    def emergency_stop(self):
        self.TraverseStepper.e_stop()

    # Traverse the head back to the home position of the brailler
    def traverse_home(self):
        # Rotate backwards until the head it detected at the home position
        callback = HeadTraverser.gpio.callback(HeadTraverser.TRAVPS, pigpio.FALLING_EDGE, self.__home_callback)

        count = self.TraverseStepper.move_steps(self.currentStep, HeadTraverser.NEG_DIR)

        if self.TraverseHomeSensor.read_sensor():
            logging.info(f"Tool Returned Home. Steps taken = {count}")
        else:
            exp = count
            count = self.TraverseStepper.move_steps(HeadTraverser.MAX_TRAV_STEPS, HeadTraverser.NEG_DIR)
            logging.info(f"Tool Rotated to Blank Position. Expected Steps = {exp}, Actual Steps = {exp + count}")

        callback.cancel()

        return count

        # BACKUP
        # while not self.tool_home_sensor.read_sensor():
        #     # Rotate the tool
        #     self.tool_stepper.move_steps(1, HeadTraverser.Neg_DIR)

    # Traverse the head by the spacing of one braille column
    def traverse_column(self, reverse=False):
        if reverse:
            self.TraverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_COLUMN, HeadTraverser.NEG_DIR)
            self.currentStep -= HeadTraverser.STEPS_BETWEEN_COLUMN
        else:
            self.TraverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_COLUMN, HeadTraverser.POS_DIR)
            self.currentStep += HeadTraverser.STEPS_BETWEEN_COLUMN

    # Traverse the head by the spacing between braille characters
    def traverse_character(self, reverse=False):
        if reverse:
            self.TraverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_CHAR, HeadTraverser.NEG_DIR)
            self.currentStep -= HeadTraverser.STEPS_BETWEEN_CHAR
        else:
            self.TraverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_CHAR, HeadTraverser.POS_DIR)
            self.currentStep += HeadTraverser.STEPS_BETWEEN_CHAR
