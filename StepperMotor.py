# Class: StepperMotor
# Desc: Hardware interface class to handle the control of a stepper motor
# Params: in_direction is the gpio pin number of the direction wire of the motor
#         in_step is the gpio pin number of the step wire of the motor
#         in_enable is the gpio pin number of the enable wire of the motor
#         in_start_speed is the starting speed of the motor
#         in_max_speed is the maximum speed of the motor
#
# Functions: move_steps(<number of steps>, <direction of movement(0 | 1)> )
#               - rotates the motor the input number of steps
#            move_until(<condition function>, <direction of movement (0 | 1)> )
#               - rotates the motor in the input direction until the condition function returns true
#            stop()
#               - Sets the stop flag for the stepper motor, stopping the current operation
#            e_stop()
#               - Sets the Emergency stop flag for the class, stopping all Stepper motor operations
import pigpio
import time
import logging


class StepperMotor:
    gpio = pigpio.pi()

    # Emergency stop flag for the stepper motors
    # Setting to True will stop all motors from rotating
    emergency_stop = False

    # Speed where the output is delayed by only the software and gpio overhead
    CLIP_SPEED = 2000

    def __init__(self, in_direction=None, in_step=None, in_enable=None, in_start_speed=None, in_max_speed=None, in_ramp_rate=None):
        self.direction = in_direction
        self.step = in_step
        self.enable = in_enable

        # Speed is in steps per second
        self.startSpeed = in_start_speed
        self.maxSpeed = in_max_speed
        self.rampRate = in_ramp_rate

        self.stop_motor = False

        StepperMotor.gpio.set_mode(self.enable, pigpio.OUTPUT)
        StepperMotor.gpio.write(self.enable, 0)
        logging.info(f"Setting up Stepper ENABLE on GPIO Pin: {self.enable}")

        StepperMotor.gpio.set_mode(self.step, pigpio.OUTPUT)
        StepperMotor.gpio.write(self.step, 0)
        logging.info(f"Setting up Stepper STEP on GPIO Pin: {self.step}")

        StepperMotor.gpio.set_mode(self.direction, pigpio.OUTPUT)
        StepperMotor.gpio.write(self.direction, 0)
        logging.info(f"Setting up Stepper DIR on GPIO Pin: {self.direction}")

        # Set enable pin high
        # Set direction pin
        self.__startup_motor(1)

    def __del__(self):
        self.__disable_motor()

    def __step_motor(self, speed):
        # Wait - Sets speed
        # Transforms speed to a delay between steps
        if speed < StepperMotor.CLIP_SPEED:
            logging.debug(f"Stepping Motor with speed: {speed}")
            time.sleep(1 / speed)

        # Pulse Step Pin
        StepperMotor.gpio.write(self.step, 1)
        StepperMotor.gpio.write(self.step, 0)

    def __startup_motor(self, in_dir):
        if not StepperMotor.emergency_stop:
            self.stop_motor = False
            StepperMotor.gpio.write(self.enable, 1)
            StepperMotor.gpio.write(self.direction, in_dir)

        else:
            logging.error("Stepper not started due to Emergency Stop Flag set")

    def __disable_motor(self):
        StepperMotor.gpio.write(self.enable, 0)
        StepperMotor.gpio.write(self.step, 0)
        StepperMotor.gpio.write(self.direction, 0)

    def stop(self):
        self.stop_motor = True
        # self.__disable_motor()

        logging.error("Stepper Motor Stop Flag Set to True")


    def e_stop(self):
        StepperMotor.emergency_stop = True
        self.__disable_motor()

        logging.error("Stepper Motor Emergency Stop Flag Set to True")

    def move_steps(self, count, in_direction):
        # Set enable pin high
        # Set direction pin
        self.__startup_motor(in_direction)

        logging.info(f"Stepping Stepper by {count} steps, in direction: {in_direction} on STEP Pin: {self.step}")

        speed = self.startSpeed

        ramp_length = (self.maxSpeed - speed) / self.rampRate

        step_count = count

        for i in range(0, count):

            if StepperMotor.emergency_stop:
                logging.info("Stepper Motor stopping due to Emergency flag set")

                step_count = i
                break

            if self.stop_motor:
                logging.info("Stepper Motor stopping due to stop flag set")
                step_count = i
                break

            self.__step_motor(speed)

            # Ramp up speed at start of movement
            if i < ramp_length:
                speed += self.rampRate

            # Ramp down speed at end of movement
            # count -1 for index from 0, total -1 as it is decremented after step
            if i > (((count-1) - ramp_length) -1):
                speed -= self.rampRate

        # Set all output pins low
        # self.__disable_motor()

        return step_count

    # Function to move motor until the function in the in_condition parameter returns TRUE
    # Returns the number of steps taken
    def move_until(self, in_condition, in_direction):
        # Set enable pin high
        # Set direction pin
        self.__startup_motor(in_direction)

        logging.info(f"Stepping Stepper until {in_condition.__name__}, in direction: {in_direction} on STEP Pin: "
                     f"{self.step}")

        count = 0

        while not in_condition():
            if StepperMotor.emergency_stop:
                if count == 0:
                    logging.error("Stepper not started due to Emergency Stop Flag set")
                else:
                    logging.info("Stepper Motor stopping due to Emergency flag set")

                break

            if self.stop_motor:
                logging.info("Stepper Motor stopping due to stop flag set")
                break

            self.__step_motor(self.startSpeed)
            count += 1

        # Set all output pins low
        # self.__disable_motor()

        return count
