# Class: ToolSelector
# Desc: Abstraction Class to represent the Tool selection mechanism for the CUB
# Params:
#
# Functions:    tool_home() - Returns the blank (home) tool to the selected position
#               tool_select(tool) - Moved the tool

import logging
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
    # GPIO Input for the sensor to return True
    PS_TRUE = 1

    def __init__(self):
        # Define Tool stepper motor
        self.toolStepper = StepperMotor(ToolSelector.TOOLDIR, ToolSelector.TOOLSTEP, ToolSelector.TOOLENA,
                                        ToolSelector.START_SPEED, ToolSelector.MAX_SPEED)

        # Define Photo interrupter sensor, input is 0 when beam is cut
        self.toolHomeSensor = PhotoSensor(ToolSelector.TOOLPS, ToolSelector.PS_TRUE)

        # Initialise tool to home position (Blank face upwards)
        self.currentTool = 9
        self.tool_home()

        self.currentTool = 0

    def tool_home(self):
        self.tool_select(0)

        if self.currentTool > 4:
            # Shortest travel is to wrap in forwards direction
            direction = ToolSelector.POS_DIR
            expected = (8 - self.currentTool) * ToolSelector.STEPS_PER_TOOL
        else:
            # Shortest travel is to rotate in backwards direction
            direction = ToolSelector.NEG_DIR
            expected = self.currentTool * ToolSelector.STEPS_PER_TOOL

        count = self.toolStepper.move_until(self.toolHomeSensor.read_sensor, direction)

        logging.info(f"Tool Returned Home. Expected Steps = {expected}, Actual Steps = {count}")

        # BACKUP #1
        # self.toolStepper.move_until(self.toolHomeSensor.read_sensor, ToolSelector.POS_DIR)

        # BACKUP #2
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
        # leaving the adjusted desired tool in a range from -3 to 4
        # The value represents the direction (-ve = backwards rotation)
        # and number of faces to rotate (Between 0 and 4)
        movement = tool - self.currentTool

        if movement > 4:
            # Wrap the adjusted movement value to keep within range
            movement -= 8
        elif movement < -3:
            # Wrap the adjusted movement value to keep within range
            movement += 8

        if movement > 0:
            # Rotate in a positive direction
            direction = ToolSelector.POS_DIR

        else:
            # Rotate in a negative direction
            direction = ToolSelector.NEG_DIR

        steps = movement * ToolSelector.STEPS_PER_TOOL

        # Move the Stepper motor
        self.toolStepper.move_steps(steps, direction)

        logging.info(f"Rotated from tool #{self.current} to #{tool} in {steps} steps via direction {direction}")

        # Update the current tool attribute
        self.currentTool = tool

