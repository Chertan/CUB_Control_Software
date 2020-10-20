from StepperMotor import StepperMotor
import time

# Motor pins
DIR = 6
STEP = 13
ENA = 5

 # Motor speed parameters to be tuned during testing
START_SPEED = 8
MAX_SPEED = 70
RAMP_RATE = 2

# Direction Selectors to be confirmed during testing
POS_DIR = 1
NEG_DIR = 0


def main():

    try:
        stepper = StepperMotor(DIR, STEP, ENA, START_SPEED, MAX_SPEED, RAMP_RATE)

        #stepper.move_steps(10, POS_DIR)
        #stepper.move_steps(10, NEG_DIR)

        while True:
            print(f"Taking {stepper.move_steps(54, POS_DIR)} steps in the POS DIR")
            time.sleep(1)

            print(f"Taking {stepper.move_steps(54, NEG_DIR)} steps in the POS DIR")

            time.sleep(1)


    except KeyboardInterrupt:
        stepper.e_stop()



if __name__ == '__main__':
    main()