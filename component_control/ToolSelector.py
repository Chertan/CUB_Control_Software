from component_control.hardware_interface.StepperMotor import StepperMotor
from component_control.hardware_interface.PhotoSensor import PhotoSensor
from CUBExceptions import *
import multiprocessing
import logging


def translate_tool(index):
    """Translates the index sent from the Main thread to a tool index

    :param index: The desired tool as a string binary representation
    :return: The corresponding tool index as a integer
    """
    # Reverse string from top to bottom, to bottom to top order
    rev = index[::-1]
    return int(rev, 2)


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

        self.exit = False
        self.currentTool = 5

        self.in_pipe, self.out_pipe = multiprocessing.Pipe()

    def __del__(self):
        self.emergency_stop()

    def thread_in(self):
        """Entrance point for the Head Traverser component thread

        :return: 0 to confirm successful close of thread
        """
        try:
            self.startup()
            self.run()

        except InitialisationError as err:
            self.emergency_stop()
            self.__output(f"{err.component} ERROR: {err.message}")
        except KeyboardInterrupt:
            self.emergency_stop()
        except CommunicationError as comm:
            self.emergency_stop()
            self.__output(f"{comm.component} ERROR: {comm.message} - MSG: {comm.errorInput}")
        except OperationError as op:
            self.emergency_stop()
            self.__output(f"{op.component} ERROR: {op.message} - OP: {op.operation}")
        finally:
            return 0

    def __output(self, obj):
        """Places the argument object into the output pipe to be received by another thread

        :param obj: Object to be output to another thread
        :return: None
        """
        self.out_pipe.send(obj)

    def __input(self):
        """Returns the next message in the input pipe to be received from another thread

        :return: The object received from another thread
        """
        msg = self.in_pipe.recv()
        logging.debug(f"HeadTraverser Received MSG: {msg}")

        msg_split = msg.split()
        for i in range(3 - len(msg_split)):
            msg_split.append("NULL")
        key = msg_split[0]
        index = msg_split[1]
        direction = msg_split[2]

        return key, index, direction

    def send(self, obj):
        """Used by other threads to send an object to the input pipe

        :param obj: Object to be input to the Head Traverser Thread
        :return: None
        """
        self.in_pipe.send(obj)

    def recv(self):
        """Used by other threads to send an object to the input pipe

        :return: Object output by Head Traverser
        """
        return self.out_pipe.recv()

    def startup(self):
        """Runs a startup test of the Tool Selector module

        :return: None
        """
        # Initialise tool to home position (Blank face upwards)
        count = self.tool_home()

        if count > ToolSelector.STEPS_PER_TOOL * 8:
            logging.error("Unable to return the Embosser Tool to the blank position")
            raise InitialisationError(self.__class__, "Unable to return the Embosser Tool to the blank position")

        self.__rotation_test()
        if self.toolHomeSensor.read_sensor():
            self.__output("ACK")
        else:
            logging.error("Tool not Blank After Test")
            raise InitialisationError(self.__class__, "Rotation Test Failed - Tool not home")

    def run(self):
        while not self.exit:
            # Get Input from Main Thread
            key, index, direction = self.__input()
            # ------------------------------------------
            # Close Command
            # ------------------------------------------
            if key is "CLOSE":
                # Close program
                self.close()
            # ------------------------------------------
            # Home Command
            # ------------------------------------------
            elif key is "HOME":
                # Move Head Home
                self.tool_home()
            # ------------------------------------------
            # Move Commands
            # ------------------------------------------
            elif key is "MOVE":
                # --------------------
                # Character Traversal
                # --------------------
                try:
                    tool = translate_tool(index)
                    self.tool_select(tool)
                except ValueError:
                    raise CommunicationError(self.__class__, index, "Conversion to Base 2 Index Failed")

            else:
                raise CommunicationError(self.__class__, key, "Key portion of message")

            # If no exceptions are raised, acknowledge task complete
            self.__output("ACK")

    def close(self):
        self.exit = True

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
        self.close()

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
        elif tool > 7 or tool < 0:
            raise CommunicationError(self.__class__, tool, "Invalid Tool Index")
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
