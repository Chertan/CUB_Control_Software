from CUBExceptions import *
from CUBConverter import *
from BrailleKeyboard import main as bk_main
import logging
import multiprocessing as mp
import threading
import tty
import sys
import termios

INPUT_MODES = ["BKEYBOARD", "KEYBOARD", "FILE"]

FILE_LANGUAGES = ["ENG", "UEB", "BKB"]


class CUBInput:
    """Functional Class to represent input into the CUB Control system

        Attributes:

        Methods:
    """

    def __init__(self, input_mode="KEYBOARD", filename="", file_language="ENG"):
        """Creates an abstraction object of the Embosser module for the CUB

        :param filename: Optional parameter to define the input file to read the characters from
        """
        logging.info(f"Setting up Input in mode: {input_mode}")
        self.mode = input_mode

        self.runFlag = threading.Event()

        self.exit = False
        self.cub_pipe, self.input_pipe_cub = mp.Pipe()
        self.BKeyboard_pipe, self.input_pipe_BKeyboard = mp.Pipe()

        self.inFilename = filename
        self.inFileLang = file_language
        self.inFile = None
        self.p_BKeyboard = None

        self.f_stdin = sys.stdin.fileno()
        self.terminal_old = termios.tcgetattr(self.f_stdin)

    def thread_in(self):
        """Entry Point for the CUB Input component thread to begin execution

        :return: None
        """
        try:
            logging.info("Input thread Started")
            self.startup()
            self.run()

        except InitialisationError as err:
            self.stop()
            self.__output_cub(f"{err.component} ERROR: {err.message}")
        except CUBClose as close:
            self.__output_cub(f"Close Signalled from {close.exit_point} - {close.message}")
        except CommunicationError as comm:
            self.stop()
            self.__output_cub(f"{comm.component} ERROR: {comm.message} - MSG: {comm.errorInput}")
        except OperationError as op:
            self.stop()
            self.__output_cub(f"{op.component} ERROR: {op.message} - OP: {op.operation}")
        finally:
            # Clean up
            if self.inFile is not None:
                self.inFile.close()
            termios.tcsetattr(self.f_stdin, termios.TCSADRAIN, self.terminal_old)

            # Notify CUB of closure
            self.__output_cub("END OF INPUT")

            # Close Braille Keyboard process if still alive
            if self.p_BKeyboard is not None and self.p_BKeyboard.is_alive():
                self.input_pipe_BKeyboard.send("END OF INPUT")
                self.p_BKeyboard.join(timeout=2)

    def startup(self):
        """Initialises Input functions depending on input mode

        :return:
        """
        logging.info("Initialising input method")
        # -----------
        # File Input
        # -----------
        if self.mode == "FILE" and self.inFilename is not "":
            try:
                self.inFile = open(self.inFilename, "r")
                logging.info(f"CUBInput opened file with name {self.inFilename}")
            except IOError:
                raise InitialisationError(self.__class__, f"Unable to open file with name - {self.inFilename}")
        # -----------------
        # Braille Keyboard
        # -----------------
        elif self.mode == "BKEYBOARD":
            try:
                # Start Process at main function of BrailleKeyboard program
                self.p_BKeyboard = mp.Process(target=bk_main, args=(self.in_BKeyboard, self.out_BKeyboard))
                self.p_BKeyboard.start()
                logging.info("Connecting to Braille keyboard for input")
            except AttributeError:
                raise InitialisationError(self.__class__, "Unable to start Braille Keyboard Process")
 
        # ---------
        # Keyboard
        # ---------
        elif self.mode == "KEYBOARD":
            logging.info("Connecting to keyboard for input")
            tty.setraw(self.f_stdin)
        else:
            raise InitialisationError(self.__class__, f"Invalid Input Mode - {self.mode}")
        self.__output_cub("ACK")

    def run(self):
        logging.info("Starting Input Loop")
        self.runFlag.wait()
        while not self.exit:
            # Get input as a list of characters in braille cell notation
            logging.info("Taking Input from source")
            in_chars = self.take_input()

            if in_chars[0] == "END OF INPUT":
                logging.info("Input denotes end of input")
                self.exit = True
            else:
                # Output each character to the Control System
                logging.info(f"Sending input to CUB - Input: {in_chars}")
                for char in in_chars:
                    logging.info(f"Sending Character to CUB - Char: {char}")
                    self.__output_cub(char)

            # Pause if flag is not set
            self.runFlag.wait()

    def take_input(self):
        chars = []
        try:
            # ---------
            # Keyboard
            # ---------
            if self.mode == "KEYBOARD":
                logging.info("Retrieving Keyboard Input")
                char_raw = sys.stdin.read(1)
                logging.info(f"Input retreived as : {char_raw}")
                if char_raw == '\x03' or char_raw == '\x1a':
                    logging.info("Keyboard triggered Shutdown")
                    raise CUBClose("Keyboard Input", "Keyboard Interrupt received")

                chars = translate(char_raw, "ENG")

            # -----------------
            # Braille Keyboard
            # -----------------
            elif self.mode == "BRAILLE KEYBOARD":
                logging.info("Retrieving Braille Keyboard input")
                msg = self.__input_b_keyboard()
                chars = translate(msg, "BKB")

            # -----------
            # File Input
            # -----------
            elif self.mode == "FILE":
                chars = translate(self.next_file_line(), self.inFileLang, grade=2)

        except EOFError:
            chars = ["END OF INPUT"]
            logging.warning("Input Finished while reading")
        return chars

    def next_file_line(self):
        return self.inFile.readline()

    def pause_input(self):
        self.runFlag.clear()

    def start_input(self):
        self.runFlag.set()

    def stop(self):
        self.exit = True
        self.runFlag.set()

    def __output_cub(self, msg):
        """Places the argument object into the output pipe to be received by another thread

        :param msg: Message to be output to another thread
        :return: None
        """
        
        self.input_pipe_cub.send(msg)
        logging.info(f"Sent message to CUB - {msg}")

    def __input_cub(self):
        """Returns the next message in the input pipe to be received from another thread

        :return: The object received from another thread
        """
        msg = self.input_pipe_cub.recv()

        return msg 

    def send(self, msg):
        """Used by other threads to send an object to the input pipe

        :param msg: Message to be input to the Head Traverser Thread
        :return: None
        """
        self.cub_pipe.send(msg)

    def recv(self):
        """Used by other threads to send an object to the input pipe

        :return: Message output by Head Traverser
        """
        msg = self.cub_pipe.recv()
        logging.info(f"Cub received message from input - {msg}")
        return msg

    def __input_b_keyboard(self):
        """Returns the next message in the input pipe to be received from another thread

        :return: The object received from another thread
        """
        return self.input_pipe_BKeyboard.recv()

    def __output_b_keyboard(self, msg):
        """

        :param msg:
        :return:
        """
        self.input_pipe_BKeyboard.send(msg)
