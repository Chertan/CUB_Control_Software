# Class: HeadTraverser
# Desc: Abstraction Class to represent the Head Traversal mechanism for the CUB
# Params:
#
# Functions:    traverse_home() - Returns brailler head to the home position (
#               tool_select(tool) - Moved the tool

from StepperMotor import StepperMotor
from PhotoSensor import PhotoSensor


class HeadTraverser:
    # GPIO pins of the head traversal stepper motor
    TRAVDIR = 21
    TRAVSTEP = 20
    TRAVENA = 16

    # Motor speed parameters to be tuned during testing
    START_SPEED = 5
    MAX_SPEED = 10

    # Direction Selectors to be confirmed during testing
    POS_DIR = 1
    NEG_DIR = 0

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

        # Photo interrupter sensor reads 0 when beam is cut
        self.TraverseHomeSensor = PhotoSensor(HeadTraverser.TRAVPS, HeadTraverser.PS_TRUE)

        self.traverse_home()
        self.currentPosition = 0

    # Traverse the head back to the home position of the brailler
    def traverse_home(self):
        # Rotate backwards until the head it detected at the home position
        self.TraverseStepper.move_until(self.TraverseHomeSensor.read_sensor, HeadTraverser.NEG_DIR)

        # BACKUP
        # while not self.tool_home_sensor.read_sensor():
        #     # Rotate the tool
        #     self.tool_stepper.move_steps(1, HeadTraverser.Neg_DIR)

    # Traverse the head by the spacing of one braille column
    def traverse_column(self):
        self.TraverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_COLUMN, HeadTraverser.POS_DIR)

    # Traverse the head by the spacing between braille characters
    def traverse_character(self):
        self.TraverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_CHAR, HeadTraverser.POS_DIR)
