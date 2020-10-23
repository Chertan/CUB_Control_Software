import logging
from StepperMotor import StepperMotor
from PhotoSensor import PhotoSensor


class ToolSelector:
    """Abstraction Class to represent the Tool selection mechanism for the CUB

        Attributes: toolStepper    - Stepper motor class to represent the Tool selection stepper motor
                    toolHomeSensor - PhotoSensor class for the Photosensor used to detect the home tool position
                    currentTool    - Tracks the currently selected tool in the embossing position

        Methods:    emergency_stop()    - Shuts down the tool stepper motor to prevent future operation
                    tool_home()         - Rotates the embosser head to the blank (home) position
                    tool_select(<tool>) - Rotates the embosser head to select the input tool

    """
    # GPIO pins of the tool selector stepper motor
    TOOLDIR = 6
    TOOLSTEP = 13
    TOOLENA = 5

    # Motor speed parameters to be tuned during testing
    START_SPEED = 20
    MAX_SPEED = 60
    RAMP_RATE = 5

    # Direction Selectors to be confirmed during testing
    POS_DIR = 1
    NEG_DIR = 0

    # Number of motor steps between each face of the tool
    STEPS_PER_TOOL = 7

    # GPIO pin of the tool selector home sensor
    TOOLPS = 27
    # GPIO Input for the sensor to return True
    PS_TRUE = 1

    def __init__(self):
        """Creates an abstraction object of the Tool Selector module for the CUB

        """
        # Define Tool stepper motor
        self.toolStepper = StepperMotor(ToolSelector.TOOLDIR, ToolSelector.TOOLSTEP, ToolSelector.TOOLENA,
                                        ToolSelector.START_SPEED, ToolSelector.MAX_SPEED, ToolSelector.RAMP_RATE)

        # Define Photo interrupter sensor, input is 0 when beam is cut
        self.toolHomeSensor = PhotoSensor(ToolSelector.TOOLPS, ToolSelector.PS_TRUE)

        # Initialise tool to home position (Blank face upwards)
        self.currentTool = 5
        self.tool_home()

        self.__rotation_test()

    def __rotation_test(self):
        """Complete a movement test of the Tool Selection Module
        Performs a full rotation and reports any differences in expected steps

        :return: None
        """
        self.toolHomeSensor.set_falling_callback(self.__home_callback)

        # One full rotation
        expected = ToolSelector.STEPS_PER_TOOL * 8

        count = self.toolStepper.move_steps(expected, ToolSelector.POS_DIR)

        if self.toolHomeSensor.read_sensor():
            difference = expected - count
            logging.info(f"Tool Test completed. Expected Steps = {expected}, Actual Steps = {count}, Diff = "
                         f"{difference}")

        else:
            count = self.toolStepper.move_steps(expected, ToolSelector.POS_DIR)
            total_count = expected + count

            logging.info(f"Tool Test completed. Expected Steps = {expected}, Actual Steps = {total_count}, "
                         f"Diff = {count}")

            self.toolHomeSensor.clear_falling_callback()

    def __home_callback(self, gpio, level, tick):
        """Callback function called when the home photosensor detects the embossing tool in the blank position

        :param gpio: Pin that triggered callback
        :param level: Level of the pin that triggered callback
        :param tick: Timing value to represent when the trigger ocured
        :return: None
        """
        self.toolStepper.stop()

    # Used to activate an emergency stop on all stepper motors
    def emergency_stop(self):
        """Stops the selector motor to a state that requires a hard restart of the program

        :return: None
        """
        self.toolStepper.e_stop()

    def tool_home(self):
        """Rotates the tool back to the blank (home) position and reports any missed or extra steps

        :return: count: number of steps taken to rotate to home position
        """
        if self.currentTool > 4:
            # Shortest travel is to wrap in forwards direction
            direction = ToolSelector.POS_DIR
            expected = (8 - self.currentTool) * ToolSelector.STEPS_PER_TOOL
        else:
            # Shortest travel is to rotate in backwards direction
            direction = ToolSelector.NEG_DIR
            expected = self.currentTool * ToolSelector.STEPS_PER_TOOL

        self.toolHomeSensor.set_falling_callback(self.__home_callback)

        count = self.toolStepper.move_steps(self.STEPS_PER_TOOL * 9, direction)

        logging.info(f"Tool Rotated to Blank Position from tool {self.currentTool}. Expected Steps = {expected}, "
                     f"Actual Steps = {count}")

        self.currentTool = 0

        self.toolHomeSensor.clear_falling_callback()

        return count

    def tool_select(self, tool):
        """Rotates the tool to place the input tool into the selected position ready for embossing

        :param tool: The integer number of the tool to be selected
        :return: count: Number of steps taken to change to input tool
        """
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
        if tool == 0:
            count = self.tool_home()
        else:
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
            count = self.toolStepper.move_steps(steps, direction)

        # Update the current tool attribute
        self.currentTool = tool

        return count
