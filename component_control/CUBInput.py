from CUBExceptions import *
from EnglishCUBConverter import *
from BrailleKeyboard import main as bk_main
import logging
import multiprocessing as mp
import threading
import tty
import sys
import termios


class CUBInput:
    """Functional Class to represent input into the CUB Control system

        Attributes:

        Methods:
    """

    def __init__(self, input_mode="KEYBOARD"):
        """Creates an abstraction object of the Embosser module for the CUB

        """
        logging.info(f"Setting up Input in mode: {input_mode}")
        self.mode = input_mode

        self.runFlag = threading.Event()

        self.exit = False
        self.in_cub, self.out_cub = mp.Pipe()
        self.in_BKeyboard, self.out_BKeyboard = mp.Pipe()

        self.inFile = None
        self.p_BKeyboard = None

        self.f_stdin = sys.stdin.fileno()
        self.terminal_old = termios.tcgetattr(self.f_stdin)

    def thread_in(self, filename=""):
        """Entry Point for the CUB Input component thread to begin execution

        :param filename: Optional parameter to define the input file to read the characters from
        :return: None
        """
        try:
            self.startup(filename)
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
            self.inFile.close()
            termios.tcsetattr(self.f_stdin, termios.TCSADRAOM, self.terminal_old)

            # Notify CUB of closure
            self.__output_cub("END OF INPUT")

            # Close Braille Keyboard process if still alive
            if self.p_BKeyboard.is_alive():
                self.out_BKeyboard.send("END OF INPUT")
                self.p_BKeyboard.join(timeout=10)

    def startup(self, filename):
        """Initialises Input functions depending on input mode

        :param filename:
        :return:
        """
        # -----------
        # File Input
        # -----------
        if self.mode == "FILE" and filename is not "":
            try:
                self.inFile = open(filename, "r")
                logging.info(f"CUBInput opened file with name {filename}")
            except IOError:
                raise InitialisationError(self.__class__, f"Unable to open file with name - {filename}")
        # -----------------
        # Braille Keyboard
        # -----------------
        elif self.mode == "BRAILLE KEYBOARD":
            try:
                # Start Process at main function of BrailleKeyboard program
                self.p_BKeyboard = mp.Process(target=bk_main, args=(self.in_BKeyboard, self.out_BKeyboard))
                self.p_BKeyboard.start()
            except AttributeError:
                raise InitialisationError(self.__class__, "Unable to start Braille Keyboard Process")

        # ---------
        # Keyboard
        # ---------
        elif self.mode == "KEYBOARD":
            tty.setraw(self.f_stdin)
        else:
            raise InitialisationError(self.__class__, f"Invalid Input Mode - {self.mode}")
        self.__output_cub("ACK")

    def run(self):
        self.runFlag.wait()

        while not self.exit:
            # Get input as a list of characters in braille cell notation
            in_chars = self.take_input()

            if in_chars[0] == "END OF INPUT":
                self.exit = True
            else:
                # Output each character to the Control System
                for char in in_chars:
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
                char_raw = sys.stdin.read(1)
                if char_raw == '\x03' or '\x1a':
                    raise CUBClose("Keyboard Input", "Keyboard Interrupt received")

                    logging.info("Keyboard triggered Shutdown")
                chars = translate(char_raw)

            # -----------------
            # Braille Keyboard
            # -----------------
            elif self.mode == "BRAILLE KEYBOARD":
                msg = self.__input_b_keyboard()
                chars = translate_b_keyboard(msg)

            # -----------
            # File Input
            # -----------
            elif self.mode == "FILE":
                chars = translate(self.next_file_char(), grade=2)

        except EOFError:
            chars = "END OF INPUT"
            logging.warning("Input Finished while reading")
        return chars

    def next_file_char(self):
        return self.inFile.readline()

    def pause_input(self):
        self.runFlag.clear()

    def start_input(self):
        self.runFlag.set()

    def stop(self):
        self.exit = True

    def __output_cub(self, msg):
        """Places the argument object into the output pipe to be received by another thread

        :param msg: Message to be output to another thread
        :return: None
        """
        self.out_cub.send(msg)

    def __input_cub(self):
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

    def send_cub(self, msg):
        """Used by other threads to send an object to the input pipe

        :param msg: Message to be input to the Head Traverser Thread
        :return: None
        """
        self.in_cub.send(msg)

    def recv_cub(self):
        """Used by other threads to send an object to the input pipe

        :return: Message output by Head Traverser
        """
        return self.out_cub.recv()

    def __input_b_keyboard(self):
        """Returns the next message in the input pipe to be received from another thread

        :return: The object received from another thread
        """
        return self.in_BKeyboard.recv()

    def __output_b_keyboard(self, msg):
        """

        :param msg:
        :return:
        """
        self.out_BKeyboard.send(msg)