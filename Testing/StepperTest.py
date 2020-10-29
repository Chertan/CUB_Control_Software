from component_control.hardware_interface.StepperMotor import StepperMotor
import time
import logging

# Motor pins
TRAV_DIR = 21
TRAV_STEP = 20
TRAV_ENA = 16

# Motor speed parameters to be tuned during testing
TRAV_START_SPEED = 500
TRAV_MAX_SPEED = 1200
TRAV_RAMP_RATE = 15
TRAV_NSTEPS = 1200

# Motor pins
TOOL_DIR = 6
TOOL_STEP = 13
TOOL_ENA = 5

# Motor speed parameters to be tuned during testing
TOOL_START_SPEED = 20
TOOL_MAX_SPEED = 60
TOOL_RAMP_RATE = 5
TOOL_NSTEPS = 54

# Direction Selectors to be confirmed during testing
POS_DIR = 1
NEG_DIR = 0


def main():

    logging.basicConfig(level=logging.INFO)

    mot = input("Enter motor to test, <TOOL or TRAV>")

    try:
        if mot == "TOOL":
            print("Testing with the Tool Selection Motor")
            stepper = StepperMotor(TOOL_DIR,TOOL_STEP, TOOL_ENA, TOOL_START_SPEED, TOOL_MAX_SPEED,TOOL_RAMP_RATE)
            n_steps = TOOL_NSTEPS
        elif mot == "TRAV":
            print("Testing with the Head Traversal Motor")
            stepper = StepperMotor(TRAV_DIR, TRAV_STEP, TRAV_ENA, TRAV_START_SPEED, TRAV_MAX_SPEED, TRAV_RAMP_RATE)
            n_steps = TRAV_NSTEPS
        else:
            print("Enter Valid Input")
            exit()

        # stepper.move_steps(10, POS_DIR)
        # stepper.move_steps(10, NEG_DIR)

        print("Exit testing with CTRL-C")

        while True:
            print(f"Moved {stepper.move_steps(n_steps, POS_DIR)} steps in the POS DIR")
            time.sleep(1)

            print(f"Moved {stepper.move_steps(n_steps, NEG_DIR)} steps in the POS DIR")

            time.sleep(1)

    except KeyboardInterrupt:
        stepper.e_stop()


if __name__ == '__main__':
    main()
