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

        Attributes: mode           - Mode of input selected for operation
                    runFlag        - Flag to pause and start input operation
                    exit           - Flag to signal the input thread to finish input
                    cub_pipe       - Pipe used by the CUB thread to communicate to the Input thread
                    input_cub_pipe - Pipe used by the Input thread to communicate to the CUB thread
                    BKeyboard_pipe - Pipe used by the Braille Keyboard process to communicate to the Input thread
                    input_pipe_BKB - Pipe used by the Input thread to communicate to the Braille Keyboard process
                    p_BKeyboard    - Running process of the Braille keyboard input program
                    f_stdin        - File of the systems standard input
                    terminal_old   - Settings of the terminal before input mode was entered
                    inFilename     - File name of the input file for FILE input mode
                    inFileLang     - Language/Format of the input file (Allows for pre-translated Braille text files)
                    inFile         - File opened for file input
                    inputlogFilename        - File name of the logging file for the input characters
                    inputlogFile            - File opened for logging input characters
                    translation_logFilename - File name of the logging file for the translated input characters
                    translationlogFile      - File opened for logging translated input characters

        Methods:    thread_in()   -
                    start_input() - Sets the run Flag to true to enable the operation of the Input thread
                    pause_input() - Sets the run Flag to false to pause the operation of the Input thread
                    close()       - Sets the exit flag to true to signal for the Input thread to close
                    send(<msg>)   - Sends a message to the input thread
                    recv()        - Receives the oldest sent message from the input thread
    """

    def __init__(self, input_mode="KEYBOARD", filename="", file_language="ENG", inputlog="cub_input_log.txt",
                 translation_log="cub_translation_log.txt"):
        """Creates an abstraction object of the Embosser module for the CUB

        :param input_mode: Parameter to select the input mode to be used for input
        :param filename: Optional parameter to define the input file to read the characters from
        :param file_language: Optional parameter to select the language/format for the input file (default is English)
        :param inputlog: Optional parameter to select the logging file for the read input
        :param translation_log: Optional parameter to select the logging file for the translated input
        """
        logging.info(f"Setting up Input in mode: {input_mode}")
        # Input mode to be ran, one of the items in INPUT_MODES
        self.mode = input_mode
        # Constructs the running thread to false, input waits until told to start taking input
        self.runFlag = threading.Event()
        # Sets exit flag to false, setting to true makes thread complete operation
        self.exit = False

        # Communication pipes:
        #   cub_pipe is the CUBs pipe for communication with the input thread
        #   BKeyboard_pipe is the Braille Keyboards pip for communication with the input thread
        #   input_pipe_cub and input_pipe_BKeyboard is the Input thread pip for communication with the CUB and
        #   Braille keyboard threads respectively
        self.cub_pipe, self.input_pipe_cub = mp.Pipe()
        self.BKeyboard_pipe, self.input_pipe_BKeyboard = mp.Pipe()
        # Braille keyboard process
        self.p_BKeyboard = None

        # File name for the Input File
        self.inFilename = filename
        # Format/Language of the Input file
        self.inFileLang = file_language
        # File attribute to store link to input file
        self.inFile = None

        # File name for the input logging file
        self.inputlogFilename = inputlog
        # Link to the input logging file
        self.inputlogFile = None
        # File name for the translated input logging file
        self.translation_logFilename = translation_log
        # Link to the translated input logging file
        self.translationlogFile = None

        # Get a pointer to the standard in system file
        self.f_stdin = sys.stdin.fileno()
        # Save a copy of terminal settings to be restored once input is complete
        self.terminal_old = termios.tcgetattr(self.f_stdin)

    def thread_in(self):
        """Entry Point for the CUB Input component thread to begin execution

        :return: None
        """
        try:
            logging.debug("Input thread Started")
            # Run component startup procedure
            self.__startup()
            # Run component loop
            self.__run()

        except InitialisationError as err:
            self.close()
            self.__output_cub(f"{err.component} ERROR: {err.message}")
        except CUBClose as close:
            self.__output_cub(f"Close Signalled from {close.exit_point} - {close.message}")
        except CommunicationError as comm:
            self.close()
            self.__output_cub(f"{comm.component} ERROR: {comm.message} - MSG: {comm.errorInput}")
        except OperationError as op:
            self.close()
            self.__output_cub(f"{op.component} ERROR: {op.message} - OP: {op.operation}")
        except Exception as ex:
            self.__output_cub(f"Undefined Input ERROR: {ex}")
        finally:
            # Clean up
            if self.inFile is not None:
                self.inFile.close()
            termios.tcsetattr(self.f_stdin, termios.TCSADRAIN, self.terminal_old)

            # Notify CUB of closure
            self.__output_cub("END OF INPUT")

            # Close Braille Keyboard process if still alive
            if self.p_BKeyboard is not None and self.p_BKeyboard.is_alive():
                self.input_pipe_BKeyboard.send("CLOSE")
                self.p_BKeyboard.join(timeout=2)

    def __startup(self):
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

    def __run(self):
        # Wait until main thread signals to begin input
        self.runFlag.wait()

        # Check if
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
                sys.stdout.flush()

            logging.info("Starting Input Loop")

        # Loop until exit flag is set
        while not self.exit:
            # Get input as a list of characters in braille cell notation
            in_chars = self.__take_input()
            logging.info(f"Input from {self.mode} is: {in_chars}")

            if in_chars[0] == "END OF INPUT":
                # Close Input, outputs end of input at close
                self.exit = True
            else:
                # Output each character to the Control System
                for char in in_chars:
                    self.__output_cub(char)

            # Pause if flag is not set
            self.runFlag.wait()

    def __take_input(self):
        """Takes the next input from the current input mode and returns it translated into CUB Braille Format

        :return: list of characters in CUB Braille format
        """
        # Setup return list
        # Note: Must be list as calls to translate can convert a single character into
        #       multiple braille characters i.e capital A is capital prefix followed by a
        chars = []

        # ---------
        # Keyboard
        # ---------
        if self.mode == "KEYBOARD":
            # Read input from keyboard via stdin
            char_raw = sys.stdin.read(1)
            # Write the input character to log file
            self.inputlogFile.write(char_raw)
            logging.debug(f"Input retreived from Keyboard as : {char_raw}")

            if char_raw == '\x03' or char_raw == '\x1a' or char_raw == '^C' or char_raw == '^Z' or char_raw == '\x1b':
                # The input key was an exit key/combination
                logging.info("Keyboard triggered Shutdown")
                raise CUBClose("Keyboard Input", "Keyboard Interrupt received")
            # Translate the input into CUB Braille format (Language set for english keyboard)
            chars = translate(char_raw, "ENG")
            self.__log_input(chars)

        # -----------------
        # Braille Keyboard
        # -----------------
        elif self.mode == "BKEYBOARD":
            # Retrieve input from the braille keyboard pipe
            msg = self.__input_b_keyboard()
            logging.debug(f"Input retreived from Braille Keyboard as : {msg}")
            if msg == "END OF INPUT":
                # Input signals end of input
                chars = [msg]
                logging.info("Input Finished while reading")
            else:
                self.inputlogFile.write(msg)
                # Translate the input to CUB Braille format
                chars = translate(msg, "BKB")
                self.__log_input(chars)

        # -----------
        # File Input
        # -----------
        elif self.mode == "FILE":
            line = self.inFile.readline()
            logging.debug(f"Input retreived from File as : {line}")
            if line == "":
                # Input signals end of input
                chars = ["END OF INPUT"]
                logging.info("Input Finished while reading")
            else:
                self.inputlogFile.write(line)
                # Translate the input to CUB Braille format, grade two for full contractions
                chars = translate(line, self.inFileLang, grade=2)
                self.__log_input(chars)

        return chars

    def __log_input(self, chars):
        """Logs the translated input characters into the translation log file

        :param chars: Input characters to be logged
        :return:
        """
        # Write all translated characters to the log file
        for character in chars:
            self.translationlogFile.write(character + " ")

    def pause_input(self):
        """Sets the run Flag to false to pause the operation of the Input thread

        :return: None
        """
        self.runFlag.clear()

    def start_input(self):
        """Sets the run Flag to true to enable the operation of the Input thread

        :return: None
        """
        self.runFlag.set()

    def close(self):
        """Sets the exit flag to true to signal for the Input thread to close

        :return: None
        """
        self.exit = True
        self.runFlag.set()

    def __output_cub(self, msg):
        """Places the argument object into the output pipe to be received by another thread

        :param msg: Message to be output to another thread
        :return: None
        """
        logging.debug(f"CUBInput Sent message to CUB - {msg}")
        self.input_pipe_cub.send(msg)

    def __input_cub(self):
        """Returns the next message in the input pipe to be received from another thread

        :return: The object received from another thread
        """
        msg = self.input_pipe_cub.recv()
        logging.debug(f" CUBInput Received message from CUB - {msg}")
        return msg

    def send(self, msg):
        """Used by other threads to send a message to the input thread

        :param msg: Message to be input to the Head Traverser Thread
        :return: None
        """
        self.cub_pipe.send(msg)

    def recv(self):
        """Used by other threads to receive a message from the input thread

        :return: Message output by Head Traverser
        """
        msg = self.cub_pipe.recv()
        logging.debug(f"Cub received message from input - {msg}")

        # Print to screen as progress indicator of file printing
        if self.mode == "FILE":
            print(".", end='')
            sys.stdout.flush()

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
