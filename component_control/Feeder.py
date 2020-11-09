# Class: DCOutputDevice
# Desc: Hardware interface class to handle the control of a stepper motor
# Params: in_direction is the gpio pin number of the direction wire of the motor
#         in_step is the gpio pin number of the step wire of the motor
#         in_enable is the gpio pin number of the enable wire of the motor
#         in_start_speed is the starting speed of the motor
#         in_max_speed is the maximum speed of the motor
#
# Functions: move_steps(<number of steps>, <direction of movement(0 | 1)> )
#               - rotates the motor the input number of steps
#            move_until(<condition function>, <direction of movement (0 | 1)> )
#               - rotates the motor in the input direction until the condition function returns true
from component_control.hardware_interface.StepperMotor import StepperMotor
from component_control.hardware_interface.DCOutputDevice import DCOutputDevice
from component_control.hardware_interface.PhotoSensor import PhotoSensor
from CUBExceptions import *
import logging
import multiprocessing



class Feeder:

    # // Line Feed Stepper Motor //
    # GPIO pins of the line feed stepper motor
    LNFDIR = 24
    LNFSTEP = 18
    LNFENA = 23
    # Motor speed parameters to be tuned during testing
    START_SPEED = 5
    MAX_SPEED = 10
    RAMP_RATE = 1

    # Motor directional parameters
    LNF_POS_DIR = 1
    LNF_NEG_DIR = 0
    # Max number of lines on Eject
    LNF_MAX_LINES = 50

    # // Paper Feed DC Motor //
    # GPIO pins of the paper feed DC motor
    PPRDIR = 25
    PPRENA = 12
    # Motor Directional parameters
    PPR_POS_DIR = 1
    PPR_NEG_DIR = 0
    # Timeout length for feeding paper from tray
    FEED_TIMEOUT = 5

    # // Input Side Paper Sensor //
    # GPIO pin of the input side paper sensor
    PBOTPS = 22
    # GPIO Input for the sensor to return True
    PBOTPS_TRUE = 0

    # // Output Side Paper Sensor //
    # GPIO pin of the output side paper sensor
    PTOPPS = 17
    # GPIO Input for the sensor to return True
    PBTOPPS_TRUE = 0

    # // Paper Width in Characters //
    # Dimensions of A4 Paper
    A4_CELLS = 20
    A4_LINES = 27
    # Dimensions of Braille Paper
    BRAILLE_CELLS = 40
    BRAILLE_LINES = 30

    # Steps between lines
    LINE_STEPS = 8

    # // A4 Paper Size Sensor //
    # GPIO pin of the A4 size paper sensor
    A4PPRPS = 14
    # GPIO Input for the sensor to return True
    A4PPRPS_TRUE = 0

    # // Braille Paper Size Sensor //
    # GPIO pin of the A4 size paper sensor
    BPPRPS = 15
    # GPIO Input for the sensor to return True
    BPPRPS_TRUE = 0

    def __init__(self, simulate=False):
        """Creates an abstraction object of the Line Feeder module for the CUB

        """
        # Flag to enable or disable simulation of outputs
        # Allows for testing of system software without needing devices connected
        # - Current set to true as system is not yet developed
        self.SIMULATE = simulate
        if self.SIMULATE:
            logging.info("Setting up Feeder as Simulated Component.")

        # Define Tool stepper motor
        self.LineStepper = StepperMotor(Feeder.LNFDIR, Feeder.LNFSTEP, Feeder.LNFENA,
                                        Feeder.START_SPEED, Feeder.MAX_SPEED, Feeder.RAMP_RATE)
        logging.info(f"Setting up Line Feed Stepper with STEP Pin: {Feeder.LNFSTEP}")

        # Define Paper Feed DC Motor
        self.PaperFeed = DCOutputDevice(Feeder.PPRDIR, Feeder.PPRENA)
        logging.info(f"Setting up Paper Feed Motor with ENA Pin: {Feeder.PPRENA}")

        # Define Paper input side Photo interrupter sensor, input is 0 when beam is cut
        self.LineInputSensor = PhotoSensor(Feeder.PBOTPS, Feeder.PBOTPS_TRUE)
        logging.info(f"Setting up Paper Input Sensor on Pin: {Feeder.PBOTPS}")

        # Define Paper output side Photo interrupter sensor, input is 0 when beam is cut
        self.LineOutputSensor = PhotoSensor(Feeder.PTOPPS, Feeder.PBTOPPS_TRUE)
        logging.info(f"Setting up Paper Output Sensor on Pin: {Feeder.PTOPPS}")

        # Define A4 Paper size Photo reflector sensor, input is 0 when paper is present
        self.A4PaperSensor = PhotoSensor(Feeder.A4PPRPS, Feeder.A4PPRPS_TRUE)
        logging.info(f"Setting up A4 Paper Size Sensor on Pin: {Feeder.A4PPRPS}")

        # Define Braille Paper size Photo reflector sensor, input is 0 when paper is present
        self.BraillePaperSensor = PhotoSensor(Feeder.BPPRPS, Feeder.BPPRPS_TRUE)
        logging.info(f"Setting up Braille Paper Size Sensor on Pin: {Feeder.BPPRPS}")

        # Exit flag for when to stop operation
        self.exit = False

        # cub_pipe is The CUB's end of the pipe
        # feeder_pipe is the Feeder's end of the pipe
        self.cub_pipe, self.feeder_pipe = multiprocessing.Pipe()

    def thread_in(self):
        """Entrance point for the Feeder component thread

        :return: 0 to confirm successful close of thread
        """
        try:
            logging.debug("Feeder thread Started")
            # Run component startup procedure
            self.startup()
            # Run component loop
            self.run()

        except InitialisationError as err:
            # Exception raised while initialising component
            self.emergency_stop()
            self.__output(f"{err.component} ERROR: {err.message}")

        except KeyboardInterrupt:
            # Interrupt raised from keyboard - Should never occur
            self.emergency_stop()

        except CommunicationError as comm:
            # Exception raised during communication
            self.emergency_stop()
            self.__output(f"{comm.component} ERROR: {comm.message} - MSG: {comm.errorInput}")

        except OperationError as op:
            # Exception raised during operation
            self.emergency_stop()
            self.__output(f"{op.component} ERROR: {op.message} - OP: {op.operation}")

        except Exception as ex:
            self.__output(f"Feeder ERROR: {ex}")

        finally:
            return 0

    def startup(self):
        """Startup procedure of the feeder system, to be impletment with construction of system

        :return:
        """
        if self.SIMULATE:
            logging.info("Simulating Feeder Startup")
        else:
            logging.info("Performing Feeder Startup")
            # Perform Startup - Develop with feeder system

        self.__output("ACK")

    def run(self):
        while not self.exit:
            # Get Input from Main Thread
            key, index, direction = self.__input()
            # ------------------------------------------
            # Close Command
            # ------------------------------------------
            if key == "CLOSE":
                # Close program
                self.close()
            # ------------------------------------------
            # FEED Command
            # ------------------------------------------
            elif key == "FEED":
                try:
                    steps = int(index)
                except ValueError:
                    raise CommunicationError(self.__class__, index, "Index conversion to Integer Failed")
                # --------------
                # Positive Feed
                # --------------
                if direction == "POS":
                    self.feed_lines(steps)
                # --------------
                # Negative Feed
                # --------------
                elif direction == "NEG":
                    self.feed_lines(steps, reverse=True)
                else:
                    raise CommunicationError(self.__class__, direction, "Direction portion of message for "
                                                                        "line feed")
            # ------------------------------------------
            # Paper Commands
            # ------------------------------------------
            elif key == "PAPER":
                # --------------------
                # Character Traversal
                # --------------------
                if index == "FEED":
                    self.feed_paper()
                # ------------
                # Eject Paper
                # ------------
                elif index == "EJECT":
                    self.eject()
                else:
                    raise CommunicationError(self.__class__, index, "Index portion of message for "
                                                                    f"{key} operation")
            else:
                raise CommunicationError(self.__class__, key, "Key portion of message")

            # If no exceptions are raised, acknowledge task complete
            self.__output("ACK")

    def __output(self, msg):
        """Places the argument message into the pipe to be received by the cub thread

        :param msg: Message to be output to another thread
        :return: None
        """
        logging.debug(f"Feeder Sending MSG: {msg}")
        self.feeder_pipe.send(msg)

    def __input(self):
        """Returns the next message in the pipe to be received from the CUB thread

        :return: Message received from the CUB thread
        :rtype string
        """
        msg = self.feeder_pipe.recv()
        logging.debug(f"Feeder Received MSG: {msg}")

        msg_split = msg.split()
        for i in range(3 - len(msg_split)):
            msg_split.append("NULL")
        key = msg_split[0]
        index = msg_split[1]
        direction = msg_split[2]

        return key, index, direction

    def send(self, msg):
        """Retrieves a message from the pipe that as been sent by the Feeder Thread

        :return: None
        """
        self.cub_pipe.send(msg)

    def recv(self):
        """Retrieves a message from the pipe that as been sent by the Feeder Thread

        :return: Object output by Fedder
        """
        return self.cub_pipe.recv()

    def close(self):
        self.exit = True

    def emergency_stop(self):
        if not self.SIMULATE:
            self.LineStepper.e_stop()
            self.PaperFeed.e_stop()
        self.close()

    def get_paper_size(self):
        """Returns the number of cells that fit on the currently loaded paper or zero if tray is empty

        :return: Width of paper in cells
        """
        if self.SIMULATE:
            out = Feeder.A4_CELLS
            logging.info(f"Simulating Get Paper Width Operation, return value of {out}...")
        else:
            # Test sensors for which is not or if paper is empty
            out = 0
            if self.A4PaperSensor.read_sensor():
                out = Feeder.A4_CELLS
            if self.BraillePaperSensor.read_sensor():
                out = Feeder.BRAILLE_CELLS

        return out

    def get_paper_length(self):
        """Returns the number of lines that fit on the currently loaded paper or zero if the tray is empty

        :return: Length of paper in lines
        """
        if self.SIMULATE:
            out = Feeder.A4_LINES
            logging.info(f"Simulating Get Paper Length Operation, return value of {out}...")
        else:
            # Test sensors for which is not or if paper is empty
            out = 0
            if self.A4PaperSensor.read_sensor():
                out = Feeder.A4_LINES
            if self.BraillePaperSensor.read_sensor():
                out = Feeder.BRAILLE_LINES

        return out

    def feed_line(self, reverse=False):
        """Performs a single line feed operation to move the position of the head on the page by one line

        :param reverse: Optional Parameter to indicate feeding in the reverse direction
        :return:
        """
        if self.SIMULATE:
            logging.info("Simulating Feed Line Operation...")
        else:
            # Feed a single line
            if not reverse:
                self.LineStepper.move_steps(Feeder.LINE_STEPS, Feeder.LNF_POS_DIR)
                logging.info(f"Feeding line in the Positive Direction")
            else:
                self.LineStepper.move_steps(Feeder.LINE_STEPS, Feeder.LNF_NEG_DIR)
                logging.info(f"Feeding line in the Negative Direction")

    def feed_lines(self, count, reverse=False):
        """Performs multiple line feed operations to move the position of the head on the page by a number of lines

        :param count: Number of lines to feed
        :param reverse: Optional Parameter to indicate feeding in the reverse direction
        :return:
        """
        for i in range(count):
            self.feed_line(reverse=reverse)

    def feed_paper(self):
        """Loads paper into embossing area

        :return: None
        """
        if self.SIMULATE:
            logging.info("Simulating Feeder Page Feed Operation...")

        else:
            # Activate motor until paper detected at
            if not self.LineInputSensor.read_sensor():
                self.LineInputSensor.set_rising_callback(self.__load_callback)

                self.PaperFeed.pulse(Feeder.PPR_POS_DIR, duration=Feeder.FEED_TIMEOUT)
                self.LineInputSensor.clear_rising_callback()

                if self.LineInputSensor.read_sensor():
                    raise OperationError(self.__class__, __name__, "Paper not detected after feeding")

            else:
                # Still Paper Loaded
                raise OperationError(self.__class__, __name__, "Can't Feed paper, paper detected in embosser")

    def eject(self):
        """Ejects the currently loaded paper from the embossing area

        :return: None
        """
        if self.SIMULATE:
            logging.info("Simulating Feeder Page Eject Operation...")
        else:
            if self.LineOutputSensor.read_sensor():
                self.LineOutputSensor.set_falling_callback(self.__eject_callback)

                self.feed_lines(Feeder.LNF_MAX_LINES)

                self.LineOutputSensor.clear_falling_callback()

                if self.LineOutputSensor.read_sensor():
                    raise OperationError(self.__class__, __name__, "Paper still detected after ejection")
            else:
                # No Paper Loaded
                raise OperationError(self.__class__, __name__, "No paper detected to eject")

    def __eject_callback(self, gpio, level, tick):
        """Callback function called when the Output side sensor no longer detects paper

        :param gpio: Pin that triggered callback
        :param level: Level of the pin that triggered callback
        :param tick: Timing value to represent when the trigger ocured
        :return: None
        """
        self.LineStepper.stop()

    def __load_callback(self, gpio, level, tick):
        """Callback function called when input Side Sensor detects paper

        :param gpio: Pin that triggered callback
        :param level: Level of the pin that triggered callback
        :param tick: Timing value to represent when the trigger ocured
        :return: None
        """
        self.PaperFeed.stop()
