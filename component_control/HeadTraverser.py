from component_control.hardware_interface.StepperMotor import StepperMotor
from component_control.hardware_interface.PhotoSensor import PhotoSensor
from CUBExceptions import *
import time
import multiprocessing
import logging


class HeadTraverser:
    """Abstraction Class to represent the Head Traversal mechanism for the CUB

        Attributes: traverseStepper    - Stepper motor class to represent the Traversal stepper motor
                    traverseHomeSensor - PhotoSensor class to represent the Photosensor used to detect the traversal
                                         home position
                    currentStep        - Tracks current position of head in number of steps from the home position
                    exit               - Boolean flag to denote when the component had been notified to close

        Methods:    thread_in()      - Entry point for the operational thread
                    send(<msg>)      - Sends the input message to the running thread
                    recv()           - Returns the message at the front of the output queue from the running thread
                    close()          - Notifies the running thread to close
                    emergency_stop() - Shuts down operation of the component
    """
    # GPIO pins of the head traversal stepper motor
    TRAVDIR = 21
    TRAVSTEP = 20
    TRAVENA = 16

    # Motor speed parameters to be tuned during testing
    START_SPEED = 400
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

    def __init__(self, simulate=False):
        """Creates an abstraction object of the Head Traverser module for the CUB

        """
        # Flag to enable or disable simulation of outputs
        # Allows for testing of system software without needing devices connected
        self.SIMULATE = simulate
        if self.SIMULATE:
            logging.info("Setting up Traverser as Simulated Component.")
        else:
            logging.info(f"Setting up Traverser with STEP Pin: {HeadTraverser.TRAVSTEP}")

        # Define Tool stepper motor
        self.traverseStepper = StepperMotor(HeadTraverser.TRAVDIR, HeadTraverser.TRAVSTEP, HeadTraverser.TRAVENA,
                                            HeadTraverser.START_SPEED, HeadTraverser.MAX_SPEED, HeadTraverser.RAMP_RATE)

        # Photo interrupter sensor reads 0 when beam is cut
        self.traverseHomeSensor = PhotoSensor(HeadTraverser.TRAVPS, HeadTraverser.PS_TRUE)

        # Tracks the current position of the embossing head
        self.currentStep = HeadTraverser.MAX_TRAV_STEPS

        # Exit flag for when to stop operation
        self.exit = False

        # cub_pipe is The CUB's end of the pipe
        # head_pipe is the HeadTraverser's end of the pipe
        self.cub_pipe, self.head_pipe = multiprocessing.Pipe()

    def thread_in(self):
        """Entrance point for the Head Traverser component thread

        :return: 0 to confirm successful close of thread
        """
        try:
            logging.debug("Traverser thread Started")
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
            self.__output(f"Undefined Traverser ERROR: {ex}")
        finally:
            self.emergency_stop()
            return 0

    def __output(self, msg):
        """Places the argument message into the pipe to be received by the cub thread

        :param msg: Message to be sent to another thread
        :return: None
        """
        logging.debug(f"HeadTraverser Sending MSG: {msg}")
        self.head_pipe.send(msg)

    def __input(self):
        """Returns the next message in the pipe to be received from the cub thread

        :return: The message received from another thread
        """
        msg = self.head_pipe.recv()
        logging.debug(f"HeadTraverser Received MSG: {msg}")

        msg_split = msg.split()
        for i in range(4 - len(msg_split)):
            msg_split.append("NULL")
        key = msg_split[0]
        index = msg_split[1]
        direction = msg_split[2]
        count = msg_split[3]

        return key, index, direction, count

    def send(self, msg):
        """Places a message into the pipe to be received by the Traverser Thread

        :param msg: Object to be input to the Head Traverser Thread
        :return: None
        """
        self.cub_pipe.send(msg)

    def recv(self):
        """Retrieves a message from the pipe that as been sent by the Traverser Thread

        :return: Object output by Head Traverser
        """
        return self.cub_pipe.recv()

    def __startup(self):
        """Runs a startup test of the Head Traverser module

        :return: None
        """
        if self.SIMULATE:
            logging.info(f"Simulating Head movement test...")
            self.__output("ACK")
        else:
            logging.info("Performing Traverser Startup")

            count = self.__traverse_home()

            if count > HeadTraverser.MAX_TRAV_STEPS:
                logging.error("Unable to return the Embosser Head to the home position")
                raise InitialisationError(self.__class__, "Unable to return the Embosser Head to the home position")

            self.__movement_test()
            if self.traverseHomeSensor.read_sensor():
                self.__output("ACK")
            else:
                logging.error("Head Not at Home After Test")
                raise InitialisationError(self.__class__, "Unable to return the Embosser Head to the home position")

    def __run(self):
        while not self.exit:
            # Get Input from Main Thread
            key, index, direction, count = self.__input()
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
                self.__traverse_home()
            # ------------------------------------------
            # Move Commands
            # ------------------------------------------
            elif key == "MOVE":
                # Set Movement count
                if count != "NULL":
                    try:
                        count = int(count)
                    except ValueError:
                        raise CommunicationError(self.__class__, count, "Conversion to Integer Failed")
                else:
                    count = 1
                # --------------------
                # Character Traversal
                # --------------------
                if index == "CHAR":
                    if direction == "POS":
                        self.__traverse_character(count=count)
                    elif direction == "NEG":
                        self.__traverse_character(reverse=True, count=count)
                    else:
                        raise CommunicationError(self.__class__, direction, "Direction portion of message for "
                                                                            f"{index} operation")
                # -----------------
                # Column Traversal
                # -----------------
                elif index == "COL":
                    if direction == "POS":
                        self.__traverse_column(count=count)
                    elif direction == "NEG":
                        self.__traverse_column(reverse=True, count=count)
                    else:
                        raise CommunicationError(self.__class__, direction, "Direction portion of message for "
                                                                            f"{index} operation")
                else:
                    raise CommunicationError(self.__class__, index, "Index portion of message for "
                                                                    f"{key} operation")
            else:
                raise CommunicationError(self.__class__, key, "Key portion of message")

            # If no exceptions are raised, acknowledge task complete
            self.__output("ACK")

    def close(self):
        """Notifys the Head traverser thread to close

        :return: None
        """
        self.exit = True

    def __movement_test(self):
        """Complete a movement test of the Head Traversal Module
        Moves forward and backwards by half the maximum and reports any difference in expected steps

        :return: None
        """
        if self.SIMULATE:
            logging.debug(f"Simulating Head movement test...")
            out = 0
        else:
            self.traverseHomeSensor.set_rising_callback(self.__home_callback)

            self.traverseStepper.move_steps(round(HeadTraverser.MAX_TRAV_STEPS / 2), HeadTraverser.POS_DIR)

            count = self.traverseStepper.move_steps(round(HeadTraverser.MAX_TRAV_STEPS / 2), HeadTraverser.NEG_DIR)

            if self.traverseHomeSensor.read_sensor():
                logging.debug(f"Tool Movement Test Completed. Expected Steps = {HeadTraverser.MAX_TRAV_STEPS/2}, "
                              f"Steps taken = {count}")
                out = count
            else:
                exp = count
                count = self.traverseStepper.move_steps(HeadTraverser.MAX_TRAV_STEPS - count, HeadTraverser.NEG_DIR)
                logging.debug(f'Tool Movement Test Completed. Expected Steps = {HeadTraverser.MAX_TRAV_STEPS/2}, '
                              f'Actual Steps = {exp + count}')
                out = count + exp

            self.traverseHomeSensor.clear_rising_callback()

        return out

    def __home_callback(self, gpio, level, tick):
        """Callback function called when the home photosensor detects the tool head in the home position

        :param gpio: Pin that triggered callback
        :param level: Level of the pin that triggered callback
        :param tick: Timing value to represent when the trigger ocured
        :return: None
        """
        # Logging commented to prevent unnecessary overhead in the callback to ensure quick reponse
        # Uncomment to aid in debugging
        # logging.debug("Traverser Callback Triggered")
        self.traverseStepper.stop()

    def emergency_stop(self):
        """Stops the traversal motor to a state that requires a hard restart of the program

        :return: None
        """
        if not self.SIMULATE:
            self.traverseStepper.e_stop()
        self.close()

    def __traverse_home(self):
        """Traverse the head back to the home position of the brailler

        :return: count: Number of steps taken to return home
        """
        if self.SIMULATE:
            logging.info(f"Simulating Head Traversal to Home...")
            time.sleep(0.5)
            count = 0
        else:
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
                    while not self.traverseHomeSensor.read_sensor() and not self.exit:
                        exp += count
                        count = self.traverseStepper.move_steps(20, HeadTraverser.NEG_DIR)
                        logging.info(f"Tool Returned Home. Expected Steps = {exp}, Actual Steps = {exp + count}")

                        self.traverseHomeSensor.clear_rising_callback()

        self.currentStep = 0

        return count

    def __traverse_column(self, reverse=False, count=1):
        """Traverses the distance between two columns of a single braille cell

        :param reverse: Optional parameter to reverse direction of traversal
        :param count: Optional parameter to perform multiple operations at once
        :return: None
        """
        if reverse:
            if self.SIMULATE:
                logging.info(f"Simulating Head Traversal of Column in Negative Dir, count:{count}...")
                time.sleep(0.5)
            else:
                logging.info(f"Completing Head Traversal of Column in Negative Dir, count:{count}...")
                self.traverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_COLUMN*count, HeadTraverser.NEG_DIR)
                self.currentStep -= HeadTraverser.STEPS_BETWEEN_COLUMN * count
        else:
            if self.SIMULATE:
                logging.info(f"Simulating Head Traversal of Column in Positive Dir, count:{count}...")
                time.sleep(0.5)
            else:
                logging.info(f"Completing Head Traversal of Column in Positive Dir, count:{count}...")
                self.traverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_COLUMN*count, HeadTraverser.POS_DIR)
                self.currentStep += HeadTraverser.STEPS_BETWEEN_COLUMN * count

    def __traverse_character(self, reverse=False, count=1):
        """Traverse the head by the spacing between braille cells

        :param reverse: Optional parameter to reverse direction of traversal
        :param count: Optional parameter to perform multiple operations at once
        :return: None
        """
        if reverse:
            if self.SIMULATE:
                logging.info(f"Simulating Head Traversal of Character in Negative Dir, count:{count}...")
                time.sleep(0.5)
            else:
                logging.info(f"Completing Head Traversal of Character in Negative Dir, count:{count}...")
                self.traverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_CHAR*count, HeadTraverser.NEG_DIR)
                self.currentStep -= HeadTraverser.STEPS_BETWEEN_CHAR * count
        else:
            if self.SIMULATE:
                logging.info(f"Simulating Head Traversal of Character in Positive Dir, count:{count}...")
                time.sleep(0.5)
            else:
                logging.info(f"Completing Head Traversal of Character in Positive Dir, count:{count}...")
                self.traverseStepper.move_steps(HeadTraverser.STEPS_BETWEEN_CHAR*count, HeadTraverser.POS_DIR)
                self.currentStep += HeadTraverser.STEPS_BETWEEN_CHAR * count
