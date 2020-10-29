from component_control.CUBInput import CUBInput
from threading import Thread

# Input Component Test Program


INPUT_MODE = "KEYBOARD"

components = {}
threads = {}
tasks = {}


def main():

    in_comp = CUBInput(input_mode = INPUT_MODE)

    t_in = Thread(target = in_comp.thread_in())

    for i in range(0, 10):
        print(in_comp.recv())



if __name__ == '__main__':
    main()
