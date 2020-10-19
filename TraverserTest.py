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
import logging


def main():
    traverser = HeadTraverser()

    logging.basicConfig(level=logging.DEBUG)

    pos = 0

    while True:

        d = input('Enter p or n for direction')
        n = input('Enter number of character spaces')

        for i in range(0, n):
            if pos == 30:
                break
            if d is 'p':
                traverser.traverse_column()
                pos += 1
            if d is 'n':
                traverser.traverse_column(reverse=True)
                pos -= 1

        if pos == 30:
            print('Reached page max distance')


if __name__ == "__main__":
    main()