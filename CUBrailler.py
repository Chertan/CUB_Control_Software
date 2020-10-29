from component_control.ToolSelector import ToolSelector
from component_control.HeadTraverser import HeadTraverser
from component_control.Embosser import Embosser
from component_control.Feeder import Feeder
from component_control.CUBInput import CUBInput
from CUBExceptions import *
import logging
from threading import Thread

INPUT_MODE = "BRAILLE KEYBOARD"

WORD_WRAP = False

components = {}
threads = {}
tasks = {}

current_line = 1
current_char = 0


def main():
    # Construct component control
    # Construct
    # Start sub threads and send to start up
    # Get ack from each thread of successful startup
    # load input thread with mode
    #

    # Work loop: take input (3,2 array)
    #            Process input into tool numbers
    #

    # Setup Constructs
    try:
        initialise_components()
        cub_loop()

    except InitialisationError as err:
        logging.error(f"{err.message}")
    except KeyboardInterrupt:
        logging.info("Shutting Down due to Keyboard Interrupt")
    finally:
        shutdown()


def initialise_components():
    components['Embosser'] = Embosser()
    components['Traverser'] = HeadTraverser()
    components['Selector'] = ToolSelector()
    components['Feeder'] = Feeder()
    components['Input'] = CUBInput()

    start_threads()

    for name, comp in components.items():
        if name is 'Embosser':
            msg = comp.startup()
        else:
            msg = comp.recv()
        if msg == "ACK":
            logging.info(f"Main Thread received ACK message {msg} from {name}")
        else:
            raise InitialisationError(name, f"Initialisation Failed. ACK message: {msg}")


def start_threads():
    tasks['Traverser'] = 0
    tasks['Selector'] = 0
    tasks['Feeder'] = 0
    tasks['Input'] = 0

    for component in components:
        if component.key() is not 'Embosser':
            threads[component.key] = Thread(component.value.thread_in)
            threads[component.key].start()


last_char = ""


def cub_loop():
    # Run CUB Operation
    # Get Input as Array of dots in cell number order
    # In No-Wrap Mode: Store in list until a blank input is received
    # Otherwise print cell in two halves
    end_of_input = False
    word_buffer = []
    global last_char
    last_char = ""

    while not end_of_input:
        next_char = components['input'].recv()

        if next_char == "END OF INPUT":
            end_of_input = True
        if next_char == "BACKSPACE":
            # Perform Backspace
            try:
                if last_char is not " ":
                    backspace(clear=True)
                    last_char = "x"
                else:
                    backspace(clear=False)
            except OperationError as op:
                logging.warning(f"{op.component} WARNING: {op.operation} Failed - {op.message}")
        elif WORD_WRAP:
            head_next_char()
            if next_char == " ":

                print_char("000000")
            else:
                print_char(next_char)

        elif not WORD_WRAP:
            if next_char == " ":
                print_word(word_buffer)
            else:
                word_buffer.append(next_char)
        last_char = next_char


def print_word(word):
    # For each word:
    # - Move Head Char (Send word length - i)
    # - Print Char
    # Then print Space
    for i, char in enumerate(word):
        head_next_char(len(word) - i)
        print_char(char)

    print_char("000000")


def print_char(char):
    # Print Left
    # Move Head Col
    # Print Right
    # Update Count
    global current_char

    if char == "000000":
        # Don't print as the first character of a new line unless there is more than one in a row
        if last_char == " " and current_char == 0:
            send_task('Traverser', "MOVE COL POS")
            send_task('Traverser', "MOVE CHAR POS")
            current_char += 1
    else:
        print_col(char[1:3])
        send_task('Traverser', "MOVE COL POS")
        print_col(char[3:6])
        current_char += 1


def print_col(column):
    send_task('Selector', "MOVE " + column)

    task_barrier(targets=['Selector', 'Traverser'])

    components['Embosser'].activate()


def head_next_char(word_length=1):
    global current_line, current_char

    if (current_char + word_length) > components['Feeder'].get_paper_size():
        send_task('Selector', "HOME")
        if current_line == components['Feeder'].get_paper_length():
            send_task('Feeder', "PAPER EJECT")
            send_task('Feeder', "PAPER LOAD")
            current_line = 1

        else:
            send_task('Feeder', "LINE FEED")
            current_line += 1

        send_task('Traverser', "HOME")
        current_char = 0

    # Prevent movement before first character is printed
    elif current_char != 0:
        send_task('Traverser', "MOVE CHAR POS")

    task_barrier(['Selector', 'Traverser'])


def backspace(clear=False):
    # Move head to the second column of the last character
    global current_char, current_line
    if current_char == 0:
        # First line of the page, backspace to last page

        if current_line != 0:
            # First line of the page, cannot return to last page
            raise OperationError("CUBBrailler", "Backspace", "Unable to backspace at start of page, no action taken")
        else:
            # Can return to last page, move to the final position
            send_task('Feeder', "PAGE FEED NEG")
            send_task('Traverser', "MOVE CHAR POS " + components['Feeder'].get_paper_size())
            send_task('Traverser', "MOVE COL POS " + components['Feeder'].get_paper_size())
            current_line -= 1
            current_char = components['Feeder'].get_paper_size()
    if clear:
        send_task('Selector', "HOME")
        # Wait for movement and tool selection to complete
        task_barrier(targets=['Traverser', 'Selector'])

        components['Embosser'].activate()

        send_task('Traverser', "MOVE COL NEG")


def send_task(target, task):
    components[target].send(task)
    tasks[target] += 1


def task_barrier(targets=list()):
    group = []
    if len(targets) == 0:
        group = tasks.items()
    else:
        for tar in targets:
            group.append([tar, tasks[tar]])

    for name, count in group:
        for i in range(0, count):
            msg = components[name].recv()
            if msg == "ACK":
                tasks[name] -= 1
            else:
                logging.error(msg)
                raise OperationError(name, "", msg)


def shutdown():
    logging.info("Shutting Down CUB System...")
    close_components()
    join_threads()
    print("CUB System successfully shut down. Now Exiting...")


def close_components():
    for name, comp in components.items():
        logging.info("fShutting down component: {name}")
        if name == 'Embosser':
            comp.exit()
        else:
            comp.exit()
            comp.send("CLOSE")


def join_threads():
    for name, t in threads.items():
        logging.info(f"Joining Thread: {name}")
        try:
            t.join()
        except RuntimeError as err:
            logging.error(f"Unable to join thread: {name} - {err.message}")


if __name__ == '__main__':
    main()