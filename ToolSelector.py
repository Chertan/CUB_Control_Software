# Class: ToolSelector
# Desc: Abstraction Class to represent the Tool selection mechanism for the CUB
# Params:
#
# Functions:    tool_home() - Returns the blank (home) tool to the selected position
#               tool_select(tool) - Moved the tool

from StepperMotor import StepperMotor
from PhotoSensor import PhotoSensor


class ToolSelector:
    # GPIO pins of the tool selector stepper motor
    TOOLDIR = 6
    TOOLSTEP = 13
    TOOLENA = 5

    # Motor speed parameters to be tuned during testing
    START_SPEED = 5
    MAX_SPEED = 10

    # Direction Selectors to be confirmed during testing
    POS_DIR = 1
    NEG_DIR = 0

    # Number of motor steps between each face of the tool
    STEPS_PER_TOOL = 6

    # GPIO pin of the tool selector home sensor
    TOOLPS = 27

    def __init__(self):
        # Define Tool stepper motor
        self.toolStepper = StepperMotor(ToolSelector.TOOLDIR, ToolSelector.TOOLSTEP, ToolSelector.TOOLENA,
                                        ToolSelector.START_SPEED, ToolSelector.MAX_SPEED)

        # Photo interrupter sensor reads 0 when beam is cut
        self.toolHomeSensor = PhotoSensor(ToolSelector.TOOLPS, 0)

        self.tool_home()
        self.currentTool = 0

    def tool_home(self):
        self.toolStepper.move_until(ToolSelector.POS_DIR, self.toolHomeSensor.read_sensor)

        # BACKUP
        # while not self.tool_home_sensor.read_sensor():
        #     # Rotate the tool
        #     self.tool_stepper.move_steps(1, Selector.POS_DIR)

    def tool_select(self, tool):
        # Rotate to a specific tool: (Top, Middle, Bot)
        #   0 - Blank
        #   1 - Top
        #   2 - Mid
        #   3 - Top + Mid
        #   4 - Bot
        #   5 - Top + Bot
        #   6 - Mid + Bot
        #   7 - Top + Mid + Bot

        # Movement is found by translating the current tool to zero
        movement = tool - self.currentTool
        direction = ToolSelector.POS_DIR

        if movement < 0:
            if movement < -3:
                # Change rotation direction
                direction = ToolSelector.NEG_DIR
            else:
                # Direction is +ve by default
                movement += 8

        steps = movement * ToolSelector.STEPS_PER_TOOL

        # Move the Stepper motor
        self.toolStepper.move_steps(steps, direction)

        # Update the current tool attribute
        self.currentTool = tool

