from component_control.HeadTraverser import HeadTraverser
import time
import logging


def main():

    logging.basicConfig(level=logging.INFO)

    trav = ""

    try:
        trav = HeadTraverser()

        if isinstance(trav, HeadTraverser):
            print("HeadTraverser Successfully Initialised")

        # stepper.move_steps(300, POS_DIR)
        # stepper.move_steps(300, NEG_DIR)

        while True:

            for i in range(0, 25):
                time.sleep(0.5)
                trav.__traverse_column()
                time.sleep(0.5)
                trav.__traverse_character()

            time.sleep(1)
            print("Returning Home")
            trav.__traverse_home()
            time.sleep(1)

    except KeyboardInterrupt:
        if isinstance(trav, HeadTraverser):
            trav.emergency_stop()


if __name__ == '__main__':
    main()
