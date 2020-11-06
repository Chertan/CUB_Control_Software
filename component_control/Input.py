from CUBExceptions import *
from component_control.Translator import *
from BrailleKeyboard import main as bk_main
import logging
import multiprocessing as mp
import threading
import tty
import sys
import termios

INPUT_MODES = ["BKEYBOARD", "KEYBOARD", "FILE"]

FILE_LANGUAGES = ["ENG", "UEB", "BKB"]


class Input:
    """Functional Class to represent input into the CUB Control system

        Attributes:

        Methods:
    """

    def __init__(self, input_mode="KEYBOARD", filename="", file_language="ENG", inputlog="cub_input_log.txt", translation_log="cub_translation_log.txt"):
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

        self.inputlogFilename = inputlog
        self.inputlogFile = None
        self.translation_logFilename = translation_log
        self.translationlogFile = None

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
            self.close()
            logging.error(f"{err.component} ERROR: {err.message}")
        except CUBClose as close:
            logging.warning(f"Close Signalled from {close.exit_point} - {close.message}")
        except CommunicationError as comm:
            self.close()
            logging.error(f"{comm.component} ERROR: {comm.message} - MSG: {comm.errorInput}")
        except OperationError as op:
            self.close()
            logging.error(f"{op.component} ERROR: {op.message} - OP: {op.operation}")
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
        try:
            self.inputlogFile = open(self.inputlogFilename, 'w')
            self.inputlogFile.write("Log file of the CUB Input\n")
            self.translationlogFile = open(self.translation_logFilename, 'w')
            self.inputlogFile.write("Log file of the CUB Translated Input\n")
        except IOError:
                raise InitialisationError("CUBInput", f"Unable to open file with name - {self.inFilename}")
        # -----------
        # File Input
        # -----------
        if self.mode == "FILE" and self.inFilename is not "":
            try:
                self.inFile = open(self.inFilename, "r")
                logging.info(f"CUBInput opened file with name {self.inFilename}")
            except IOError:
                raise InitialisationError("CUBInput", f"Unable to open file with name - {self.inFilename}")
        # -----------------
        # Braille Keyboard
        # -----------------
        elif self.mode == "BKEYBOARD":
            try:
                # Start Process at main function of BrailleKeyboard program
                self.p_BKeyboard = mp.Process(target=bk_main, kwargs={'pipe': self.BKeyboard_pipe})
                self.p_BKeyboard.start()
                logging.info("Connecting to Braille keyboard for input")
            except AttributeError:
                raise InitialisationError("CUBInput", "Unable to start Braille Keyboard Process")

        # ---------
        # Keyboard
        # ---------
        elif self.mode == "KEYBOARD":
            logging.info("Connecting to keyboard for input")

        else:
            raise InitialisationError("CUBInput", f"Invalid Input Mode - {self.mode}")
        self.__output_cub("ACK")

    def run(self):
        self.runFlag.wait()
        if not self.exit:
            if self.mode == "KEYBOARD":
                self.inputlogFile.write("Reading Input from Keyboard\n")
                self.inputlogFile.write("------------------------------\n")
                print("\nKeyboard connected for input: type to print to the Curtin University Brailler")
                print("To Exit, press ESC, CTRL-C or CTRL-Z")
                print("-----------------------------------------------------------------------------")
                tty.setraw(self.f_stdin)
            elif self.mode == "FILE":
                self.inputlogFile.write(f"Reading Input from File: {self.inFilename}\n")
                self.inputlogFile.write("------------------------------\n")
                print(f"Translating and outputting from file: {self.inFilename}")
                print("Printing", end='')

            logging.info("Starting Input Loop")

        while not self.exit:
            # Get input as a list of characters in braille cell notation
            logging.info("Taking Input from source")
            in_chars = self.take_input()
            logging.info(f"Input is: {in_chars}")

            if in_chars[0] == "END OF INPUT":
                logging.info("Input denotes end of input")
                self.exit = True
            else:
                # Output each character to the Control System
                logging.info(f"Sending input to CUB - Input: {in_chars}")
                for char in in_chars:
                    logging.info(f"Sending Character to CUB - Char: {char}")
                    self.__output_cub(char)

            if self.mode == "FILE":
                print(".",end='')
                sys.stdout.flush()
            # Pause if flag is not set
            self.runFlag.wait()

    def take_input(self):
        chars = []

        # ---------
        # Keyboard
        # ---------
        if self.mode == "KEYBOARD":
            logging.info("Retrieving Keyboard Input")
            char_raw = sys.stdin.read(1)
            self.inputlogFile.write(char_raw)
            logging.info(f"Input retreived as : {char_raw}")
            if char_raw == '\x03' or char_raw == '\x1a' or char_raw == '^C' or char_raw == '^Z' or char_raw == '\x1b':
                logging.info("Keyboard triggered Shutdown")
                raise CUBClose("Keyboard Input", "Keyboard Interrupt received")

            chars = translate(char_raw, "ENG")
            for character in chars:
                self.translationlogFile.write(character + " ")

        # -----------------
        # Braille Keyboard
        # -----------------
        elif self.mode == "BKEYBOARD":
            logging.info("Retrieving Braille Keyboard input")
            msg = self.__input_b_keyboard()
            if msg == "END OF INPUT":
                logging.warning("Input Finished while reading")
                chars = [msg]
            else:
                self.inputlogFile.write(msg)
                chars = translate(msg, "BKB")
                for character in chars:
                    self.translationlogFile.write(character+ " ")

        # -----------
        # File Input
        # -----------
        elif self.mode == "FILE":
            line = self.inFile.readline()
            if line == "":
                chars = ["END OF INPUT"]
                logging.warning("Input Finished while reading")
            else:
                self.inputlogFile.write(line)
                chars = translate(line, self.inFileLang, grade=2)
                for character in chars:
                    self.translationlogFile.write(character+ " ")
        return chars

    def logInput(chars):
        for character in chars:
            self.translationlogFile.write(character)

    def pause_input(self):
        self.runFlag.clear()

    def start_input(self):
        self.runFlag.set()

    def close(self):
        self.exit = True
        self.runFlag.set()

    def __output_cub(self, msg):
        """Places the argument object into the output pipe to be received by another thread

        :param msg: Message to be output to another thread
        :return: None
        """
        logging.info(f"CUBInput Sent message to CUB - {msg}")
        self.input_pipe_cub.send(msg)

    def __input_cub(self):
        """Returns the next message in the input pipe to be received from another thread

        :return: The object received from another thread
        """
        msg = self.input_pipe_cub.recv()
        logging.info(f" CUBInput Received message from CUB - {msg}")
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
