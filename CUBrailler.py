from component_control.ToolSelector import ToolSelector
from component_control.HeadTraverser import HeadTraverser
from component_control.Embosser import Embosser
from component_control.Feeder import Feeder
from component_control.Input import Input
from component_control.Input import INPUT_MODES
from component_control.Input import FILE_LANGUAGES
from CUBExceptions import *
import sys
import argparse
import logging
from threading import Thread

# String literal for component acknowledgements
ACK = "ACK"

# Global flag for enabling word wrapping on new lines
word_wrap = True

# Container dictionary for all component Objects
components = {}
# Container dictionary for all component Threads
threads = {}
# Counter dictionary for the current number of outstanding tasks for each component
tasks = {}

# Tracks current position on page
current_line = 1
current_char = 0

# Shared variable for the last character printed
last_char = ''


def main():
    """Main function for the Curtin University Brailler(CUB) Control system

    :return: 0 on successful exit
    """
    try:
        # Retrieve arguments from the command line
        mode, filename, file_language, level, logfile = get_args()

        # Enable logging as per arguments
        setup_logging(level, logfile)

        print("=============================================")
        print(" Curtin University Brailler Control Software")
        print("=============================================")

        # Create component objects and start threads
        # Also runs startup procedures and ensures components return positive acknowledgements
        initialise_components(mode, filename, file_language)

        # Run the main loop of the System, returns on error or end of input.
        cub_loop()

    except KeyboardInterrupt:
        # Interrupt from the command line
        logging.warning("Shutting Down due to Keyboard Interrupt")
        print("")

    except ArgumentError as err:
        # Exception when parsing command line arguments
        logging.error(f"Error parsing Argument {err.argumentName}: {err.message}")
        # Prints the argument help prompt to the screen
        print(err.argHelp)

    except InitialisationError as err:
        # Exception while initialising components
        logging.error(f"Error while Initialising {err.component} - {err.message}")

    except OperationError as err:
        # Exception during operation
        logging.error(err.message)

    finally:
        # Shut down the system, ensures outputs are disabled and threads are joined on close
        print("Shutting down components...", end='')
        shutdown()
        print("Complete\n")
        print("Goodbye.\n")
    return 0


def get_args():
    """Parses the arguments for the control system and outputs usage or help information if needed

    :return: mode: Input mode of the CUB as one of the choices defined in Input.INPUT_MODES
             filename: Input file for the file input mode
             file_language: Language/Format of the input file as defined in Input.FILE_LANGUAGES
             level:  Logging level for providing extra output to user
             logfile: Logging file for output to a file
    :rtype: (string, string, string, string, string)
    """
    # Create parser
    parser = argparse.ArgumentParser(description='Curtin University Brailler Control System.')

    # Input mode
    parser.add_argument('mode', metavar='<Input Mode>', type=str.upper, nargs=1, choices=INPUT_MODES,
                        help='Mode selection for Input to the Brailler')
    # No Wrap Flag
    parser.add_argument('-nowrap', action="store_false", help='Disables partial word wrapping on new lines')
    # Input file for FILE input mode
    parser.add_argument('-inputfile', metavar='<Filename>', type=str, nargs='?', help='File name for file input')
    # Input file language
    parser.add_argument('-file_language', metavar='<File Language>', type=str.upper, nargs='?', default="ENG",
                        help='Language of file text for file input', choices=FILE_LANGUAGES)
    # Log level definition
    parser.add_argument('-log', metavar='<Logging Level>', type=str.upper, nargs='?', help='Level of Logging output',
                        choices={'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'})
    # Log output file definition
    parser.add_argument('-logfile', metavar='<Filename>', type=str, nargs='?', help='File name for logging output')

    # Parse command line arguments
    args = parser.parse_args()

    # Set word wrap value based on flag presence
    global word_wrap
    word_wrap = args.nowrap

    # Get mode argument (Converted to Uppercase by parser)
    mode = args.mode[0]
    # Optional arguments
    filename = args.inputfile
    file_language = args.file_language
    level = args.log
    logfile = args.logfile

    # Ensure that a file is provided for file input
    if mode == "FILE":
        if filename is None:
            raise ArgumentError("-inputfile", "No file option provided for file input", parser.format_help())

    return mode, filename, file_language, level, logfile


def setup_logging(level, logfile):
    """Initialises the logging library as per inputs

    :param level: Logging level to be output
    :param logfile: Output file for the logging if logging is to be to a file
    :return:
    """
    # Define format for logging strings
    log_format = '%(asctime)s.%(msecs)03d : %(levelname)s : %(module)s : %(message)s'
    date_format = '%d/%m/%Y - %H:%M:%S'

    # Log to file if flag was set
    if logfile is None:
        # Log to screen
        logging.basicConfig(level=level, format=log_format, datefmt=date_format)
    else:
        # Log to file
        logging.basicConfig(level=level, format=log_format, datefmt=date_format, filename=logfile)


def initialise_components(mode, filename, file_language):
    """Initialises The CUB components and threads and checks for successful start-up of all components

    :param mode: Selected Input mode
    :param filename: File name if input mode is set to FILE
    :param file_language: Language of input file if input mode is set to FILE
    :return:
    """
    # Construct component objects
    print("Initialising Components...", end='')
    logging.info("Constructing Components...")
    components['Embosser'] = Embosser(simulate=False)
    components['Traverser'] = HeadTraverser(simulate=False)
    components['Selector'] = ToolSelector(simulate=False)
    components['Feeder'] = Feeder(simulate=True)
    components['Input'] = Input(input_mode=mode, filename=filename, file_language=file_language)
    print("Complete")

    # Fork threads and run startup routines
    start_threads()

    print("Running Startup routines", end='')
    # For each of the components
    for name, comp in components.items():
        logging.debug(f"Confirming startup for {name}")
        print(".", end='')
        # Embosser is controlled by main thread
        if name == 'Embosser':
            # run Embosser startup
            msg = comp.startup()
        else:
            # Receive startup message
            msg = comp.recv()

        # Ensure startup was successful
        if msg == ACK:
            logging.info(f"Startup Confirmed for {name}")
        else:
            # Startup Failure
            raise InitialisationError(name, f"Initialisation Failed. ACK message: {msg}")
    print("Complete")


def start_threads():
    """Starts the component threads and initialises the tasks dictionary to zero

    :return: None
    """
    print("Starting Threads...", end='')

    # Initialise task counters to zero
    tasks['Traverser'] = 0
    tasks['Selector'] = 0
    tasks['Feeder'] = 0
    tasks['Input'] = 0

    # For each non embosser component, create and start the thread
    for name, component in components.items():
        if name != 'Embosser':
            logging.info(f"Starting {name} thread...")
            # Create thread targeting the thread_in function of the component
            threads[name] = Thread(target=component.thread_in)
            # Start the threads execution (Runs startup routine)
            threads[name].start()
    print("Complete")


def cub_loop():
    """Operational loop of the CUB control program

    :return: None
    """
    # Get Input as Array of dots in cell number order
    # In No-Wrap Mode: Store in list until a blank input is received
    # Otherwise print cell in two halves
    end_of_input = False
    word_buffer = []
    global last_char
    last_char = ""

    components["Input"].start_input()

    print("Starting Cub Operation")
    # Loop until the input is finished
    while not end_of_input:
        # Retrieve the next character from the Input component
        next_char = components['Input'].recv()
        logging.info(f"Processing character: {next_char}")
        try:

            if next_char == "END OF INPUT":
                # Input signals the end of input
                end_of_input = True

            elif next_char == "BACKSPACE":
                # Input is a backspace
                    if last_char != "000000":
                        # Last character not a space, clear the cell
                        backspace(clear=True)
                    else:
                        # last character is a space, no need to clear
                        backspace(clear=False)

                    # Last character buffer is now out of date
                    last_char = 'x'

            elif not word_wrap:
                # Only print word on spaces
                if next_char == "000000":
                    # Print the buffered word
                    print_word(word_buffer)
                else:
                    # Add the character to the buffer
                    word_buffer.append(next_char)

            else:
                # Print each character as received
                head_next_char()
                print_char(next_char)

        except OperationError as op:
            # Catch errors in operations (Thrown by Task barrier)
            logging.warning(f"{op.component} WARNING: {op.operation} Failed - {op.message}")
        # Keep track of previous character
        last_char = next_char


def print_word(word):
    """Prints the input word on the Brailler followed by a space

    :param word:
    :return: None
    """
    logging.debug(f"Printing word: {word}")
    # Print each character in the word:
    for i, char in enumerate(word):
        head_next_char(len(word) - i)
        print_char(char)

    # Print space as per last input
    print_char("000000")


def print_char(char):
    """Prints the input char to the brailler

    :param char: Character in CUB Braille format to be printed
    :return: None
    """
    logging.debug(f"Printing character: {char}")
    global current_char
    global last_char

    # No need to emboss for spaces
    if char == "000000":
        # Don't print as the first character of a new line unless there is more than one in a row
        if current_char == 0 and last_char != "000000":
            # Dont print space as the first character of a new line
            # Unless it is multiple spaces in a row
        else:
            send_task('Traverser', "MOVE COL POS")
            send_task('Traverser', "MOVE CHAR POS")
    # Print each column separately
    else:
        print_col(char[0:3])
        send_task('Traverser', "MOVE COL POS")
        print_col(char[3:6])


def print_col(column):
    """Prints the input string as a single column

    :param column: Input half CUB Braille format to be output
    :return: None
    """
    logging.debug(f"Printing Column: {column}")
    send_task('Selector', "MOVE " + column)

    task_barrier(targets=['Selector', 'Traverser', 'Feeder'])

    components['Embosser'].activate()


def head_next_char(word_length=1):
    """Move the traversal head to the next character position, feeds a new line if needed

    :param word_length: The length of the word to be output (Used when not allowing word wrapping)
    :return: None
    """
    global current_line, current_char

    logging.debug(f"Moving Head Position to next character, curr_char = {current_char}")

    # Check if the current character (or word) will overflow the line
    if (current_char + word_length) > components['Feeder'].get_paper_size():
        # If so, return the head to the home position
        send_task('Traverser', "HOME")
        send_task('Selector', "HOME")
        current_char = 0
        # Check if reached the end of the paper
        if current_line == components['Feeder'].get_paper_length():
            # If so, eject the page and load another
            logging.debug(f"Loading new page into embosser")
            send_task('Feeder', "PAPER EJECT")
            send_task('Feeder', "PAPER LOAD")
            current_line = 1

        else:
            # If not at end of page, load the next line
            logging.debug(f"Feeding to next line of page")
            send_task('Feeder', "FEED 1 POS")
            current_line += 1
    else:
        # Dont move from the start of the line until character is printed
        if current_char != 0:
            # Move to the next character position
            send_task('Traverser', "MOVE CHAR POS")
        # Incement character count
        current_char += 1


def backspace(clear=True):
    """Actions a backspace on the CUB

    :param clear: Optional parameter which flags if an embossing of the clear tool is necessary
    :return: None
    """
    global current_char, current_line

    # If currently at the first character of the page
    if current_char == 0:
        if current_line == 1:
            # First line of the page, cannot return to last page
            raise OperationError("CUBBrailler", "Backspace", "Unable to backspace at start of page, no action taken")
        else:
            # Can return to last line, move to the final position
            send_task('Feeder', "FEED 1 NEG")
            # Select blank tool for large movement - Current mitigation of tool head dragging on embossing plate
            send_task('Selector', "HOME")
            # Move the head to the position of the last column
            send_task('Traverser', "MOVE CHAR POS " + str(components['Feeder'].get_paper_size()))
            send_task('Traverser', "MOVE COL POS " + str(components['Feeder'].get_paper_size()))
            # Update State variables
            current_line -= 1
            current_char = components['Feeder'].get_paper_size() -1

    # If clear flag is set
    if clear:
        # Clear the second column
        print_col("000")

        # Move to the first column
        send_task('Traverser', "MOVE COL NEG")

        #Clear the first column
        print_col("000")
    else:
        # No need to clear, just move to left column
        send_task('Traverser', "MOVE COL NEG")

    # Reduce the character counter
    current_char -= 1

    # Only move backward if not already in home position
    if current_char != 0:
        # Move to previous character
        send_task('Traverser', "MOVE CHAR NEG")


def send_task(target, task):
    """Sends the task to the target component and increases the relevant task counter

    :param target: String name of the target component
    :param task: String task message to be send
    :return: None
    """
    logging.debug(f"Sending Task to {target} - {task}")
    # Send task to component
    components[target].send(task)
    # Increment task tracker counter
    tasks[target] += 1


def task_barrier(targets=list()):
    """Ensures that all components in the targets list have completed all tasks successfully

    :param targets: list of components to check
    :return: None
    """
    # Initialise component group to iterate, if no input, group is all components
    group = []
    if len(targets) == 0:
        group = tasks.items()
    else:
        for tar in targets:
            group.append([tar, tasks[tar]])

    logging.debug(f"Task barrier for: {group}")

    # For each component in the group, and its task count
    for name, count in group:
        # Loop for number of tasks in count
        for i in range(0, count):
            # Receive the output from the component
            msg = components[name].recv()
            # If message is an acknowledgement
            if msg == ACK:
                tasks[name] -= 1
            else:
                logging.error(msg)
                raise OperationError(name, "", msg)

    logging.debug(f"Leaving Task barrier for: {group}")


def shutdown():
    """Shuts down all components and rejoins all threads

    :return: None
    """
    logging.info("Shutting Down CUB System")
    close_components()
    join_threads()
    logging.info("Shut down complete")


def close_components():
    """Send a close message to all components to ensure they close gracefully

    :return: None
    """
    for name, comp in components.items():
        logging.info(f"Shutting down component: {name}")
        if comp is not None:
            comp.close()
            if name != 'Embosser':
                comp.send("CLOSE")


def join_threads():
    """Joins all forked threads

    :return: None
    """
    for name, t in threads.items():
        logging.debug(f"Joining Thread: {name}")
        try:
            t.join()
            logging.info(f"Successfully Joined Thread: {name}")
        except RuntimeError as err:
            logging.error(f"Unable to join thread: {name} - {err.message}")


if __name__ == '__main__':
    main()
