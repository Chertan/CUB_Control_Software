from component_control.Input import Input
from threading import Thread
import logging
import argparse

# Input Component Test Program


def main():
   
    parser = argparse.ArgumentParser(description='Test Program for the CUBInput class.')
    parser.add_argument('mode', metavar='MODE', type=str, nargs=1, help='Input Mode to test')
    parser.add_argument('--file', metavar='file', type=str, nargs='?', help='File name for file input')
    parser.add_argument('--log', metavar='level', type=str, nargs='?', help='Logging Level')

    args = parser.parse_args()

    mode = args.mode[0]
    filename = args.file
    level = args.log

    if mode == "FILE" and filename is None:
        print("File name required for File Input")
        exit()

    if level == "info":
        logging.basicConfig(level=logging.INFO)
    elif level == "debug":
        logging.basicConfig(level=logging.DEBUG)

    in_comp = Input(input_mode=mode, filename=filename)

    t_in = Thread(target=in_comp.thread_in)

    t_in.start()

    msg = in_comp.recv()

    if msg == "ACK":
        logging.info(f"Received Acknowledgement: {msg}")

        in_comp.start_input()

        while True:
            msg = (in_comp.recv())
            print(msg)
            if msg == "END OF INPUT":
                break

    else:
        logging.error(msg)

    in_comp.close()


if __name__ == '__main__':
    main()
