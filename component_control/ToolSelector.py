from component_control.hardware_interface.StepperMotor import StepperMotor
from component_control.hardware_interface.PhotoSensor import PhotoSensor
from CUBExceptions import *
import time
import multiprocessing
import logging


def translate_tool(index):
    """Translates the index sent from the Main thread to a tool index

    :param index: The desired tool as a string binary representation
    :return: The corresponding tool index as a integer
    """
    # Reverse string from top to bottom, to bottom to top order
    rev = index[::-1]
    out = int(rev, 2)
    logging.debug(f"Translated tool {index} to {out}")
    return out


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
    # Tested range of speeds, current motor still skips/misses steps
    # (Software outputs appear to be fine, May be a issue with the motor itself)
    START_SPEED = 50
    MAX_SPEED = 50
    RAMP_RATE = 1

    # Direction Selectors to be confirmed during testing
    POS_DIR = 1
    NEG_DIR = 0

    # Number of motor steps between each face of the tool
    # Steps per revolution / 8 - note with current motor not a whole number (50/8)
    STEPS_PER_TOOL = 6

    # GPIO pin of the tool selector home sensor
    TOOLPS = 17
    # GPIO Input for the sensor to return True
    PS_TRUE = 0

    def __init__(self, simulate=False):
        """Creates an abstraction object of the Tool Selector module for the CUB

        """
        # Flag to enable or disable simulation of outputs
        # Allows for testing of system software without needing devices connected
        self.SIMULATE = simulate
        if self.SIMULATE:
            logging.info("Setting up Selector as Simulated Component.")
        else:
            logging.info("Setting up Selector component")

        # Define Tool stepper motor
        self.toolStepper = StepperMotor(ToolSelector.TOOLDIR, ToolSelector.TOOLSTEP, ToolSelector.TOOLENA,
                                        ToolSelector.START_SPEED, ToolSelector.MAX_SPEED, ToolSelector.RAMP_RATE)

        # Define Photo interrupter sensor, input is 0 when beam is cut
        self.toolHomeSensor = PhotoSensor(ToolSelector.TOOLPS, ToolSelector.PS_TRUE)

        # Tracks the currently selected tool
        self.currentTool = 5

        # Exit flag for when to stop operation
        self.exit = False

        # cub_pipe is The CUB's end of the pipe
        # tool_pipe is the ToolSelector's end of the pipe
        self.cub_pipe, self.tool_pipe = multiprocessing.Pipe()

    def thread_in(self):
        """Entrance point for the Head Traverser component thread

        :return: 0 to confirm successful close of thread
        """
        try:
            logging.debug("Selector thread Started")
            # Run component startup procedure
            self.__startup()
            # Run component loop
            self.__run()

        except InitialisationError as err:
            self.__output(f"{err.component} ERROR: {err.message}")
        except KeyboardInterrupt:
            self.emergency_stop()
        except CommunicationError as comm:
            self.__output(f"{comm.component} ERROR: {comm.message} - MSG: {comm.errorInput}")
        except OperationError as op:
            self.__output(f"{op.component} ERROR: {op.message} - OP: {op.operation}")
        except Exception as ex:
            self.__output(f"Unidentified Selector ERROR: {ex}")
        finally:
            self.emergency_stop()
            return 0

    def __output(self, msg):
        """Places the argument message into the pipe to be received by the cub thread

        :param msg: Message to be output to another thread
        :return: None
        """
        logging.debug(f"ToolSelector Sent MSG: {msg}")
        self.tool_pipe.send(msg)

    def __input(self):
        """Returns the next message in the pipe to be received from the CUB thread

        :return: Message received from the CUB thread
        :rtype string
        """
        msg = self.tool_pipe.recv()
        logging.debug(f"ToolSelector Received MSG: {msg}")

        msg_split = msg.split()
        for i in range(3 - len(msg_split)):
            msg_split.append("NULL")
        key = msg_split[0]
        index = msg_split[1]
        direction = msg_split[2]

        return key, index, direction

    def send(self, msg):
        """Places a message into the pipe to be received by the ToolSelector Thread

        :param msg: Message to be input to the Head Traverser Thread
        :return: None
        """
        self.cub_pipe.send(msg)

    def recv(self):
        """Retrieves a message from the pipe that as been sent by the ToolSelector Thread

        :return: Object output by Tool Selector
        """
        return self.cub_pipe.recv()

    def __startup(self):
        """Runs a startup test of the Tool Selector module

        :return: None
        """
        if self.SIMULATE:
            logging.info(f"Simulating Head movement test...")
            self.__output("ACK")
        else:
            logging.info("Performing Selector Startup")

            # Initialise tool to home position (Blank face upwards)
            count = self.__tool_home()

            if count > ToolSelector.STEPS_PER_TOOL * 8:
                logging.error("Unable to return the Embosser Tool to the blank position")
                raise InitialisationError(__name__, "Unable to return the Embosser Tool to the blank position")

            self.__rotation_test()
            if self.toolHomeSensor.read_sensor():
                self.currentTool = 0
                self.__output("ACK")
            else:
                logging.error("Tool not Blank After Test")
                raise InitialisationError(__name__, "Rotation Test Failed - Tool not in blank position after test")

    def __run(self):
        """Main operational loop for the ToolSelector Thread

        :return:
        """
        while not self.exit:
            # Get Message from CUB
            # Blocks until message is received
            key, index, direction = self.__input()
            # ------------------------------------------
            # Close Command
            # ------------------------------------------
            if key == "CLOSE":
                # Close program
                self.close()
            # ------------------------------------------
            # Home Command
            # ------------------------------------------
            elif key == "HOME":
                # Move Head Home
                self.__tool_home()
            # ------------------------------------------
            # Move Commands
            # ------------------------------------------
            elif key == "MOVE":
                # --------------------
                # Character Traversal
                # --------------------
                try:
                    tool = translate_tool(index)
                    self.__tool_select(tool)
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
        if self.SIMULATE:
            logging.debug("Simulating Tool Rotation Test...")
        else:
            self.toolHomeSensor.set_falling_callback(self.__home_callback)
            # One full rotation
            expected = ToolSelector.STEPS_PER_TOOL * 8

            count = self.toolStepper.move_steps(expected, ToolSelector.POS_DIR)

            if self.toolHomeSensor.read_sensor():
                difference = expected - count
                logging.debug(f"Tool Test completed. Expected Steps = {expected}, Actual Steps = {count}, Diff = "
                              f"{difference}")

            else:
                count2 = self.toolStepper.move_steps(expected, ToolSelector.POS_DIR)
                total_count = count + count2

                logging.debug(f"Tool Test completed. Expected Steps = {expected}, Actual Steps = {total_count}, "
                              f"Diff = {count2}")

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
        if not self.SIMULATE:
            self.toolStepper.e_stop()
        self.close()

    def __tool_home(self):
        """Rotates the tool back to the blank (home) position and reports any missed or extra steps

        :return: count: number of steps taken to rotate to home position
        """
        if self.SIMULATE:
            logging.info(f"Simulating Selecting blank tool...")
            time.sleep(0.5)
            count = 0
        else:
            if self.toolHomeSensor.read_sensor():
                count = 0
            else:
                if self.currentTool > 4:
                    # Shortest travel is to wrap in forwards direction
                    direction = ToolSelector.POS_DIR
                    expected = (8 - self.currentTool) * ToolSelector.STEPS_PER_TOOL
                else:
                    # Shortest travel is to rotate in backwards direction
                    direction = ToolSelector.NEG_DIR
                    expected = self.currentTool * ToolSelector.STEPS_PER_TOOL

                self.toolHomeSensor.set_falling_callback(self.__home_callback)
                count = self.toolStepper.move_steps(expected*2, direction)

                if self.toolHomeSensor.read_sensor():
                    logging.info(f"Tool Rotated to Blank Position from tool {self.currentTool}. Expected Steps = "
                                 f"{expected}, Actual Steps = {count}")
                    self.currentTool = 0
                else:
                    count2 = self.toolStepper.move_steps(self.STEPS_PER_TOOL * 10, direction)

                    if self.toolHomeSensor.read_sensor():
                        logging.info(f"Tool Rotated to Blank Position from tool {self.currentTool}. Expected Steps = "
                                     f"{expected}, Actual Steps = {count+count2}")
                        self.currentTool = 0
                    else:
                        logging.error("Tool could not be returned home")
                        raise OperationError(__name__, 'Tool Home', "Tool home operation failed, - Blank face could "
                                                                    "not be selected")
                self.toolHomeSensor.clear_falling_callback()

        return count

    def __tool_select(self, tool):
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
        if tool == self.currentTool:
            logging.info(f"Staying at tool {self.currentTool}")
            count = 0
        elif tool == 0:
            count = self.__tool_home()
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
                movement *= -1

            steps = movement * ToolSelector.STEPS_PER_TOOL

            # Move the Stepper motor
            if self.SIMULATE:
                logging.info(f"Simulating Tool selection to tool {tool}...")
                time.sleep(0.5)
                count = steps
            else:
                count = self.toolStepper.move_steps(steps, direction)
                logging.info(f"Moved Tool from {self.currentTool} to tool {tool} in {count} steps")

        # Update the current tool attribute
        self.currentTool = tool

        return count
