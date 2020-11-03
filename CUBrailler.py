from component_control.ToolSelector import ToolSelector
from component_control.HeadTraverser import HeadTraverser
from component_control.Embosser import Embosser
from component_control.Feeder import Feeder
from component_control.CUBInput import CUBInput
from component_control.CUBInput import INPUT_MODES
from component_control.CUBInput import FILE_LANGUAGES
from CUBExceptions import *
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

        # Create component objects and start threads
        # Also runs startup procedures and ensures components return positive acknowledgements
        initialise_components(mode, filename, file_language)

        # Run the main loop of the System, returns on error or end of input.
        cub_loop()

    except KeyboardInterrupt:
        # Interrupt from the command line
        logging.warning("Shutting Down due to Keyboard Interrupt")

    except ArgumentError as err:
        # Exception when parsing command line arguments
        logging.error(f"Error parsing Argument {err.argumentName}: {err.message}")
        # Prints the argument help prompt to the screen
        print(err.argHelp)

    except InitialisationError as err:
        # Exception while initialising components
        logging.error(err.message)

    except OperationError as err:
        # Exception during operation
        logging.error(err.message)

    finally:
        # Shut down the system, ensures outputs are disabled and threads are joined on close
        shutdown()

    return 0


def get_args():
    """Parses the arguments for the control system and outputs usage or help information if needed

    :return: mode: Input mode of the CUB as one of the choices defined in CUBInput.INPUT_MODES
             filename: Input file for the file input mode
             file_language: Language/Format of the input file as defined in CUBInput.FILE_LANGUAGES
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
    mode = args.mode
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
    log_format = '%(asctime)s : $(message)s'
    date_format = '%d/%m/%Y - %H:%M:S'

    if logfile is None:
        logging.basicConfig(level=level, format=log_format, datefmt=date_format)
    else:
        logging.basicConfig(level=level, format=log_format, datefmt=date_format,  filename=logfile)


def initialise_components(mode, filename, file_language):
    """Initialises The CUB components and threads and checks for successful start-up of all components

    :param mode: Selected Input mode
    :param filename: File name if input mode is set to FILE
    :param file_language: Language of input file if input mode is set to FILE
    :return:
    """
    # Construct component objects
    components['Embosser'] = Embosser(simulate=True)
    components['Traverser'] = HeadTraverser(simulate=True)
    components['Selector'] = ToolSelector(simulate=True)
    components['Feeder'] = Feeder(simulate=True)
    components['Input'] = CUBInput(input_mode=mode, filename=filename, file_language=file_language)

    # Fork threads and run startup routines
    start_threads()

    # For each of the components
    for name, comp in components.items():
        # Embosser is controlled by main thread
        if name is 'Embosser':
            # run Embosser startup
            msg = comp.startup()
        else:
            # Receive startup message
            msg = comp.recv()

        # Ensure startup was successful
        if msg == ACK:
            logging.info(f"Main Thread received ACK message {msg} from {name}")
        else:
            # Startup Failure
            raise InitialisationError(name, f"Initialisation Failed. ACK message: {msg}")


def start_threads():
    """Starts the component threads and initialises the tasks dictionary to zero

    :return: None
    """
    tasks['Traverser'] = 0
    tasks['Selector'] = 0
    tasks['Feeder'] = 0
    tasks['Input'] = 0

    # For each non embosser component, create and start the thread
    for component in components:
        if component.key() is not 'Embosser':
            threads[component.key] = Thread(component.value.thread_in)
            threads[component.key].start()


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

    # Loop until the input is finished
    while not end_of_input:
        # Retrieve the next character from the Input component
        next_char = components['input'].recv()

        # Input signals the end of input
        if next_char == "END OF INPUT":
            end_of_input = True
        # Input is a backspace
        if next_char == "BACKSPACE":
            # Perform Backspace
            try:
                # Last character is a space,
                if last_char is not "000000":
                    backspace(clear=True)
                # last character is a space, no need to clear
                else:
                    backspace(clear=False)

                # Last character buffer is now out of date
                last_char = 'x'
            except OperationError as op:
                logging.warning(f"{op.component} WARNING: {op.operation} Failed - {op.message}")
        elif word_wrap:
            head_next_char()
            print_char(next_char)

        elif not word_wrap:
            if next_char == "000000":
                print_word(word_buffer)
            else:
                word_buffer.append(next_char)
        last_char = next_char


def print_word(word):
    """Prints the input word on the Brailler followed by a space

    :param word:
    :return: None
    """
    # For each word:
    # - Move Head Char (Send word length - i)
    # - Print Char
    # Then print Space
    for i, char in enumerate(word):
        head_next_char(len(word) - i)
        print_char(char)

    print_char("000000")


def print_char(char):
    """Prints the input char to the brailler

    :param char: Character in CUB Braille format to be printed
    :return: None
    """
    # Print Left
    # Move Head Col
    # Print Right
    # Update Count
    global current_char
    global last_char

    # No need to emboss for spaces
    if char == "000000":
        # Don't print as the first character of a new line unless there is more than one in a row
        if last_char == "000000" and current_char == 0:
            send_task('Traverser', "MOVE COL POS")
            send_task('Traverser', "MOVE CHAR POS")
            current_char += 1
    # Print each column separately
    else:
        print_col(char[1:3])
        send_task('Traverser', "MOVE COL POS")
        print_col(char[3:6])
        current_char += 1


def print_col(column):
    """Prints the input string as a single column

    :param column: Input half CUB Braille format to be output
    :return: None
    """
    send_task('Selector', "MOVE " + column)

    task_barrier(targets=['Selector', 'Traverser'])

    components['Embosser'].activate()


def head_next_char(word_length=1):
    """Move the traversal head to the next character position, feeds a new line if needed

    :param word_length: The length of the word to be output (Used when not allowing word wrapping)
    :return: None
    """
    global current_line, current_char

    # Check if the current character (or word) will overflow the line
    if (current_char + word_length) > components['Feeder'].get_paper_size():
        # If so, return the head to the home position
        send_task('Selector', "HOME")
        # Check if reached the end of the paper
        if current_line == components['Feeder'].get_paper_length():
            # If so, eject the page and load another
            send_task('Feeder', "PAPER EJECT")
            send_task('Feeder', "PAPER LOAD")
            current_line = 1

        else:
            # If not at end of page, load the next line
            send_task('Feeder', "LINE FEED")
            current_line += 1

        send_task('Traverser', "HOME")
        current_char = 0

    #
    if current_char == 0:
        # First character of the line, no need to move
        current_char += 1
    else:
        # Move to the next character position
        send_task('Traverser', "MOVE CHAR POS")
        current_char += 1

    # Wait until movement is complete to continue
    task_barrier(['Selector', 'Traverser'])


def backspace(clear=True):
    """Actions a backspace on the CUB

    :param clear: Optional parameter which flags if an embossing of the clear tool is necessary
    :return: None
    """
    # Move head to the second column of the last character
    global current_char, current_line

    # If clear flag is set
    if clear:
        # Select the clear tool
        send_task('Selector', "HOME")
        # Wait for movement and tool selection to complete
        task_barrier(targets=['Selector'])
        # Emboss action
        components['Embosser'].activate()
        # Move to the first column
        send_task('Traverser', "MOVE COL NEG")
        # Wait for movement to be complete
        task_barrier(targets=['Traverser'])
        # Emboss action
        components['Embosser'].activate()
    else:
        # No need to clear, just move to left column
        send_task('Traverser', "MOVE COL NEG")

    # If currently at the first character of the page
    if current_char == 1:
        if current_line == 1:
            # First line of the page, cannot return to last page
            raise OperationError("CUBBrailler", "Backspace", "Unable to backspace at start of page, no action taken")
        else:
            # Can return to last line, move to the final position
            send_task('Feeder', "PAGE FEED NEG")
            # Select blank tool for large movement - Current mitigation of tool head dragging on embossing plate
            send_task('Selector', "HOME")
            # Move the head to the position of the last column
            send_task('Traverser', "MOVE CHAR POS " + components['Feeder'].get_paper_size())
            send_task('Traverser', "MOVE COL POS " + components['Feeder'].get_paper_size())
            # Update State variables
            current_line -= 1
            current_char = components['Feeder'].get_paper_size()

    else:  # Not first character
        # Move to previous character
        send_task('Traverser', "MOVE CHAR NEG")
        current_char -= 1

    # Ensure head and page movement is complete before continuing
    task_barrier(['Traverser', 'Feeder'])


def send_task(target, task):
    """Sends the task to the target component and increases the relevant task counter

    :param target: String name of the target component
    :param task: String task message to be send
    :return: None
    """
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
        if name == 'Embosser':
            comp.exit()
        else:
            comp.exit()
            comp.send("CLOSE")


def join_threads():
    """Joins all forked threads

    :return: None
    """
    for name, t in threads.items():
        logging.info(f"Joining Thread: {name}")
        try:
            t.join()
            logging.info(f"Successfully Joined Thread: {name}")
        except RuntimeError as err:
            logging.error(f"Unable to join thread: {name} - {err.message}")


if __name__ == '__main__':
    main()
