# Class: PhotoSensor
# Desc: Hardware interface class to handle the reading of photosensor components
# Params: in_pin is the gpio pin number of the sensor
#         in_true_value is the gpio value for which the sensor will return true
#
# Functions: read_sensor() - Returns True or False depending on the current output of the sensor

from StepperMotor import StepperMotor
from PhotoSensor import PhotoSensor


class Selector:
    # GPIO pins of the tool
    DIR_PIN = 6
    STEP_PIN = 13
    ENA_PIN = 5

    # Motor speed parameters to be tuned during testing
    START_SPEED = 5
    MAX_SPEED = 10

    # Direction Selectors to be confirmed during testing
    POS_DIR = 1
    NEG_DIR = 0

    # Number of motor steps between each face of the tool
    STEPS_PER_TOOL = 8

    # GPIO pin of the tool selector home sensor
    TRAVPS_PIN = 4

    def __init__(self):
        # Define Tool stepper motor
        self.toolStepper = StepperMotor(Selector.DIR_PIN, Selector.STEP_PIN, Selector.ENA_PIN,
                                        Selector.START_SPEED, Selector.MAX_SPEED)

        # Photo interrupter sensor reads 0 when beam is cut
        self.toolHomeSensor = PhotoSensor(Selector.TRAVPS_PIN, 0)

        self.tool_home()
        self.currentTool = 0

    def tool_home(self):
        self.toolStepper.move_until(Selector.POS_DIR, self.toolHomeSensor.read_sensor)

        # BACKUP
        # while not self.tool_home_sensor.read_sensor():
        #     # Rotate the tool
        #     self.tool_stepper.move_steps(1, Selector.POS_DIR)

    def tool_select(self, num):
        # Rotate to a specific tool: (Top, Middle, Bot)
        #   0 - Blank
        #   1 -
        #   2 -
        #   3 -
        #   4 -
        #   5 -
        #   6 -
        #   7 -


