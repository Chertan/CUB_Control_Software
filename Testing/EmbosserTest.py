from component_control.Embosser import Embosser
import logging
import time


def main():
    logging.basicConfig(level=logging.INFO)

    embosser = ""

    try:
        embosser = Embosser()

        if isinstance(embosser, Embosser):
            print("Embosser Successfully Initialised")

        while True:
            print("Starting Embosser Testing...")
            print("---------------------------------------------------------------")

            for i in range(1, 25):
                print(f"Testing activation pulse of length: {1.0/i} seconds")
                embosser.activate(length=1.0/i)
                time.sleep(0.5)

            print("---------------------------------------------------------------")

            for i in range(1, 25):
                print(f"Testing pulse gap of:  {1.0/i} seconds")
                embosser.activate()
                time.sleep(1.0/i)

    except KeyboardInterrupt:
        if isinstance(embosser, Embosser):
            embosser.emergency_stop()


if __name__ == "__main__":
    main()
