# Program:
#

#
#
#
#
#
#
#
#

from HeadTraverser import HeadTraverser
import time
import logging

def main():

    logging.basicConfig(level = logging.INFO)

    trav = ""

    try:
        trav = HeadTraverser()

        if isinstance(trav, HeadTraverser):
            print("HeadTraverser Successfully Initialised")

        #stepper.move_steps(300, POS_DIR)
        #stepper.move_steps(300, NEG_DIR)

        step = 0
        while True:

            # time.sleep(0.5)
            # print("Printing first Column")
            # trav.traverse_column()

            # time.sleep(0.5)
            # print("Printing second Column")
            # trav.traverse_column()

            # time.sleep(1)
            # print("Moving to next Character")
            # trav.traverse_character()

            # time.sleep(1)
            # print("Moving back to last Character")
            # trav.traverse_character(reverse=True)

            # time.sleep(0.5)
            # print("Replacing second Column")
            # trav.traverse_column(reverse=True)

            # time.sleep(0.5)
            # print("Replacing first Column")
            # trav.traverse_column(reverse=True)

            for i in range(0, 25):
                time.sleep(0.5)
                trav.traverse_column()
                time.sleep(0.5)
                trav.traverse_character()

            time.sleep(1)
            print("Returning Home")
            trav.traverse_home()
            time.sleep(1)


    except:
        if isinstance(trav, HeadTraverser):
            trav.emergency_stop()



if __name__ == '__main__':
    main()